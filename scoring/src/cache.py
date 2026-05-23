"""
TTL-aware JSON file cache. Caller decides what to store and the TTL window;
this module just does load/save with freshness checks.

Two tiers in use today (set up in data_layer.py):
- prices:        keyed by ISO date     (TTL: 1 day)
- fundamentals:  keyed by ISO week     (TTL: 7 days)
"""

from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"


def _ensure_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def today_key() -> str:
    return date.today().isoformat()  # "2026-05-22"


def this_week_key() -> str:
    iso = date.today().isocalendar()
    return f"{iso.year}-W{iso.week:02d}"  # "2026-W21"


def load(name: str) -> dict[str, Any] | None:
    """Load `cache/{name}.json` or return None if missing/corrupt."""
    _ensure_dir()
    path = CACHE_DIR / f"{name}.json"
    if not path.exists():
        return None
    try:
        with path.open("r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        log.warning("cache load failed for %s: %s", name, e)
        return None


def save(name: str, payload: dict[str, Any]) -> None:
    _ensure_dir()
    path = CACHE_DIR / f"{name}.json"
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        json.dump(payload, f)
    tmp.replace(path)  # atomic on POSIX
