"""
Load the current S&P 500 constituents from Wikipedia.

We cache the list for a week — it changes only on index reconstitutions, which
are infrequent. If Wikipedia is unreachable we fall back to the last cached
copy, even if stale.
"""

from __future__ import annotations

import io
import logging

import httpx
import pandas as pd

from . import cache

log = logging.getLogger(__name__)

WIKI_URL = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
CACHE_NAME = "sp500_list"
_USER_AGENT = "Mozilla/5.0 (screener-bot; +local research tool)"


def load_sp500() -> list[str]:
    cached = cache.load(CACHE_NAME) or {}
    if cached.get("week") == cache.this_week_key() and cached.get("tickers"):
        return cached["tickers"]

    # httpx uses certifi's bundled CA store, which sidesteps the common
    # macOS-Python "certificate verify failed" issue.
    try:
        r = httpx.get(WIKI_URL, headers={"User-Agent": _USER_AGENT}, timeout=20.0, follow_redirects=True)
        r.raise_for_status()
        tables = pd.read_html(io.StringIO(r.text))
        df = tables[0]
        # Wikipedia uses 'BRK.B' style; FMP uses 'BRK-B'.
        tickers = [str(t).replace(".", "-") for t in df["Symbol"].tolist()]
        cache.save(CACHE_NAME, {"week": cache.this_week_key(), "tickers": tickers})
        log.info("Loaded %d S&P 500 tickers from Wikipedia", len(tickers))
        return tickers
    except Exception as e:
        log.warning("Failed to fetch S&P 500 list (%s); using stale cache if available", e)
        return cached.get("tickers", [])
