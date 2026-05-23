"""
Phase 1 smoke test. Fetches 3 tickers, prints the normalized objects.
Eyeball check: closes length looks like ~1yr (~252), pe/market_cap/profit_margin
are sensible floats, no .error on healthy names.

Run from the scoring/ directory with the venv activated:
    python scripts/smoke_test.py
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

# Allow running as a script: add scoring/ to sys.path so `src` resolves.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data_layer import fetch_universe  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

TICKERS = ["AAPL", "AMD", "PLTR"]


def main() -> None:
    print(f"\nFetching {TICKERS}...\n")
    stocks = fetch_universe(TICKERS)
    for s in stocks:
        print(f"--- {s.ticker} ---")
        print(f"  closes: {len(s.closes)} points"
              + (f"  (first={s.closes[0]:.2f}, last={s.closes[-1]:.2f})" if s.closes else ""))
        print(f"  pe: {s.pe}")
        print(f"  market_cap: {s.market_cap}")
        print(f"  profit_margin: {s.profit_margin}")
        print(f"  error: {s.error}")
        print()


if __name__ == "__main__":
    main()
