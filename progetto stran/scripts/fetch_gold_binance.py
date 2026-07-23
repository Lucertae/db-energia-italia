#!/usr/bin/env python3
"""Fetch gold proxy (PAXG/USDT Binance) into cache/XAU.csv — FRED gold discontinued."""
import json
import os
import sys
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache")
URL = "https://api.binance.com/api/v3/klines"


def main():
    os.makedirs(CACHE, exist_ok=True)
    params = urllib.parse.urlencode({
        "symbol": "PAXGUSDT",
        "interval": "1d",
        "limit": 1000,
    })
    req = urllib.request.Request(f"{URL}?{params}", headers={"User-Agent": "ops-desk/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.load(resp)
    rows = []
    for k in data:
        ts_ms = int(k[0])
        close = float(k[4])
        if close <= 0:
            continue
        t = time.gmtime(ts_ms / 1000)
        ymd = f"{t.tm_year:04d}-{t.tm_mon:02d}-{t.tm_mday:02d}"
        rows.append((ymd, close))
    if len(rows) < 100:
        print(f"FAIL XAU: only {len(rows)} rows", file=sys.stderr)
        return 1
    out = os.path.join(CACHE, "XAU.csv")
    with open(out, "w", encoding="utf-8", newline="") as f:
        f.write("DATE,VALUE\n")
        for ymd, val in rows:
            f.write(f"{ymd},{val}\n")
    print(f"OK XAU {len(rows)} days (PAXG proxy) -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
