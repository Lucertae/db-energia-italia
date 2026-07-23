#!/usr/bin/env python3
"""Silent cool-down then one harvest attempt (no probe spam)."""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

HARVEST = Path(__file__).resolve().parent / "harvest_open_meteo.py"


def main() -> int:
    # Open-Meteo free-tier bans can last a long time after burst traffic.
    cool = int(sys.argv[1]) if len(sys.argv) > 1 else 1800
    print(f"cooling {cool}s with zero API calls...", flush=True)
    time.sleep(cool)
    print("starting harvest", flush=True)
    return subprocess.call([sys.executable, str(HARVEST)])


if __name__ == "__main__":
    raise SystemExit(main())
