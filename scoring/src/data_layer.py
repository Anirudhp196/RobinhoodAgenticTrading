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
    closes: list[float] = []          # oldest -> newest; ~252 trading days
    pe: float | None = None
    market_cap: float | None = None
    profit_margin: float | None = None  # fraction (0.25 == 25%)
    error: str | None = None


def fetch_universe(tickers: list[str]) -> list[NormalizedStock]:
    """
    For each ticker, return a NormalizedStock built from (cached or fresh)
    FMP data. Never raises — bad tickers come back with .error set.
    """
    prices_by_ticker = _get_prices(tickers)
    fundamentals_by_ticker = _get_fundamentals(tickers)

    return [
        _normalize_raw_to_stock(
            ticker=t,
            closes=prices_by_ticker.get(t),
            fundamentals=fundamentals_by_ticker.get(t),
        )
        for t in tickers
    ]


# ---------------------------------------------------------------------------
# Cache-aware fetch helpers
# ---------------------------------------------------------------------------

def _get_prices(tickers: list[str]) -> dict[str, list[float] | None]:
    cache_name = f"prices_{cache.today_key()}"
    cached = cache.load(cache_name) or {}
    missing = [t for t in tickers if t not in cached]

    if missing:
        log.info("Fetching prices for %d ticker(s) from FMP", len(missing))
        fresh = fmp_client.fetch_prices(missing)
        cached.update(fresh)
        cache.save(cache_name, cached)
    else:
        log.info("All %d ticker prices served from cache", len(tickers))

    return {t: cached.get(t) for t in tickers}


def _get_fundamentals(tickers: list[str]) -> dict[str, dict[str, Any] | None]:
    cache_name = f"fundamentals_{cache.this_week_key()}"
    cached = cache.load(cache_name) or {}
    missing = [t for t in tickers if t not in cached]

    if missing:
        log.info("Fetching fundamentals for %d ticker(s) from FMP", len(missing))
        fresh = fmp_client.fetch_fundamentals(missing)
        for t in missing:
            cached[t] = fresh.get(t) or {"pe": None, "market_cap": None, "profit_margin": None}
        cache.save(cache_name, cached)
    else:
        log.info("All %d ticker fundamentals served from cache", len(tickers))

    return {t: cached.get(t) for t in tickers}


# ---------------------------------------------------------------------------
# Boundary normalization
# ---------------------------------------------------------------------------
#
# TODO(anirudh): implement this function.
#
# Contract:
#   Input:
#     - ticker: str (always present)
#     - closes: list[float] | None   <-- may be None or [] if FMP failed
#     - fundamentals: dict | None    <-- may be None, or a dict with keys
#                                        "pe", "market_cap", "profit_margin"
#                                        whose values may themselves be None
#   Output:
#     - NormalizedStock with sensible defaults + .error set when data is unusable
#
# Rules (these are the CLAUDE.md "validate at the boundary" rule in practice):
#   1. If closes is None or empty -> return NormalizedStock(ticker=ticker,
#      error="no price data"). Other fields can stay defaults.
#   2. Otherwise: only keep finite float closes (filter out anything that's
#      not a number). If after filtering you have fewer than 50 closes, treat
#      it like no-price-data and set error="insufficient history".
#   3. Pull pe, market_cap, profit_margin from fundamentals if it's a dict;
#      otherwise leave them as None. Do NOT raise if a field is missing.
#   4. If everything is fine, error stays None.
#
# Why this is your function: this is the *exact* boundary between the messy
# outside world and our clean domain type. Every Java/TS app you'll write
# has one of these; getting comfortable writing it defensively in Python
# is the point.
#
# When you're done, the smoke test in scripts/smoke_test.py will exercise it.

def _normalize_raw_to_stock(
    ticker: str,
    closes: list[float] | None,
    fundamentals: dict[str, Any] | None,
) -> NormalizedStock:
    if not closes:
        return NormalizedStock(ticker=ticker, error="no price data")
    finite_closes = [c for c in closes if isinstance(c, (int, float)) and math.isfinite(c)]
    if len(finite_closes) < 50:
        return NormalizedStock(ticker=ticker, error="insufficient history")
    f = fundamentals if isinstance(fundamentals, dict) else {}
    return NormalizedStock(
        ticker=ticker,
        closes=finite_closes,
        pe=f.get("pe"),
        market_cap=f.get("market_cap"),
        profit_margin=f.get("profit_margin"),
    )