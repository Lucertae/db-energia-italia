#!/usr/bin/env python3
"""Fetch EIA weekly petroleum/gas storage into FRED-format cache CSV for CRU and NGS."""
import json
import os
import sys
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache")

SERIES = {
    "CRU": ("petroleum/stoc/wstk/data", "WCESTUS1", "US crude stocks ex-SPR (kbbl)"),
    "NGS": ("natural-gas/stor/wkly/data", "NW2_EPG0_SWO_R48_BCF", "US gas working storage (BCF)"),
}


def load_key():
    env = os.environ.get("EIA_API_KEY", "").strip()
    if env:
        return env
    path = os.path.join(CACHE, "eia.key")
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    return ""


def ymd_from_period(period: str) -> str:
    # weekly: 2024-01-05, monthly: 2024-01
    if len(period) >= 10:
        return period[:10]
    return period + "-01"


def fetch_series(key: str, route: str, series_id: str, length: int = 520):
    params = {
        "api_key": key,
        "frequency": "weekly",
        "data[0]": "value",
        "facets[series][]": series_id,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": str(length),
    }
    url = f"https://api.eia.gov/v2/{route}/?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "ops-desk/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return json.load(resp)


def write_fred_csv(path: str, rows):
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write("DATE,VALUE\n")
        for period, val in rows:
            f.write(f"{ymd_from_period(period)},{val}\n")


def main():
    key = load_key()
    if not key:
        print("WARN: no EIA key — using EIA public LeafHandler", file=sys.stderr)
        here = os.path.dirname(os.path.abspath(__file__))
        harvest = os.path.join(here, "desk_harvest", "eia_public_inventories.py")
        if os.path.isfile(harvest):
            import subprocess
            return subprocess.call([sys.executable, harvest])
        print("FAIL: fred_inventories.py missing", file=sys.stderr)
        return 1

    os.makedirs(CACHE, exist_ok=True)
    ok = 0
    for desk_id, (route, series_id, _label) in SERIES.items():
        try:
            data = fetch_series(key, route, series_id)
            items = data.get("response", {}).get("data", [])
            rows = [(it["period"], it["value"]) for it in items if it.get("value") is not None]
            if len(rows) < 10:
                print(f"FAIL {desk_id}: only {len(rows)} rows")
                continue
            out = os.path.join(CACHE, f"{desk_id}.csv")
            write_fred_csv(out, rows)
            print(f"OK {desk_id} {len(rows)} weeks -> {out}")
            ok += 1
        except Exception as e:
            print(f"FAIL {desk_id}: {e}")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
