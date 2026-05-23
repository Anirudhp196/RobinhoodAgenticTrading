"""
Phase 2 tests. The 'good dip' vs 'overheated' contrast from CLAUDE.md is
what proves the engine is calibrated. If you change the scoring math,
these tests are your safety net.

Run from scoring/ with the venv active:
    pytest tests/ -v

The helpers below build synthetic NormalizedStocks so you can control the
inputs precisely. Two tests are written out as examples. The rest are
TODO(anirudh) stubs — read the contract, then write the assertions.
"""

from __future__ import annotations

import math

import pytest

from src.data_layer import NormalizedStock
from src.signals import (
    compute_pullback_score,
    compute_quality_score,
    compute_rsi,
    compute_trend_score,
    compute_value_score,
    score_stock,
)

DEFAULT_WEIGHTS = {"trend": 0.30, "pullback": 0.30, "value": 0.25, "quality": 0.15}
DEFAULT_FILTERS = {"maxRsi": 75, "minMarketCap": 2e9, "maxPe": 60}


# ---------------------------------------------------------------------------
# Helpers — build synthetic stocks
# ---------------------------------------------------------------------------

def make_closes(
    n_days: int = 260,
    start: float = 100.0,
    end: float = 110.0,
    high: float | None = None,
) -> list[float]:
    """
    Build a `n_days`-long price series that linearly moves from `start` to
    `end`. Optionally inserts a `high` value somewhere in the middle so you
    can control "pct off 52w high" precisely.

    Example: make_closes(end=110, high=120) → series ends at 110 but has had
    a high of 120 within the lookback window — i.e. 8.3% off the high.
    """
    closes = [start + (end - start) * (i / (n_days - 1)) for i in range(n_days)]
    if high is not None:
        closes[n_days // 2] = high
    return closes


def make_stock(
    ticker: str = "TEST",
    closes: list[float] | None = None,
    pe: float | None = 15.0,
    market_cap: float | None = 50e9,
    profit_margin: float | None = 0.20,
) -> NormalizedStock:
    if closes is None:
        closes = make_closes()
    return NormalizedStock(
        ticker=ticker,
        closes=closes,
        pe=pe,
        market_cap=market_cap,
        profit_margin=profit_margin,
    )


# ---------------------------------------------------------------------------
# Worked examples — these PASS as written. Read them, then write your own.
# ---------------------------------------------------------------------------

def test_pullback_peaks_at_10_percent_off_high():
    """The pullback sweet spot per CLAUDE.md is ~10% off the 52w high."""
    # closes ending at 90 with a high of 100 = 10% off
    closes = make_closes(end=90.0, high=100.0)
    score = compute_pullback_score(closes)
    assert score is not None
    assert score == pytest.approx(1.0, abs=0.01), f"Expected 1.0, got {score}"


def test_at_52w_high_scores_zero_pullback():
    """Buying at the top = the FOMO penalty."""
    closes = make_closes(end=100.0, high=100.0)  # ends at the high
    assert compute_pullback_score(closes) == 0.0


# ---------------------------------------------------------------------------
# TODO(anirudh): write the following tests.
# Each docstring describes the input, what should happen, and why.
# ---------------------------------------------------------------------------

def test_good_dip_stock_scores_above_threshold():
    """
    The flagship test. Per CLAUDE.md: 'a quality name on a 9% dip scored 89/100'.
    Build a stock with:
      - 260 closes ending at 91, with a 52w high of 100   (9% pullback)
      - trending up: start at 80, end at 91  (well above 200dMA)
      - P/E of 16  (reasonable)
      - profit margin 0.25  (high quality)
      - market cap 100e9  (no small-cap flag)

    Assert score_stock(...).score > 70 (clears the threshold).
    Bonus: assert at least one reason mentions the pullback.
    """

    closes = make_closes(start=80.0, end=91.0, high=100.0)
    stock = make_stock(closes=closes, pe=16.0, profit_margin=0.25, market_cap=100e9)
    result = score_stock(stock, weights=DEFAULT_WEIGHTS, filters=DEFAULT_FILTERS)
    assert result.score > 70, f"Expected score > 70, got {result.score}"
    assert any("pullback" in reason for reason in result.reasons), "Expected at least one reason to mention 'pullback'"


def test_overheated_stock_scores_below_threshold():
    """
    The opposite case. Per CLAUDE.md: 'an overheated expensive name scored 34/100'.
    Build a stock with:
      - closes hitting a new high today (0% off the high)  → use end == high
      - P/E of 90  (very expensive — should also trigger a flag)
      - profit margin 0.05  (thin)
      - market cap 10e9

    Assert score_stock(...).score < 50.
    Assert 'very expensive' appears in flags.
    """
    closes = make_closes(start=80.0, end=100.0, high=100.0)
    stock = make_stock(closes=closes, pe=90.0, profit_margin=0.05, market_cap=10e9)
    result = score_stock(stock, weights=DEFAULT_WEIGHTS, filters=DEFAULT_FILTERS)
    assert result.score < 50, f"Expected score < 50, got {result.score}"
    assert any("very expensive" in flag for flag in result.flags), "Expected 'very expensive' in flags"

def test_rsi_overbought_adds_flag_but_not_score_penalty():
    """
    Build a stock whose closes only go up (strictly monotonic) — that drives
    RSI(14) to ~100 (overbought).

    A monotonic closes series can be: [100, 101, 102, ..., 100 + n_days - 1].

    Assert that score_stock(...).flags contains a string starting with
    'overbought'. (Don't assert anything about the score number itself —
    the design choice was 'flag, don't modify score'.)
    """

    closes = make_closes(start=100.0, end=100.0 + 59.0)  # strictly increasing
    stock = make_stock(closes=closes)
    result = score_stock(stock, weights=DEFAULT_WEIGHTS, filters=DEFAULT_FILTERS)
    assert any(flag.startswith("overbought") for flag in result.flags), "Expected a flag starting with 'overbought'"

def test_unprofitable_company_quality_zero():
    """
    compute_quality_score(-0.10)  should equal 0.0  (loss-making).
    compute_quality_score(0.0)    should be very low (~0.1).
    compute_quality_score(0.30)   should equal 1.0  (clamped above 25%).
    """

    assert compute_quality_score(-0.10) == 0.0, f"Expected 0.0 for -10% margin, got {compute_quality_score(-0.10)}"
    assert compute_quality_score(0.0) == pytest.approx(0.1, abs=0.01), f"Expected ~0.1 for 0% margin, got {compute_quality_score(0.0)}"
    assert compute_quality_score(0.30) == 1.0, f"Expected 1.0 for 30% margin (clamped), got {compute_quality_score(0.30)}"

def test_missing_data_returns_error_not_crash():
    """
    Build a stock with pe=None (FMP failure case from Phase 1). Score it.
    Assert score == 0.0 and .error is set (not None), and that nothing raised.
    The 'never throw' contract from CLAUDE.md applies here too.
    """

    stock = make_stock(pe=None)  # Simulate missing P/E data
    result = score_stock(stock, weights=DEFAULT_WEIGHTS, filters=DEFAULT_FILTERS)
    assert result.score == 0.0, f"Expected score of 0.0 for missing P/E, got {result.score}"
    assert result.error is not None, "Expected .error to be set for missing P/E data"

def test_value_score_peaks_around_pe_15():
    """
    compute_value_score(15)  should be 1.0
    compute_value_score(60)  should be < 0.10  (expensive)
    compute_value_score(-5)  should be 0.0     (negative earnings)

    These three assertions document the shape of the value curve.
    """

    assert compute_value_score(15) == 1.0, f"Expected 1.0 for P/E of 15, got {compute_value_score(15)}"
    assert compute_value_score(60) < 0.10, f"Expected < 0.10 for P/E of 60, got {compute_value_score(60)}"
    assert compute_value_score(-5) == 0.0, f"Expected 0.0 for negative P/E, got {compute_value_score(-5)}"

# ---------------------------------------------------------------------------
# Sanity tests (these don't require you to write anything; they protect
# the math helpers if you ever touch them).
# ---------------------------------------------------------------------------

def test_rsi_in_range():
    closes = [100 + math.sin(i / 5) * 5 for i in range(60)]
    rsi = compute_rsi(closes)
    assert rsi is not None
    assert 0 <= rsi <= 100


def test_trend_score_when_price_well_above_ma():
    # 250 closes climbing steadily — last price ~25% above the 200-day MA.
    closes = make_closes(n_days=250, start=80, end=120)
    score = compute_trend_score(closes)
    assert score == 1.0  # clamped to ceiling
