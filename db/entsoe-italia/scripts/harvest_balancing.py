#!/usr/bin/env python3
"""Harvest ENTSO-E balancing series for Italy only (resume-safe)."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from harvest_all_italia import (
    DATA,
    LOGS,
    harvest_balancing,
    load_key,
    log_event,
)
from entsoe import EntsoePandasClient


def purge_empty_markers():
    base = DATA / "IT" / "balancing"
    if not base.exists():
        return 0
    removed = 0
    for p in base.rglob("*.csv"):
        if p.stat().st_size == 0:
            p.unlink()
            removed += 1
    return removed


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    key = load_key()
    if not key:
        raise SystemExit("Missing entsoe.key")

    removed = purge_empty_markers()
    print(f"Removed {removed} empty balancing marker(s)")

    client = EntsoePandasClient(api_key=key)
    log_path = LOGS / f"harvest_balancing_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jsonl"
    print(f"ENTSO-E balancing harvest IT -> {DATA / 'IT' / 'balancing'}")
    print(f"log: {log_path}")

    with log_path.open("a", encoding="utf-8") as logfp:
        harvest_balancing(client, logfp, retry_empty=True, sleep_s=1.0)
        log_event(logfp, status="done", dataset="balancing", zone="IT", year=0)

    n = len(list((DATA / "IT" / "balancing").rglob("*.csv")))
    bytes_total = sum(p.stat().st_size for p in (DATA / "IT" / "balancing").rglob("*") if p.is_file())
    print(f"DONE balancing: {n} CSV files, {bytes_total / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
