#!/usr/bin/env python3
"""Download FRED CSV into desk cache (flat + cache/fred/)."""
from __future__ import annotations

import os
import subprocess
import sys
import time
import urllib.parse
from datetime import date, timedelta
from pathlib import Path

from series_config import DESK_FRED, PRODUCTION_FRED

UA = "ops-desk-harvest/1.0"
HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("DESK_ROOT", HERE.parents[1]))
CACHE = Path(os.environ.get("DESK_CACHE", ROOT / "cache"))
FRED_DIR = CACHE / "fred"
CURL = os.environ.get("CURL_BIN", "curl")


def cosd(days: int) -> str:
    return (date.today() - timedelta(days=days)).isoformat()


def fetch_fred_csv(fred_id: str, days: int) -> str:
    params = urllib.parse.urlencode({"id": fred_id, "cosd": cosd(days)})
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?{params}"
    last_err = ""
    flags_list = ([], ["--http1.1"])
    for attempt in range(3):
        flags = flags_list[min(attempt, len(flags_list) - 1)]
        proc = subprocess.run(
            [CURL, "-fsSL", "--max-time", "90", *flags, url],
            capture_output=True,
            text=True,
            timeout=120,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            return proc.stdout
        last_err = proc.stderr.strip() or f"curl exit {proc.returncode}"
        time.sleep(1.0 * (attempt + 1))
    raise RuntimeError(last_err)


def row_count(body: str) -> int:
    return max(0, sum(1 for line in body.splitlines() if line and not line.startswith("DATE")))


def write_csv(path: Path, body: str) -> bool:
    if row_count(body) < 5:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body if body.endswith("\n") else body + "\n", encoding="utf-8")
    return True


def harvest_one(name: str, fred_id: str, days: int, out_flat: Path | None, out_fred: Path) -> bool:
    try:
        body = fetch_fred_csv(fred_id, days)
    except Exception as e:
        print(f"FAIL {name}/{fred_id}: {e}", file=sys.stderr)
        return False
    ok = write_csv(out_fred, body)
    if out_flat:
        ok = write_csv(out_flat, body) and ok
    if ok:
        print(f"OK {name} {row_count(body)} rows")
    else:
        print(f"FAIL {name}/{fred_id}: too few rows", file=sys.stderr)
    return ok


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    FRED_DIR.mkdir(parents=True, exist_ok=True)
    ok = fail = 0

    for s in DESK_FRED:
        if harvest_one(s.desk_id, s.fred_id, s.days, CACHE / f"{s.desk_id}.csv", FRED_DIR / f"{s.desk_id}.csv"):
            ok += 1
        else:
            fail += 1
        time.sleep(0.5)

    for fred_id, days in PRODUCTION_FRED:
        if harvest_one(fred_id, fred_id, days, CACHE / f"{fred_id}.csv", FRED_DIR / f"{fred_id}.csv"):
            ok += 1
        else:
            fail += 1
        time.sleep(0.5)

    print(f"fred harvest ok={ok} fail={fail}")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
