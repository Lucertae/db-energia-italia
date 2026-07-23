#!/usr/bin/env python3
"""EIA weekly petroleum/gas storage when cache/eia.key is present."""
from __future__ import annotations

import json
import os
import sys
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
CACHE = Path(os.environ.get("DESK_CACHE", ROOT / "cache"))
EIA_DIR = CACHE / "eia"

SERIES = {
    "CRU": ("petroleum/stoc/wstk/data", "WCESTUS1"),
    "NGS": ("natural-gas/stor/wkly/data", "NW2_EPG0_SWO_R48_BCF"),
}


def load_key() -> str:
    env = os.environ.get("EIA_API_KEY", "").strip()
    if env:
        return env
    key_path = CACHE / "eia.key"
    if key_path.is_file():
        return key_path.read_text(encoding="utf-8").strip()
    return ""


def fetch_series(key: str, route: str, series_id: str) -> list[tuple[str, float]]:
    params = {
        "api_key": key,
        "frequency": "weekly",
        "data[0]": "value",
        "facets[series][]": series_id,
        "sort[0][column]": "period",
        "sort[0][direction]": "asc",
        "length": "520",
    }
    url = f"https://api.eia.gov/v2/{route}/?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "ops-desk-harvest/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.load(resp)
    items = data.get("response", {}).get("data", [])
    rows: list[tuple[str, float]] = []
    for it in items:
        if it.get("value") is None:
            continue
        period = it["period"]
        ymd = period[:10] if len(period) >= 10 else period + "-01"
        rows.append((ymd, float(it["value"])))
    return rows


def write_csv(path: Path, rows: list[tuple[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write("DATE,VALUE\n")
        for ymd, val in rows:
            f.write(f"{ymd},{val}\n")


def main() -> int:
    key = load_key()
    if not key:
        print("WARN eia: no key — using EIA public LeafHandler", file=sys.stderr)
        from eia_public_inventories import main as eia_main
        return eia_main()
    ok = 0
    for desk_id, (route, series_id) in SERIES.items():
        try:
            rows = fetch_series(key, route, series_id)
            if len(rows) < 10:
                print(f"FAIL {desk_id}: {len(rows)} rows", file=sys.stderr)
                continue
            write_csv(CACHE / f"{desk_id}.csv", rows)
            write_csv(EIA_DIR / f"{desk_id}.csv", rows)
            print(f"OK {desk_id} {len(rows)} weeks")
            ok += 1
        except Exception as e:
            print(f"FAIL {desk_id}: {e}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
