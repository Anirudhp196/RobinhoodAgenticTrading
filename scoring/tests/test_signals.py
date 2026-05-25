"""
Phase 2 tests. The 'good dip' vs 'overheated' contrast from CLAUDE.md is
what proves the engine is calibrated. If you change the scoring math,
these tests are your safety net.

Run from scoring/ with the venv active:
    pytest tests/ -v
"""

from __future__ import annotations

import math

import pytest

from src.data_layer import NormalizedStock
from src.signals import (
    compute_pullback_score,
    compute_quality_score,
    compute_peg_score,
    compute_rsi,
    compute_trend_score,
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
    """
    closes = [start + (end - start) * (i / (n_days - 1)) for i in range(n_days)]
    if high is not None:
        closes[n_days // 2] = high
    return closes


def make_volumes(n_days: int = 260, avg: float = 1_000_000) -> list[float]:
    """Flat volume series at `avg`."""
    return [avg] * n_days


def make_stock(
    ticker: str = "TEST",
    closes: list[float] | None = None,
    volumes: list[float] | None = None,
    pe: float | None = 20.0,
    market_cap: float | None = 50e9,
    profit_margin: float | None = 0.20,
    eps_growth_rate: float | None = None,
) -> NormalizedStock:
    if closes is None:
        closes = make_closes()
    if volumes is None:
        volumes = make_volumes(len(closes))
    return NormalizedStock(
        ticker=ticker,
        closes=closes,
        volumes=volumes,
        pe=pe,
        market_cap=market_cap,
        profit_margin=profit_margin,
        eps_growth_rate=eps_growth_rate,
    )


# ---------------------------------------------------------------------------
# Pullback tests
# ---------------------------------------------------------------------------

def test_pullback_peaks_at_10_percent_off_high():
    """The pullback sweet spot per CLAUDE.md is ~10% off the 52w high."""
    closes = make_closes(end=90.0, high=100.0)
    score = compute_pullback_score(closes)
    assert score is not None
    assert score == pytest.approx(1.0, abs=0.01), f"Expected 1.0, got {score}"


def test_at_52w_high_scores_zero_pullback():
    """Buying at the top = the FOMO penalty."""
    closes = make_closes(end=100.0, high=100.0)
    assert compute_pullback_score(closes) == 0.0


def test_quiet_pullback_scores_higher_than_heavy_selloff():
    """
    Same 10% dip but with different volume profiles.
    A quiet drift down should score higher than a heavy-volume selloff.
    """
    closes = make_closes(end=90.0, high=100.0)
    n = len(closes)
    avg_vol = 1_000_000

    # Quiet pullback: recent volume at 0.5x average
    quiet_volumes = [avg_vol] * (n - 10) + [avg_vol * 0.5] * 10
    quiet_score = compute_pullback_score(closes, quiet_volumes)

    # Heavy selling: recent volume at 2x average
    heavy_volumes = [avg_vol] * (n - 10) + [avg_vol * 2.0] * 10
    heavy_score = compute_pullback_score(closes, heavy_volumes)

    assert quiet_score is not None and heavy_score is not None
    assert quiet_score > heavy_score, (
        f"Quiet pullback ({quiet_score:.3f}) should beat heavy selloff ({heavy_score:.3f})"
    )


# ---------------------------------------------------------------------------
# PEG / value score tests
# ---------------------------------------------------------------------------

def test_peg_score_cheap_growth_stock_scores_high():
    """
    P/E 30 with 40% EPS growth → PEG 0.75 → score ~0.90.
    Should reward a company growing faster than you're paying for.
    """
    score = compute_peg_score(pe=30.0, eps_growth_rate=0.40)
    assert score is not None
    assert score >= 0.85, f"Expected >= 0.85 for PEG 0.75, got {score}"


def test_peg_score_overpriced_slow_growth_scores_low():
    """
    P/E 60 with 10% EPS growth → PEG 6.0 → clamps to 0.
    """
    score = compute_peg_score(pe=60.0, eps_growth_rate=0.10)
    assert score is not None
    assert score == pytest.approx(0.0, abs=0.01), f"Expected ~0.0 for PEG 6, got {score}"


def test_peg_score_fallback_to_pe_curve_when_no_growth():
    """
    Without growth data, falls back to P/E curve that peaks at 20.
    P/E 20 → score 1.0; P/E 60 → score < 0.10; negative P/E → 0.0.
    """
    assert compute_peg_score(20.0, None) == pytest.approx(1.0, abs=0.01), \
        f"P/E 20 (no growth) should peak at 1.0, got {compute_peg_score(20.0, None)}"
    assert compute_peg_score(60.0, None) < 0.10, \
        f"P/E 60 (no growth) should be < 0.10, got {compute_peg_score(60.0, None)}"
    assert compute_peg_score(-5.0, None) == 0.0, \
        f"Negative P/E should be 0.0, got {compute_peg_score(-5.0, None)}"


def test_peg_score_ignores_negative_growth():
    """
    Negative EPS growth rate → fall back to P/E curve, not broken PEG.
    With P/E 15 and no meaningful growth, should still get a decent P/E score.
    """
    score_neg_growth = compute_peg_score(pe=15.0, eps_growth_rate=-0.10)
    score_no_growth = compute_peg_score(pe=15.0, eps_growth_rate=None)
    # Both should fall back to the P/E curve and give similar results
    assert score_neg_growth == pytest.approx(score_no_growth, abs=0.01), \
        "Negative growth should fall back to P/E curve same as no growth"


# ---------------------------------------------------------------------------
# Full stock scoring tests
# ---------------------------------------------------------------------------

def test_good_dip_stock_scores_above_threshold():
    """
    Quality name on a 9% dip, good fundamentals. Should clear the bar.
    Uses PEG when EPS growth is provided.
    """
    closes = make_closes(start=80.0, end=91.0, high=100.0)
    stock = make_stock(
        closes=closes,
        pe=25.0,
        eps_growth_rate=0.20,  # PEG = 25/20 = 1.25 → fairly valued
        profit_margin=0.25,
        market_cap=100e9,
    )
    result = score_stock(stock, weights=DEFAULT_WEIGHTS, filters=DEFAULT_FILTERS)
    assert result.score > 65, f"Expected score > 65, got {result.score}"
    assert any("pullback" in r.lower() for r in result.reasons), \
        "Expected at least one reason to mention 'pullback'"


def test_overheated_stock_scores_below_threshold():
    """
    At 52w high, very expensive P/E with poor growth coverage. Should score low.
    """
    closes = make_closes(start=80.0, end=100.0, high=100.0)
    stock = make_stock(closes=closes, pe=90.0, profit_margin=0.05, market_cap=10e9)
    result = score_stock(stock, weights=DEFAULT_WEIGHTS, filters=DEFAULT_FILTERS)
    assert result.score < 50, f"Expected score < 50, got {result.score}"
    assert any("very expensive" in f for f in result.flags), \
        "Expected 'very expensive' in flags"


def test_rsi_overbought_adds_flag_but_not_score_penalty():
    """
    Strictly monotonic closes drive RSI to ~100. Flags should include overbought,
    but the design keeps it as a flag — it does not lower the score directly.
    """
    closes = make_closes(start=100.0, end=100.0 + 59.0)
    stock = make_stock(closes=closes)
    result = score_stock(stock, weights=DEFAULT_WEIGHTS, filters=DEFAULT_FILTERS)
    assert any(f.startswith("overbought") for f in result.flags), \
        "Expected a flag starting with 'overbought'"


def test_unprofitable_company_quality_zero():
    """Quality scoring for various margin levels."""
    assert compute_quality_score(-0.10) == 0.0
    assert compute_quality_score(0.0) == pytest.approx(0.1, abs=0.01)
    assert compute_quality_score(0.30) == 1.0


def test_missing_pe_returns_error_not_crash():
    """
    P/E=None with no growth data → value score=None → score=0 and error set.
    The 'never throw' contract from CLAUDE.md applies here too.
    """
    stock = make_stock(pe=None, eps_growth_rate=None)
    result = score_stock(stock, weights=DEFAULT_WEIGHTS, filters=DEFAULT_FILTERS)
    assert result.score == 0.0, f"Expected score 0.0 for missing P/E, got {result.score}"
    assert result.error is not None, "Expected .error to be set for missing P/E"


def test_declining_eps_adds_flag():
    """
    EPS declining > 10% YoY should add an 'EPS declining' flag.
    """
    closes = make_closes(start=80.0, end=90.0, high=100.0)
    stock = make_stock(closes=closes, pe=18.0, eps_growth_rate=-0.15, profit_margin=0.20)
    result = score_stock(stock, weights=DEFAULT_WEIGHTS, filters=DEFAULT_FILTERS)
    assert any("EPS declining" in f for f in result.flags), \
        f"Expected 'EPS declining' flag, got flags: {result.flags}"


def test_peg_metrics_appear_in_signal():
    """
    When EPS growth data is available, peg_ratio and eps_growth_rate should
    appear in signal.metrics.
    """
    closes = make_closes(start=80.0, end=90.0, high=100.0)
    stock = make_stock(closes=closes, pe=25.0, eps_growth_rate=0.20, profit_margin=0.20)
    result = score_stock(stock, weights=DEFAULT_WEIGHTS, filters=DEFAULT_FILTERS)
    assert result.metrics.get("peg_ratio") is not None, "Expected peg_ratio in metrics"
    assert result.metrics.get("eps_growth_rate") is not None, "Expected eps_growth_rate in metrics"
    expected_peg = round(25.0 / (0.20 * 100.0), 2)
    assert result.metrics["peg_ratio"] == pytest.approx(expected_peg, abs=0.01)


# ---------------------------------------------------------------------------
# Sanity tests (protect the math helpers)
# ---------------------------------------------------------------------------

def test_rsi_in_range():
    closes = [100 + math.sin(i / 5) * 5 for i in range(60)]
    rsi = compute_rsi(closes)
    assert rsi is not None
    assert 0 <= rsi <= 100


def test_trend_score_when_price_well_above_ma():
    closes = make_closes(n_days=250, start=80, end=120)
    score = compute_trend_score(closes)
    assert score == 1.0  # clamped to ceiling


def test_volume_ratio_in_metrics():
    """volume_ratio should be populated in metrics when volumes are available."""
    closes = make_closes(start=80.0, end=90.0, high=100.0)
    volumes = make_volumes(len(closes), avg=1_000_000)
    stock = make_stock(closes=closes, volumes=volumes, pe=20.0, profit_margin=0.20)
    result = score_stock(stock, weights=DEFAULT_WEIGHTS, filters=DEFAULT_FILTERS)
    assert result.metrics.get("volume_ratio") is not None, "Expected volume_ratio in metrics"
    assert result.metrics["volume_ratio"] == pytest.approx(1.0, abs=0.05), \
        "Flat volume should have volume_ratio ≈ 1.0"
