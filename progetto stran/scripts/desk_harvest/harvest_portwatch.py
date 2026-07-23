#!/usr/bin/env python3
"""IMF PortWatch chokepoint transits → cache/portwatch/chokepoints.csv (no API key)."""
from __future__ import annotations

import csv
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(os.environ.get("DESK_CACHE", ROOT / "cache")) / "portwatch"
OUT_CSV = OUT_DIR / "chokepoints.csv"

BASE = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services"
LAYER = f"{BASE}/Daily_Chokepoints_Data/FeatureServer/0/query"

# Desk priority corridors (IMF portid)
WATCH = [
    ("chokepoint6", "HORMUZ"),
    ("chokepoint5", "MALACCA"),
    ("chokepoint7", "CAPE"),
    ("chokepoint4", "BAB"),
    ("chokepoint19", "SUNDA"),
    ("chokepoint15", "LOMBOK"),
    ("chokepoint1", "SUEZ"),
]


def fetch_days(portid: str, days: int = 45) -> list[dict]:
    where = f"portid='{portid}'"
    params = {
        "where": where,
        "outFields": "date,portid,portname,n_total,n_tanker,n_cargo",
        "orderByFields": "date DESC",
        "resultRecordCount": str(days),
        "f": "json",
    }
    url = f"{LAYER}?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers={"User-Agent": "ops-desk-harvest/1.0"})
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.load(resp)
    return [f["attributes"] for f in data.get("features", [])]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    rows: list[dict] = []
    for portid, desk_id in WATCH:
        try:
            for a in fetch_days(portid):
                rows.append({
                    "date": a.get("date", ""),
                    "desk_id": desk_id,
                    "portid": a.get("portid", portid),
                    "name": a.get("portname", ""),
                    "n_total": a.get("n_total", 0),
                    "n_tanker": a.get("n_tanker", 0),
                    "n_cargo": a.get("n_cargo", 0),
                })
        except Exception as e:
            print(f"FAIL {desk_id}: {e}", flush=True)

    if not rows:
        return 1

    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=["date", "desk_id", "portid", "name", "n_total", "n_tanker", "n_cargo"],
        )
        w.writeheader()
        w.writerows(rows)

    print(f"OK portwatch {len(rows)} rows -> {OUT_CSV}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
