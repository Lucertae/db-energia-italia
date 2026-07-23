#!/usr/bin/env python3
"""Wait until Open-Meteo archive answers, then run harvest."""
from __future__ import annotations

import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

PROBE = (
    "https://archive-api.open-meteo.com/v1/archive?"
    "latitude=41.9&longitude=12.5&start_date=2024-06-01&end_date=2024-06-01"
    "&hourly=rain,snowfall,precipitation&timezone=Europe/Rome"
)
HARVEST = Path(__file__).resolve().parent / "harvest_open_meteo.py"


def ok() -> bool:
    try:
        req = urllib.request.Request(PROBE, headers={"User-Agent": "meteo-italia/2.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            return resp.status == 200 and len(resp.read()) > 100
    except Exception as e:
        print(f"  probe fail: {e}", flush=True)
        return False


def main() -> int:
    for i in range(40):
        print(f"probe {i+1}/40", flush=True)
        if ok():
            print("API ready — starting harvest", flush=True)
            return subprocess.call([sys.executable, str(HARVEST)])
        time.sleep(120)
    print("API still rate-limited after ~80 min", flush=True)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
