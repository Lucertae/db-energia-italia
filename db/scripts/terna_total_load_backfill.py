#!/usr/bin/env python3
"""Backfill Terna total-load for years before 2023 (hourly/quarter-hourly)."""
from __future__ import annotations

import importlib.util
import sys
import time
from calendar import monthrange
from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parents[1]
OUT = DB / "consumi-italia" / "sources" / "terna" / "total_load"


def log(msg: str) -> None:
    print(msg, flush=True)


def load_terna():
    path = DB / "consumi-italia" / "scripts" / "harvest_terna_api.py"
    spec = importlib.util.spec_from_file_location("harvest_terna_api", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    t = load_terna()
    cid, sec = t.load_creds()
    client = t.TernaClient(cid, sec)
    client.refresh()
    OUT.mkdir(parents=True, exist_ok=True)

    # API window: last 5 calendar years + current year (in 2026 => 2021..2026).
    # Already have 2023-2026; fill 2021-2022 only.
    for year in range(2021, 2023):
        dest = OUT / f"total_load_{year}.csv"
        if dest.exists() and dest.stat().st_size > 1_000_000:
            log(f"  skip {dest.name}")
            continue
        rows: list[dict] = []
        for month in range(1, 13):
            last = monthrange(year, month)[1]
            date_from = f"01/{month:02d}/{year}"
            date_to = f"{last:02d}/{month:02d}/{year}"
            url = (
                "https://api.terna.it/load/v2.0/total-load"
                f"?dateFrom={date_from}&dateTo={date_to}"
            )
            try:
                data = client.get(url)
                items = data.get("total_load") or []
                rows.extend(items)
                log(f"  total-load {year}-{month:02d}: {len(items)}")
            except Exception as e:
                log(f"  FAIL {year}-{month:02d}: {e}")
            time.sleep(t.SLEEP)
        if rows:
            pd.DataFrame(rows).to_csv(dest, index=False)
            log(f"  wrote {dest.name} rows={len(rows)}")
        else:
            log(f"  no rows for {year}")

    # Merge all years into one if present
    parts = sorted(OUT.glob("total_load_*.csv"))
    if parts:
        frames = [pd.read_csv(p) for p in parts]
        all_df = pd.concat(frames, ignore_index=True)
        merged = OUT / "total_load_all.csv"
        all_df.to_csv(merged, index=False)
        log(f"  merged {merged.name} rows={len(all_df)} from {len(parts)} files")
    log("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
