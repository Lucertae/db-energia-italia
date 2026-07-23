#!/usr/bin/env python3
"""Import EU day-ahead power prices from math/data unified CSV into terminal cache (FRED format)."""
import csv
import os
import sys
from collections import defaultdict
from datetime import datetime

ZONE_MAP = {
    "DE-LU": "PDE",
    "FR": "PFR",
    "IT-NORTH": "PIT",
    "NL": "PNL",
    "PL": "PPL",
    "NO2": "PNO",
    "AT": "PAT",
}

def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    src = os.environ.get(
        "PRICES_UNIFIED",
        r"C:\Users\jecho\Desktop\math\data\unified\prices_unified.csv",
    )
    cache = os.path.join(root, "cache")
    os.makedirs(cache, exist_ok=True)

    if not os.path.isfile(src):
        print(f"MISSING {src}", file=sys.stderr)
        return 1

    buckets = defaultdict(list)
    with open(src, newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            zone = row.get("zone", "")
            sid = ZONE_MAP.get(zone)
            if not sid:
                continue
            ts = row.get("timestamp_utc", "")
            price = row.get("price_eur_mwh", "")
            if not ts or not price:
                continue
            try:
                dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                day = dt.strftime("%Y-%m-%d")
                buckets[sid].append((day, float(price)))
            except (ValueError, TypeError):
                continue

    for sid, rows in buckets.items():
        daily = defaultdict(list)
        for day, px in rows:
            daily[day].append(px)
        days = sorted(daily.keys())
        out = os.path.join(cache, f"{sid}.csv")
        with open(out, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["DATE", sid])
            for d in days[-1900:]:
                avg = sum(daily[d]) / len(daily[d])
                w.writerow([d, f"{avg:.4f}"])
        print(f"OK {sid} {len(days)} days -> {out}")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
