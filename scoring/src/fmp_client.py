"""
FMP HTTP client. Only knows about FMP's URLs and JSON shapes.
Returns plain dicts; domain types live in data_layer.py.

Note on FMP tiers (May 2026): the legacy /api/v3/ endpoints are paywalled.
The free tier uses /stable/ endpoints, and multi-symbol batching is paid-only.
So all fetches are per-ticker. The weekly fundamentals cache is what keeps
the daily call count low.

Never raises on HTTP/JSON errors. Returns None for that ticker so one
bad symbol does not kill a whole refresh (CLAUDE.md "never throw" rule).
"""

from __future__ import annotations

import logging
import os
from datetime import date, timedelta
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

FMP_BASE = "https://financialmodelingprep.com/stable"
_API_KEY = os.environ.get("FMP_API_KEY")
_TIMEOUT = httpx.Timeout(15.0)


def _require_key() -> str:
    if not _API_KEY:
        raise RuntimeError(
            "FMP_API_KEY not set. Copy scoring/.env.example to scoring/.env "
            "and paste your key."
        )
    return _API_KEY


def _get(path: str, params: dict[str, Any] | None = None) -> Any | None:
    """GET helper. Returns parsed JSON, or None on any failure."""
    params = {**(params or {}), "apikey": _require_key()}
    try:
        r = httpx.get(f"{FMP_BASE}{path}", params=params, timeout=_TIMEOUT)
        r.raise_for_status()
        return r.json()
    except (httpx.HTTPError, ValueError) as e:
        log.warning("FMP GET %s failed: %s", path, e)
        return None


def fetch_prices(tickers: list[str]) -> dict[str, list[float] | None]:
    """
    Returns {ticker: [close, close, ...] oldest -> newest} or None per ticker.
    One call per ticker (free tier does not support batching).
    """
    return {t: _fetch_prices_single(t) for t in tickers}


def _fetch_prices_single(ticker: str) -> list[float] | None:
    """~1 year of daily closes via /stable/historical-price-eod/light."""
    today = date.today()
    raw = _get(
        "/historical-price-eod/light",
        {
            "symbol": ticker,
            "from": (today - timedelta(days=400)).isoformat(),
            "to": today.isoformat(),
        },
    )
    if not isinstance(raw, list) or not raw:
        return None
    # API returns newest -> oldest; we want oldest -> newest.
    closes: list[float] = []
    for row in reversed(raw):
        if not isinstance(row, dict):
            continue
        # /stable/ uses "price" for the EOD light endpoint (vs "close" on legacy).
        v = _maybe_float(row.get("price"))
        if v is not None:
            closes.append(v)
    return closes or None


def fetch_fundamentals(tickers: list[str]) -> dict[str, dict[str, Any] | None]:
    """
    Returns {ticker: {"pe", "market_cap", "profit_margin"}} or None.
    Two calls per ticker:
      - /ratios-ttm    -> pe (priceToEarningsRatioTTM) + profit_margin
      - /key-metrics-ttm -> market_cap
    """
    return {t: _fetch_fundamentals_single(t) for t in tickers}


def _fetch_fundamentals_single(ticker: str) -> dict[str, Any] | None:
    ratios = _get("/ratios-ttm", {"symbol": ticker})
    metrics = _get("/key-metrics-ttm", {"symbol": ticker})

    pe: float | None = None
    profit_margin: float | None = None
    if isinstance(ratios, list) and ratios and isinstance(ratios[0], dict):
        pe = _maybe_float(ratios[0].get("priceToEarningsRatioTTM"))
        profit_margin = _maybe_float(ratios[0].get("netProfitMarginTTM"))

    market_cap: float | None = None
    if isinstance(metrics, list) and metrics and isinstance(metrics[0], dict):
        market_cap = _maybe_float(metrics[0].get("marketCap"))

    if pe is None and profit_margin is None and market_cap is None:
        return None  # both endpoints failed
    return {"pe": pe, "market_cap": market_cap, "profit_margin": profit_margin}


def _maybe_float(v: Any) -> float | None:
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    # Reject NaN/inf early — CLAUDE.md rule
    if f != f or f in (float("inf"), float("-inf")):
        return None
    return f
