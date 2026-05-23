"""Load config.json from the repo root."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_CONFIG_PATH = Path(__file__).resolve().parent.parent.parent / "config.json"


def load_config() -> dict[str, Any]:
    with _CONFIG_PATH.open() as f:
        return json.load(f)
