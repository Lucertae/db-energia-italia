#!/usr/bin/env python3
"""Scarica flussi elettrici bilaterali Eurostat (NRG_TI_EH / NRG_TE_EH)."""
from __future__ import annotations

import csv
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "cache" / "eurostat"
OUT_CSV = CACHE / "electricity_trade_bilateral.csv"

DATASETS = {
    "import": "NRG_TI_EH",
    "export": "NRG_TE_EH",
}


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": "STRAN-OPS-DESK/1.0"})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())


def unravel(pos: int, sizes: list[int]) -> list[int]:
    coords: list[int] = []
    rem = pos
    for size in reversed(sizes):
        coords.append(rem % size)
        rem //= size
    return list(reversed(coords))


def parse_dataset(data: dict, direction: str) -> list[dict]:
    dims = data["dimension"]
    dim_ids = data["id"]
    sizes = data["size"]
    labels = {
        dim: dims[dim]["category"]["label"]
        for dim in dim_ids
    }
    indices = {
        dim: list(dims[dim]["category"]["index"].keys())
        for dim in dim_ids
    }

    rows: list[dict] = []
    for pos, value in data.get("value", {}).items():
        if not value or float(value) <= 0:
            continue
        coords = unravel(int(pos), sizes)
        rec = {dim_ids[i]: indices[dim_ids[i]][coords[i]] for i in range(len(dim_ids))}
        if rec.get("siec") != "E7000":
            continue
        if rec.get("unit") != "GWH":
            continue
        if rec.get("freq") != "A":
            continue
        rows.append({
            "direction": direction,
            "reporter": rec["geo"],
            "reporter_name": labels["geo"].get(rec["geo"], rec["geo"]),
            "partner": rec["partner"],
            "partner_name": labels["partner"].get(rec["partner"], rec["partner"]),
            "year": int(rec["time"]),
            "gwh": float(value),
            "twh": float(value) / 1000.0,
        })
    return rows


def harvest_years(years: list[int] | None = None) -> list[dict]:
    if years is None:
        years = list(range(2015, 2025))
    all_rows: list[dict] = []
    for year in years:
        for direction, code in DATASETS.items():
            url = (
                "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
                f"{code}?lang=EN&format=JSON&time={year}&unit=GWH&siec=E7000&freq=A"
            )
            print(f"GET {code} {year}...")
            data = fetch_json(url)
            parsed = parse_dataset(data, direction)
            print(f"  {len(parsed)} righe > 0")
            all_rows.extend(parsed)
    return all_rows


def write_csv(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "direction", "reporter", "reporter_name", "partner", "partner_name",
        "year", "gwh", "twh",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["reporter"], r["year"], r["direction"], -r["twh"])))


def main() -> int:
    rows = harvest_years()
    write_csv(rows, OUT_CSV)
    reporters = len({r["reporter"] for r in rows})
    print(f"OK {OUT_CSV} ({len(rows)} flussi, {reporters} paesi reporter)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
