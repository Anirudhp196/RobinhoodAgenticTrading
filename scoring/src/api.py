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
    _get_prices,
    _normalize_raw_to_stock,
    fetch_universe,
)
from .signals import Signal, score_stock, score_universe

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

    # Persist score history for non-errored signals
    cache.append_score_history(
        {s.ticker: s.score for s in signals if s.error is None}
    )

    return _payload_for_signals(signals, cfg)


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


@app.post("/refresh")
def refresh() -> dict[str, Any]:
    """Force a fresh fetch by clearing today's price cache."""
    cache_name = f"prices_{cache.today_key()}"
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

def _payload_for_signals(signals: list[Signal], cfg: dict[str, Any]) -> dict[str, Any]:
    threshold = cfg.get("signalThreshold", 70)
    qualified = [s for s in signals if s.error is None and s.score >= threshold]
    return {
        "generated_at": cache.today_key(),
        "threshold": threshold,
        "verdict": (
            f"{len(qualified)} name(s) clear the bar"
            if qualified
            else "Nothing meets the bar today. Hold."
        ),
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
    prices = _get_prices(tickers)
    fundamentals = _get_fundamentals(tickers)

    signals: list[Signal] = []
    for i, ticker in enumerate(tickers, start=1):
        stock = _normalize_raw_to_stock(
            ticker=ticker,
            closes=prices.get(ticker),
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
    yield _sse({"type": "done", "payload": _payload_for_signals(signals, cfg)})


def _sse(event: dict[str, Any]) -> bytes:
    return f"data: {json.dumps(event)}\n\n".encode("utf-8")
