"""
FastAPI surface for the scoring service.

Endpoints:
  GET  /health             — liveness
  GET  /screen             — full ranked screen for today's universe
  GET  /screen/{ticker}    — single ticker detail + score history
  POST /refresh            — clear today's cache and re-run
  GET  /stream             — SSE: progress events as each ticker is scored
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from . import cache
from .config import load_config
from .data_layer import (
    _get_fundamentals,
    _get_ohlcv,
    _normalize_raw_to_stock,
    fetch_spy_regime,
    fetch_universe,
)
from .discovery import (
    SLICES,
    get_all_discovery_signals,
    run_rolling_scan,
    today_slice_index,
    todays_tickers,
)
from .signals import Signal, score_stock, score_universe
from .sp500 import load_sp500

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Screener Scoring Service")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    service: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="scoring")


@app.get("/screen")
def screen() -> dict[str, Any]:
    """Run (or serve from cache) today's screen for the configured universe."""
    cfg = load_config()
    stocks = fetch_universe(cfg["universe"])
    signals = score_universe(stocks, cfg["weights"], cfg["riskFilters"])
    regime = fetch_spy_regime()

    # Persist score history for non-errored signals
    cache.append_score_history(
        {s.ticker: s.score for s in signals if s.error is None}
    )

    return _payload_for_signals(signals, cfg, regime)


@app.get("/screen/{ticker}")
def screen_one(ticker: str) -> dict[str, Any]:
    cfg = load_config()
    ticker = ticker.upper()
    if ticker not in [t.upper() for t in cfg["universe"]]:
        raise HTTPException(status_code=404, detail=f"{ticker} not in universe")

    stocks = fetch_universe([ticker])
    if not stocks:
        raise HTTPException(status_code=502, detail="failed to fetch")
    signal = score_stock(stocks[0], cfg["weights"], cfg["riskFilters"])
    history = cache.load_score_history().get(ticker, [])

    return {
        "signal": signal.model_dump(),
        "history": history,
    }


@app.get("/discover")
def discover() -> dict[str, Any]:
    """
    Rolling S&P 500 scan. Each call scores today's slice (~50 tickers) via FMP
    and merges into a persistent discovery store. Returns the union of all
    scored tickers, sorted by score. Full S&P 500 coverage takes ~10 days
    to bootstrap.
    """
    cfg = load_config()
    disc_cfg = cfg.get("discovery", {})
    top_n = int(disc_cfg.get("topN", 15))
    threshold = cfg.get("signalThreshold", 70)

    # Run today's slice if we haven't already today.
    store = cache.load("discovery_scores") or {}
    universe = load_sp500()
    if not universe:
        raise HTTPException(status_code=502, detail="S&P 500 list unavailable")
    slice_today = todays_tickers(universe)
    today = cache.today_key()
    already_done = all(
        store.get(t, {}).get("last_scored") == today for t in slice_today
    )
    if not already_done:
        run_rolling_scan(cfg["weights"], cfg["riskFilters"])

    entries = get_all_discovery_signals()
    qualifiers = [
        e for e in entries
        if e["signal"].get("error") is None and e["signal"].get("score", 0) >= threshold
    ]
    top = qualifiers[:top_n]
    return {
        "generated_at": today,
        "threshold": threshold,
        "universe_size": len(universe),
        "scored_count": len(entries),
        "qualifiers_count": len(qualifiers),
        "slice_today": today_slice_index() + 1,
        "total_slices": SLICES,
        "verdict": (
            f"{len(qualifiers)} of {len(entries)} scored names clear the bar — showing top {len(top)}"
            if qualifiers
            else f"Nothing in {len(entries)} scored names clears the bar. Hold."
        ),
        "entries": [
            {**e["signal"], "last_scored": e["last_scored"]}
            for e in top
        ],
    }


@app.post("/refresh")
def refresh() -> dict[str, Any]:
    """Force a fresh fetch by clearing today's price and regime caches."""
    for cache_name in [f"prices_{cache.today_key()}", f"spy_regime_{cache.today_key()}"]:
        path = cache.CACHE_DIR / f"{cache_name}.json"
        if path.exists():
            path.unlink()
    return screen()


@app.get("/stream")
async def stream() -> StreamingResponse:
    """SSE stream of progress events as each ticker is fetched + scored."""
    return StreamingResponse(_stream_events(), media_type="text/event-stream")


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------

def _payload_for_signals(
    signals: list[Signal],
    cfg: dict[str, Any],
    regime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    threshold = cfg.get("signalThreshold", 65)
    qualified = [s for s in signals if s.error is None and s.score >= threshold]

    regime = regime or {}
    above_200ma = regime.get("above_200ma")

    if above_200ma is False:
        # Bear market: surface any qualifiers but warn loudly
        verdict = (
            "⚠ SPY is below its 200-day MA — market in downtrend. "
            + (f"{len(qualified)} name(s) clear the bar, but caution is warranted."
               if qualified
               else "Nothing meets the bar. Hold — especially in a downtrend.")
        )
    elif qualified:
        verdict = f"{len(qualified)} name(s) clear the bar"
    else:
        verdict = "Nothing meets the bar today. Hold."

    return {
        "generated_at": cache.today_key(),
        "threshold": threshold,
        "market_regime": {
            "above_200ma": above_200ma,
            "spy_price": regime.get("spy_price"),
            "spy_ma200": regime.get("spy_ma200"),
        },
        "verdict": verdict,
        "signals": [s.model_dump() for s in signals],
    }


async def _stream_events() -> AsyncIterator[bytes]:
    """Score the universe one ticker at a time, yielding SSE events."""
    cfg = load_config()
    tickers = cfg["universe"]
    total = len(tickers)

    yield _sse({"type": "start", "total": total})
    await asyncio.sleep(0)

    # Warm caches in one pass; per-ticker loop below then never hits the network.
    ohlcv = _get_ohlcv(tickers)
    fundamentals = _get_fundamentals(tickers)

    signals: list[Signal] = []
    for i, ticker in enumerate(tickers, start=1):
        stock = _normalize_raw_to_stock(
            ticker=ticker,
            ohlcv=ohlcv.get(ticker),
            fundamentals=fundamentals.get(ticker),
        )
        sig = score_stock(stock, cfg["weights"], cfg["riskFilters"])
        signals.append(sig)
        yield _sse({
            "type": "progress",
            "done": i,
            "total": total,
            "ticker": ticker,
            "score": sig.score,
        })
        await asyncio.sleep(0)

    signals.sort(key=lambda s: s.score, reverse=True)
    cache.append_score_history(
        {s.ticker: s.score for s in signals if s.error is None}
    )
    regime = fetch_spy_regime()
    yield _sse({"type": "done", "payload": _payload_for_signals(signals, cfg, regime)})


def _sse(event: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(event)}\n\n".encode("utf-8")
