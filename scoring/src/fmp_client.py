"""
FMP HTTP client. Only knows about FMP's URLs and JSON shapes.
Returns plain dicts; domain types live in data_layer.py.

Note on FMP tiers (May 2026): the legacy /api/v3/ endpoints are paywalled.
The free tier uses /stable/ endpoints, and multi-symbol batching is paid-only.
So all fetches are per-ticker. The weekly fundamentals cache is what keeps
the daily call count low.

Never raises on HTTP/JSON errors. Returns None for that ticker so one
bad symbol does not kill a whole refresh (CLAUDE.md "never throw" rule).

Call budget per day (free tier: 250):
  - 1 call/ticker/day  for OHLCV prices (watchlist ~16 + discovery ~30)
  - 3 calls/ticker/week for fundamentals (pe+margin, market_cap, eps_growth)
  - 1 call/day for SPY regime check
  Typical: ~47 price + ~21 fundamentals amortized + 1 spy ≈ 69/day
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


# ---------------------------------------------------------------------------
# OHLCV prices (replaces the old close-only "prices" fetch)
# ---------------------------------------------------------------------------

def fetch_ohlcv(tickers: list[str]) -> dict[str, dict[str, list[float]] | None]:
    """
    Returns {ticker: {"closes": [...], "volumes": [...]}} or None per ticker.
    Both lists are oldest -> newest, same length.
    Uses the full EOD endpoint (not /light) to get volume data.
    """
    return {t: _fetch_ohlcv_single(t) for t in tickers}


def _fetch_ohlcv_single(ticker: str) -> dict[str, list[float]] | None:
    """
    ~1 year of daily prices via /stable/historical-price-eod/light (free tier).

    The /light endpoint returns rows shaped like:
        {"symbol": "AAPL", "date": "2026-05-23", "price": 180.5, "volume": 50000000}
    Volume is included on the free tier — confirmed by inspecting live responses.
    The non-light /historical-price-eod endpoint is paid-tier (returns 404 on free).
    """
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

    closes: list[float] = []
    volumes: list[float] = []

    for row in reversed(raw):  # API returns newest -> oldest; reverse to oldest -> newest
        if not isinstance(row, dict):
            continue
        c = _maybe_float(row.get("price") or row.get("close") or row.get("adjClose"))
        v = _maybe_float(row.get("volume") or row.get("unadjustedVolume"))
        if c is not None:
            closes.append(c)
            volumes.append(v if v is not None and v > 0 else 0.0)

    if not closes:
        return None
    return {"closes": closes, "volumes": volumes}


# ---------------------------------------------------------------------------
# Fundamentals (pe, market_cap, profit_margin, eps_growth_rate)
# ---------------------------------------------------------------------------

def fetch_fundamentals(tickers: list[str]) -> dict[str, dict[str, Any] | None]:
    """
    Returns {ticker: {"pe", "market_cap", "profit_margin", "eps_growth_rate"}} or None.
    Three calls per ticker (cached weekly so this is cheap over time):
      - /ratios-ttm        -> pe + profit_margin
      - /key-metrics-ttm   -> market_cap
      - /financial-growth  -> eps_growth_rate (YoY, as a fraction e.g. 0.15 = 15%)
    """
    return {t: _fetch_fundamentals_single(t) for t in tickers}


def _fetch_fundamentals_single(ticker: str) -> dict[str, Any] | None:
    ratios = _get("/ratios-ttm", {"symbol": ticker})
    metrics = _get("/key-metrics-ttm", {"symbol": ticker})
    growth = _get("/financial-growth", {"symbol": ticker, "limit": 1})

    pe: float | None = None
    profit_margin: float | None = None
    if isinstance(ratios, list) and ratios and isinstance(ratios[0], dict):
        pe = _maybe_float(ratios[0].get("priceToEarningsRatioTTM"))
        profit_margin = _maybe_float(ratios[0].get("netProfitMarginTTM"))

    market_cap: float | None = None
    if isinstance(metrics, list) and metrics and isinstance(metrics[0], dict):
        market_cap = _maybe_float(metrics[0].get("marketCap"))

    eps_growth_rate: float | None = None
    if isinstance(growth, list) and growth and isinstance(growth[0], dict):
        # FMP field is "epsgrowth" (annual YoY EPS growth as a fraction)
        raw_growth = growth[0].get("epsgrowth") or growth[0].get("epsGrowth")
        eps_growth_rate = _maybe_float(raw_growth)

    if pe is None and profit_margin is None and market_cap is None:
        return None  # all endpoints failed
    return {
        "pe": pe,
        "market_cap": market_cap,
        "profit_margin": profit_margin,
        "eps_growth_rate": eps_growth_rate,
    }


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
