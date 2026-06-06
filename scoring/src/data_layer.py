"""
Phase 1 orchestrator. Public API for Phase 2 (scoring).

Combines the FMP client and the cache to return NormalizedStock objects.
Callers should treat NormalizedStock.error as the never-throw signal:
if error is set, the other fields may be missing or partial.
"""

from __future__ import annotations

import logging
import math
from typing import Any

from pydantic import BaseModel

from . import cache, fmp_client

log = logging.getLogger(__name__)


class NormalizedStock(BaseModel):
    ticker: str
    closes: list[float] = []           # oldest -> newest; ~252 trading days
    volumes: list[float] = []          # parallel to closes; 0.0 where unavailable
    pe: float | None = None
    market_cap: float | None = None
    profit_margin: float | None = None  # fraction (0.25 == 25%)
    eps_growth_rate: float | None = None  # YoY EPS growth, fraction (0.15 == 15%)
    error: str | None = None


def fetch_universe(tickers: list[str]) -> list[NormalizedStock]:
    """
    For each ticker, return a NormalizedStock built from (cached or fresh)
    FMP data. Never raises — bad tickers come back with .error set.
    """
    ohlcv_by_ticker = _get_ohlcv(tickers)
    fundamentals_by_ticker = _get_fundamentals(tickers)

    return [
        _normalize_raw_to_stock(
            ticker=t,
            ohlcv=ohlcv_by_ticker.get(t),
            fundamentals=fundamentals_by_ticker.get(t),
        )
        for t in tickers
    ]


def fetch_spy_regime() -> dict[str, Any]:
    """
    Returns whether SPY is above its 200-day MA today.
    { "above_200ma": bool | None, "spy_price": float, "spy_ma200": float }
    None means data was unavailable — treat as unknown, not as a bear market.
    Cached daily so this costs 1 API call/day.

    Only caches successful results — a failed fetch returns "unknown" but
    does not poison the cache, so the next call will retry.
    """
    cache_name = f"spy_regime_{cache.today_key()}"
    cached = cache.load(cache_name)
    if cached is not None and cached.get("above_200ma") is not None:
        return cached

    ohlcv = fmp_client.fetch_ohlcv(["SPY"])
    spy_data = ohlcv.get("SPY")
    if not spy_data or not spy_data.get("closes") or len(spy_data["closes"]) < 200:
        log.warning("SPY data unavailable — regime unknown (not cached)")
        return {"above_200ma": None, "spy_price": None, "spy_ma200": None}

    closes = spy_data["closes"]
    ma200 = sum(closes[-200:]) / 200.0
    current = closes[-1]
    result: dict[str, Any] = {
        "above_200ma": current > ma200,
        "spy_price": round(current, 2),
        "spy_ma200": round(ma200, 2),
    }
    cache.save(cache_name, result)
    return result


# ---------------------------------------------------------------------------
# Cache-aware fetch helpers
# ---------------------------------------------------------------------------

def _get_ohlcv(tickers: list[str]) -> dict[str, dict[str, list[float]] | None]:
    """
    Returns {ticker: {"closes": [...], "volumes": [...]}} or None per ticker.
    Cached daily. Detects old list-format cache entries and re-fetches them.

    IMPORTANT: failed fetches are NOT cached. If FMP returns null/None for a
    ticker (rate limit, bad symbol, etc.), we leave it out of the cache so
    the next call retries. Caching failures poisons the cache for the rest
    of the day.
    """
    cache_name = f"prices_{cache.today_key()}"
    cached = cache.load(cache_name) or {}

    # Evict any poisoned entries: old list-format and any null values from
    # previously-cached failures.
    poisoned = [t for t, v in cached.items() if v is None or isinstance(v, list)]
    if poisoned:
        log.info("Evicting %d poisoned/old price cache entries", len(poisoned))
        for t in poisoned:
            del cached[t]

    missing = [t for t in tickers if t not in cached]
    if missing:
        log.info("Fetching OHLCV for %d ticker(s) from FMP", len(missing))
        fresh = fmp_client.fetch_ohlcv(missing)
        # Only cache successful fetches — never persist None.
        successes = {t: v for t, v in fresh.items() if v is not None}
        if successes:
            cached.update(successes)
            cache.save(cache_name, cached)
        if len(successes) < len(missing):
            failed = [t for t in missing if t not in successes]
            log.warning("OHLCV fetch failed for %d ticker(s): %s", len(failed), failed[:5])
    else:
        log.info("All %d ticker prices served from cache", len(tickers))

    return {t: cached.get(t) for t in tickers}


def _get_fundamentals(tickers: list[str]) -> dict[str, dict[str, Any] | None]:
    """
    Returns {ticker: {"pe", "market_cap", "profit_margin", "eps_growth_rate"}} or None.
    Cached weekly. Re-fetches entries that are missing eps_growth_rate (old format).

    IMPORTANT: failed fetches are NOT cached. If FMP fails for a ticker, we
    leave it out so the next call retries. Caching failures poisons the cache
    for the rest of the week.
    """
    cache_name = f"fundamentals_{cache.this_week_key()}"
    cached = cache.load(cache_name) or {}

    # Evict poisoned entries: anything missing eps_growth_rate (old format),
    # anything that's None, or anything where every field is None (a failed
    # fetch we wrote as a placeholder before this fix).
    poisoned = []
    for t, v in cached.items():
        if v is None:
            poisoned.append(t)
        elif isinstance(v, dict):
            if "eps_growth_rate" not in v:
                poisoned.append(t)
            elif all(v.get(k) is None for k in ("pe", "market_cap", "profit_margin", "eps_growth_rate")):
                poisoned.append(t)
    if poisoned:
        log.info("Evicting %d poisoned fundamentals cache entries", len(poisoned))
        for t in poisoned:
            del cached[t]

    missing = [t for t in tickers if t not in cached]

    if missing:
        log.info("Fetching fundamentals for %d ticker(s) from FMP", len(missing))
        fresh = fmp_client.fetch_fundamentals(missing)
        # Only cache successful fetches — never persist a None or all-None placeholder.
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
        if len(successes) < len(missing):
            failed = [t for t in missing if t not in successes]
            log.warning("Fundamentals fetch failed for %d ticker(s): %s", len(failed), failed[:5])
    else:
        log.info("All %d ticker fundamentals served from cache", len(tickers))

    return {t: cached.get(t) for t in tickers}


# ---------------------------------------------------------------------------
# Boundary normalization
# ---------------------------------------------------------------------------

def _normalize_raw_to_stock(
    ticker: str,
    ohlcv: dict[str, list[float]] | None,
    fundamentals: dict[str, Any] | None,
) -> NormalizedStock:
    """
    Maps raw FMP data to NormalizedStock. Validates at the boundary:
    - Missing / empty OHLCV → error, no partial scores
    - Fewer than 50 finite closes → error
    - Individual None fundamentals are allowed (scoring handles them gracefully)
    """
    if not ohlcv or not ohlcv.get("closes"):
        return NormalizedStock(ticker=ticker, error="no price data")

    raw_closes = ohlcv["closes"]
    raw_volumes = ohlcv.get("volumes", [])

    finite_closes = [
        c for c in raw_closes
        if isinstance(c, (int, float)) and math.isfinite(c)
    ]
    if len(finite_closes) < 50:
        return NormalizedStock(ticker=ticker, error="insufficient history")

    # Keep volumes aligned with closes after filtering (use 0.0 for missing slots)
    # Simplest safe approach: if lengths match after filtering, keep; otherwise rebuild.
    if len(raw_volumes) == len(raw_closes):
        finite_volumes = [
            v if isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 else 0.0
            for v in raw_volumes
        ]
        # Re-align: only keep volumes corresponding to finite close indices
        paired = [
            (c, v) for c, v in zip(raw_closes, raw_volumes)
            if isinstance(c, (int, float)) and math.isfinite(c)
        ]
        finite_volumes = [v if isinstance(v, (int, float)) and math.isfinite(v) and v >= 0 else 0.0
                         for _, v in paired]
    else:
        finite_volumes = [0.0] * len(finite_closes)

    f = fundamentals if isinstance(fundamentals, dict) else {}
    return NormalizedStock(
        ticker=ticker,
        closes=finite_closes,
        volumes=finite_volumes,
        pe=f.get("pe"),
        market_cap=f.get("market_cap"),
        profit_margin=f.get("profit_margin"),
        eps_growth_rate=f.get("eps_growth_rate"),
    )
