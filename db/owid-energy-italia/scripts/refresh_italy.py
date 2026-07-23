#!/usr/bin/env python3
"""Legacy wrapper — usa db/owid-italia/scripts/harvest_all.py."""
from __future__ import annotations

import runpy
from pathlib import Path

TARGET = Path(__file__).resolve().parents[2] / "owid-italia" / "scripts" / "harvest_all.py"
runpy.run_path(str(TARGET), run_name="__main__")
