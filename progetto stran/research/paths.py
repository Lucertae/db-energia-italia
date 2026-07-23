"""Path helpers for OPS DESK research layer."""
from __future__ import annotations

import os
from pathlib import Path

RESEARCH_DIR = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("DESK_ROOT", RESEARCH_DIR.parent))
CACHE = Path(os.environ.get("DESK_CACHE", ROOT / "cache"))
CATALOG = RESEARCH_DIR / "series_catalog.json"
OUTPUT = RESEARCH_DIR / "output"


def ensure_output() -> Path:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    return OUTPUT
