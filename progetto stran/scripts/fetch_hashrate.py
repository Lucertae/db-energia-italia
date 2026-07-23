#!/usr/bin/env python3
"""Fetch Bitcoin network hash rate (EH/s) into FRED-format cache/HAS.csv."""
import json
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache")
URL = (
    "https://api.blockchain.info/charts/hash-rate"
    "?timespan=5years&format=json&sampled=true"
)


def main():
    os.makedirs(CACHE, exist_ok=True)
    req = urllib.request.Request(URL, headers={"User-Agent": "ops-desk/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.load(resp)
    values = data.get("values", [])
    rows = []
    for pt in values:
        ts = pt.get("x")
        val = pt.get("y")
        if ts is None or val is None:
            continue
        t = time.gmtime(int(ts))
        ymd = f"{t.tm_year:04d}-{t.tm_mon:02d}-{t.tm_mday:02d}"
        rows.append((ymd, float(val)))
    if len(rows) < 30:
        print(f"FAIL HAS: only {len(rows)} rows", file=sys.stderr)
        return 1
    out = os.path.join(CACHE, "HAS.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write("DATE,VALUE\n")
        for ymd, val in rows:
            f.write(f"{ymd},{val}\n")
    print(f"OK HAS {len(rows)} days -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
