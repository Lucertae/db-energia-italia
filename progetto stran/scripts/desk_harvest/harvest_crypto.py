#!/usr/bin/env python3
"""Binance daily klines -> cache/crypto/{ID}.csv and flat cache/{ID}.csv for XAU."""
from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from series_config import BINANCE_SYMBOLS

UA = "ops-desk-harvest/1.0"
HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("DESK_ROOT", HERE.parents[1]))
CACHE = Path(os.environ.get("DESK_CACHE", ROOT / "cache"))
CRYPTO_DIR = CACHE / "crypto"
API = "https://api.binance.com/api/v3/klines"
DAYS = int(os.environ.get("CRYPTO_DAYS", "1825"))


def fetch_klines(symbol: str, start_ms: int | None = None) -> list:
    rows: list = []
    cursor = start_ms
    end_ms = int(time.time() * 1000)
    while True:
        params: dict[str, str | int] = {
            "symbol": symbol,
            "interval": "1d",
            "limit": 1000,
        }
        if cursor:
            params["startTime"] = cursor
        url = f"{API}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=90) as resp:
            chunk = json.load(resp)
        if not chunk:
            break
        rows.extend(chunk)
        last_open = int(chunk[-1][0])
        if last_open >= end_ms - 86400000 or len(chunk) < 1000:
            break
        cursor = last_open + 1
        time.sleep(0.15)
    return rows


def klines_to_rows(data: list) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for k in data:
        ts_ms = int(k[0])
        close = float(k[4])
        if close <= 0:
            continue
        t = time.gmtime(ts_ms / 1000)
        ymd = f"{t.tm_year:04d}-{t.tm_mon:02d}-{t.tm_mday:02d}"
        out.append((ymd, close))
    out.sort(key=lambda x: x[0])
    return out


def write_csv(path: Path, rows: list[tuple[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["DATE", "VALUE"])
        for ymd, val in rows:
            w.writerow([ymd, f"{val:.8g}"])


def main() -> int:
    CRYPTO_DIR.mkdir(parents=True, exist_ok=True)
    start_ms = int((time.time() - DAYS * 86400) * 1000)
    ok = fail = 0
    for symbol, desk_id in BINANCE_SYMBOLS:
        try:
            data = fetch_klines(symbol, start_ms)
            rows = klines_to_rows(data)
            if len(rows) < 30:
                print(f"FAIL {desk_id}: only {len(rows)} rows", file=sys.stderr)
                fail += 1
                continue
            write_csv(CRYPTO_DIR / f"{desk_id}.csv", rows)
            if desk_id == "XAU":
                write_csv(CACHE / "XAU.csv", rows)
            print(f"OK {desk_id} {len(rows)} days ({symbol})")
            ok += 1
        except Exception as e:
            print(f"FAIL {desk_id}: {e}", file=sys.stderr)
            fail += 1
    print(f"crypto ok={ok} fail={fail}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
