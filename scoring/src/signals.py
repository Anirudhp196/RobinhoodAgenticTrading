"""
Phase 2 — Scoring layer.

Pure functions, no I/O. Input: NormalizedStock. Output: Signal.

Design (matches CLAUDE.md):
  - 4 weighted components: trend, pullback, value, quality. Each maps to [0, 1].
  - Final score = 100 * weighted sum. Threshold default 70.
  - Risk filters (RSI>75, P/E>60, small cap) add *flags* only; they do not
    modify the score. The user sees both and decides.
  - Reasons[] are human-readable explanations attached to every signal so
    nothing is a black box.

Every public function is intentionally easy to test in isolation. Pass in
synthetic closes / pe / margin values directly. No globals.
"""

from __future__ import annotations

from typing import Iterable

from pydantic import BaseModel

from .data_layer import NormalizedStock


# ---------------------------------------------------------------------------
# Output type
# ---------------------------------------------------------------------------

class Signal(BaseModel):
    ticker: str
    score: float                          # 0-100
    reasons: list[str] = []
    flags: list[str] = []
    metrics: dict[str, float | None] = {}  # rsi, pct_from_high, ma200, etc.
    error: str | None = None              # set if the stock could not be scored


# ---------------------------------------------------------------------------
# Component scores (each returns 0..1)
# ---------------------------------------------------------------------------

def compute_trend_score(closes: list[float]) -> float | None:
    """
    Linear ramp from 5% below the 200-day MA (score 0) to 5% above (score 1).
    Crossing the MA exactly is 0.5. Returns None if there isn't 200 days of
    data to compute the MA.
    """
    if len(closes) < 200:
        return None
    ma200 = sum(closes[-200:]) / 200.0
    if ma200 <= 0:
        return None
    ratio = closes[-1] / ma200
    return _clamp((ratio - 0.95) / 0.10, 0.0, 1.0)


def compute_pullback_score(closes: list[float]) -> float | None:
    """
    Reward modest pullbacks on the way up, penalize buying at the top.

    pct off 52w high -> score:
      0%  -> 0.0  (at the top: 'FOMO penalty')
      5%  -> 0.7
      10% -> 1.0  (peak: doc's sweet spot)
      15% -> 0.7
      25% -> 0.2  (deep drawdown — investigate)
      40% -> 0.0  (broken / falling knife)

    Linear interpolation between waypoints.
    """
    if not closes:
        return None
    high52 = max(closes[-252:]) if len(closes) >= 252 else max(closes)
    if high52 <= 0:
        return None
    pct_off = (high52 - closes[-1]) / high52
    return _piecewise_linear(
        pct_off,
        [(0.00, 0.0), (0.05, 0.7), (0.10, 1.0), (0.15, 0.7),
         (0.25, 0.2), (0.40, 0.0)],
    )


def compute_value_score(pe: float | None) -> float | None:
    """
    Peak around P/E = 15. Tapers off both sides; bottoms out by P/E ~ 80.
    Negative or zero P/E (losing money / no earnings) returns 0.0
    (not None — losing money is a *known* low-value signal).
    """
    if pe is None:
        return None
    if pe <= 0:
        return 0.0
    return _piecewise_linear(
        pe,
        [(0, 0.30), (10, 0.85), (15, 1.00), (20, 0.85),
         (30, 0.50), (50, 0.10), (80, 0.00)],
    )


def compute_quality_score(profit_margin: float | None) -> float | None:
    """
    Ramps up through 25% net margin, then flat at 1.0.
    Unprofitable (margin <= 0) scores 0.0.
    """
    if profit_margin is None:
        return None
    if profit_margin < 0:
        return 0.0  # unprofitable -> hard zero
    return _piecewise_linear(
        profit_margin,
        [(0.0, 0.10), (0.05, 0.40), (0.15, 0.80),
         (0.25, 1.00), (1.0, 1.00)],
    )


def compute_rsi(closes: list[float], period: int = 14) -> float | None:
    """
    Wilder's RSI. Returns a value in [0, 100], or None if not enough data.

    Wilder smoothing is the textbook version:
      1) Seed avg_gain / avg_loss with the simple mean of the first `period`
         changes.
      2) For each subsequent change, blend:
           avg = (avg * (period - 1) + new) / period
      3) RSI = 100 - 100 / (1 + avg_gain / avg_loss)
    """
    if len(closes) < period + 1:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(closes)):
        delta = closes[i] - closes[i - 1]
        gains.append(max(delta, 0.0))
        losses.append(max(-delta, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def score_stock(
    stock: NormalizedStock,
    weights: dict[str, float],
    filters: dict[str, float],
) -> Signal:
    """
    Combine component scores into a final 0-100 score plus reasons and flags.
    Never raises. If the input is unusable, returns a Signal with score=0 and
    error set.
    """
    if stock.error:
        return Signal(ticker=stock.ticker, score=0.0, error=stock.error)

    trend = compute_trend_score(stock.closes)
    pullback = compute_pullback_score(stock.closes)
    value = compute_value_score(stock.pe)
    quality = compute_quality_score(stock.profit_margin)
    rsi = compute_rsi(stock.closes)

    components = {"trend": trend, "pullback": pullback, "value": value, "quality": quality}
    if any(v is None for v in components.values()):
        missing = [k for k, v in components.items() if v is None]
        return Signal(
            ticker=stock.ticker,
            score=0.0,
            error=f"missing components: {','.join(missing)}",
        )

    weighted = sum(components[k] * weights.get(k, 0.0) for k in components)
    score = round(100.0 * weighted, 1)

    # Metrics (for the UI detail panel)
    high52 = max(stock.closes[-252:]) if len(stock.closes) >= 252 else max(stock.closes)
    ma200 = sum(stock.closes[-200:]) / 200.0 if len(stock.closes) >= 200 else None
    pct_from_high = (high52 - stock.closes[-1]) / high52 if high52 > 0 else None
    metrics: dict[str, float | None] = {
        "rsi": round(rsi, 1) if rsi is not None else None,
        "pct_from_high": round(pct_from_high, 4) if pct_from_high is not None else None,
        "ma200": round(ma200, 2) if ma200 is not None else None,
        "current_price": round(stock.closes[-1], 2),
    }

    reasons = _build_reasons(stock, components, metrics)
    flags = _build_flags(stock, rsi, filters)

    return Signal(
        ticker=stock.ticker,
        score=score,
        reasons=reasons,
        flags=flags,
        metrics=metrics,
    )


def score_universe(
    stocks: Iterable[NormalizedStock],
    weights: dict[str, float],
    filters: dict[str, float],
) -> list[Signal]:
    """Score every stock, return list sorted by score descending."""
    signals = [score_stock(s, weights, filters) for s in stocks]
    return sorted(signals, key=lambda s: s.score, reverse=True)


# ---------------------------------------------------------------------------
# Reason + flag builders
# ---------------------------------------------------------------------------

def _build_reasons(
    stock: NormalizedStock,
    components: dict[str, float],
    metrics: dict[str, float | None],
) -> list[str]:
    reasons: list[str] = []

    ma200 = metrics["ma200"]
    price = metrics["current_price"]
    if ma200 is not None and price is not None:
        pct = (price - ma200) / ma200 * 100
        if components["trend"] >= 0.8:
            reasons.append(f"Trading {pct:+.1f}% vs 200-day MA — healthy uptrend")
        elif components["trend"] <= 0.2:
            reasons.append(f"Trading {pct:+.1f}% vs 200-day MA — broken trend")

    pct_high = metrics["pct_from_high"]
    if pct_high is not None:
        p = pct_high * 100
        if 0.05 <= pct_high <= 0.15:
            reasons.append(f"{p:.1f}% off 52w high — sweet-spot pullback")
        elif pct_high < 0.02:
            reasons.append(f"Only {p:.1f}% off 52w high — buying the top")
        elif pct_high > 0.20:
            reasons.append(f"{p:.1f}% off 52w high — deep drawdown, investigate")

    if stock.pe is not None:
        if 10 <= stock.pe <= 20:
            reasons.append(f"P/E of {stock.pe:.1f} — reasonable valuation")
        elif stock.pe > 40:
            reasons.append(f"P/E of {stock.pe:.1f} — expensive")
        elif stock.pe <= 0:
            reasons.append("Negative P/E — unprofitable")

    if stock.profit_margin is not None:
        m = stock.profit_margin * 100
        if stock.profit_margin >= 0.20:
            reasons.append(f"{m:.0f}% profit margin — high-quality earnings")
        elif stock.profit_margin < 0.05:
            reasons.append(f"{m:.0f}% profit margin — thin or no profits")

    return reasons


def _build_flags(
    stock: NormalizedStock,
    rsi: float | None,
    filters: dict[str, float],
) -> list[str]:
    flags: list[str] = []
    if rsi is not None and rsi > filters.get("maxRsi", 75):
        flags.append(f"overbought (RSI {rsi:.0f})")
    if stock.pe is not None and stock.pe > filters.get("maxPe", 60):
        flags.append(f"very expensive (P/E {stock.pe:.0f})")
    if stock.market_cap is not None and stock.market_cap < filters.get("minMarketCap", 2e9):
        flags.append("small cap")
    return flags


# ---------------------------------------------------------------------------
# Math helpers
# ---------------------------------------------------------------------------

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def _piecewise_linear(x: float, waypoints: list[tuple[float, float]]) -> float:
    """
    Linear interpolation across a sorted list of (x, y) waypoints.
    Outside the range, clamps to the nearest endpoint y.
    """
    if x <= waypoints[0][0]:
        return waypoints[0][1]
    if x >= waypoints[-1][0]:
        return waypoints[-1][1]
    for (x0, y0), (x1, y1) in zip(waypoints, waypoints[1:]):
        if x0 <= x <= x1:
            t = (x - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return 0.0  # unreachable
