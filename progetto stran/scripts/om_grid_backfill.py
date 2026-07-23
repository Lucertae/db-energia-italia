#!/usr/bin/env python3
"""Backfill Open-Meteo multi-grid hourly wind until cache complete."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bridge.adapters.open_meteo.hourly_harvest import run as om_run
from bridge.energy.entsoe_util import load_power_wind_config
from datetime import date, timedelta


def _missing_count(base: Path) -> int:
    pcfg = load_power_wind_config(base)
    end = date.today()
    missing = 0
    for desk_id, desk in pcfg.get("desks", {}).items():
        for pt in desk.get("grid_points", []):
            pid = str(pt["id"])
            d = base / "cache" / "weather" / "open_meteo_hourly" / desk_id / pid
            existing = {p.stem for p in d.glob("*.json")} if d.is_dir() else set()
            cursor = date(2021, 1, 1)
            while cursor < end:
                mk = cursor.strftime("%Y-%m")
                if mk not in existing:
                    missing += 1
                cursor = (cursor.replace(day=1) + timedelta(days=32)).replace(day=1)
    return missing


def main() -> int:
    base = ROOT
    max_rounds = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    for i in range(max_rounds):
        before = _missing_count(base)
        if before == 0:
            print(f"complete after {i} rounds")
            return 0
        r = om_run(base)
        after = _missing_count(base)
        print(f"round {i+1}: {r.get('message')} missing_months~{after} (was {before})")
        if after >= before:
            print("no progress — stopping")
            break
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
