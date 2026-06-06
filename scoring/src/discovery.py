"""
Discovery orchestrator — rolling-slice FMP scan.

Strategy (since FMP free tier blocks batching and we only have ~250 calls/day):
  - Split the S&P 500 into 10 slices of ~50 tickers each.
  - Each calendar day, score one slice. Persist results to
    cache/discovery_scores.json keyed by ticker.
  - /discover returns the *union* of every score we have on file, sorted by
    score. Each entry carries a `last_scored` date so the UI can flag stale
    entries.

Tradeoffs:
  - Full S&P 500 coverage takes ~10 days to bootstrap.
  - A ticker's data can be up to 10 days old.
  - But: this stays cleanly within FMP's free quota and matches the doc's
    "bias toward hold" spirit (you wait longer for a name to surface).

After ~10 days of running, every S&P 500 name has a score. After that the UI
keeps showing the freshest copy and slowly refreshes everything in rotation.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from . import cache, fmp_client
from .data_layer import NormalizedStock, _normalize_raw_to_stock
from .signals import Signal, score_stock
from .sp500 import load_sp500

log = logging.getLogger(__name__)

SLICES = 17  # ~30 tickers/day; full S&P 500 covered every 17 days
DISCOVERY_STORE = "discovery_scores"


def today_slice_index(num_slices: int = SLICES) -> int:
    """Deterministic slice picker — same date always picks the same slice."""
    return date.today().toordinal() % num_slices


def todays_tickers(universe: list[str], num_slices: int = SLICES) -> list[str]:
    if not universe:
        return []
    size = max(1, len(universe) // num_slices)
    idx = today_slice_index(num_slices)
    start = idx * size
    end = start + size if idx < num_slices - 1 else len(universe)
    return universe[start:end]


def run_rolling_scan(
    weights: dict[str, float],
    filters: dict[str, float],
) -> dict[str, Any]:
    """
    Score today's slice of the S&P 500 and merge results into the persistent
    discovery store. Returns the merged store payload.
    """
    universe = load_sp500()
    slice_tickers = todays_tickers(universe)
    log.info("discovery slice %d/%d: %d tickers", today_slice_index() + 1, SLICES, len(slice_tickers))

    # Use the standard FMP client path (OHLCV + fundamentals) — same as watchlist.
    ohlcv = _get_fmp_ohlcv(slice_tickers)
    fundamentals = _get_fmp_fundamentals(slice_tickers)

    today = cache.today_key()
    store = cache.load(DISCOVERY_STORE) or {}

    for ticker in slice_tickers:
        stock = _normalize_raw_to_stock(
            ticker=ticker,
            ohlcv=ohlcv.get(ticker),
            fundamentals=fundamentals.get(ticker),
        )
        signal = score_stock(stock, weights, filters)
        store[ticker] = {
            "last_scored": today,
            "signal": signal.model_dump(),
        }

    cache.save(DISCOVERY_STORE, store)
    return store


def get_all_discovery_signals() -> list[dict[str, Any]]:
    """Return every persisted discovery entry, sorted by score descending."""
    store = cache.load(DISCOVERY_STORE) or {}
    entries = list(store.values())
    entries.sort(key=lambda e: e["signal"].get("score", 0), reverse=True)
    return entries


# ---------------------------------------------------------------------------
# Per-ticker FMP fetch helpers (no daily cache here — discovery has its own
# persistent store, so re-fetching today's slice each day is intentional).
# ---------------------------------------------------------------------------

def _get_fmp_ohlcv(tickers: list[str]) -> dict[str, dict | None]:
    # Share the daily OHLCV cache with the watchlist layer to avoid double-fetching.
    # Never cache failures — see data_layer._get_ohlcv for rationale.
    cache_name = f"prices_{cache.today_key()}"
    cached = cache.load(cache_name) or {}
    # Evict poisoned entries: old list-format AND any null values.
    poisoned = [t for t, v in cached.items() if v is None or isinstance(v, list)]
    for t in poisoned:
        del cached[t]
    missing = [t for t in tickers if t not in cached]
    if missing:
        log.info("discovery: fetching FMP OHLCV for %d ticker(s)", len(missing))
        fresh = fmp_client.fetch_ohlcv(missing)
        successes = {t: v for t, v in fresh.items() if v is not None}
        if successes:
            cached.update(successes)
            cache.save(cache_name, cached)
    return {t: cached.get(t) for t in tickers}


def _get_fmp_fundamentals(tickers: list[str]) -> dict[str, dict[str, Any] | None]:
    cache_name = f"fundamentals_{cache.this_week_key()}"
    cached = cache.load(cache_name) or {}
    # Evict poisoned entries: old format, None, or all-None failed-fetch placeholders
    poisoned: list[str] = []
    for t, v in cached.items():
        if v is None:
            poisoned.append(t)
        elif isinstance(v, dict):
            if "eps_growth_rate" not in v:
                poisoned.append(t)
            elif all(v.get(k) is None for k in ("pe", "market_cap", "profit_margin", "eps_growth_rate")):
                poisoned.append(t)
    for t in poisoned:
        del cached[t]
    missing = [t for t in tickers if t not in cached]
    if missing:
        log.info("discovery: fetching FMP fundamentals for %d ticker(s)", len(missing))
        fresh = fmp_client.fetch_fundamentals(missing)
        successes: dict[str, Any] = {}
        for t in missing:
            v = fresh.get(t)
            if v is None:
                continue
            if all(v.get(k) is None for k in ("pe", "market_cap", "profit_margin", "eps_growth_rate")):
                continue
            successes[t] = v
        if successes:
            cached.update(successes)
            cache.save(cache_name, cached)
    return {t: cached.get(t) for t in tickers}
