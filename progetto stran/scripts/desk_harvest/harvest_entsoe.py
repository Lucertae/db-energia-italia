#!/usr/bin/env python3
"""ENTSO-E day-ahead A44 -> cache PDE/PFR/PIT... (FRED CSV daily mean)."""
from __future__ import annotations

import os
import sys
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("DESK_ROOT", HERE.parents[1]))
CACHE = Path(os.environ.get("DESK_CACHE", ROOT / "cache"))

ZONES = {
    "PDE": "10Y1001A1001A82H",
    "PFR": "10YFR-RTE------C",
    "PIT": "10Y1001A1001A73I",
    "PNL": "10YNL----------L",
    "PPL": "10YPL-AREA-----S",
}


def load_key() -> str:
    for env in ("ENTSOE_API_TOKEN", "HEDGE_ENTSOE_TOKEN"):
        v = os.environ.get(env, "").strip()
        if v:
            return v
    p = CACHE / "entsoe.key"
    if p.is_file():
        return p.read_text(encoding="utf-8").strip()
    return ""


def period_fmt(dt: datetime) -> str:
    return dt.strftime("%Y%m%d%H%M")


def fetch_xml(token: str, eic: str, start: datetime, end: datetime) -> bytes:
    q = urllib.parse.urlencode(
        {
            "securityToken": token,
            "documentType": "A44",
            "in_Domain": eic,
            "out_Domain": eic,
            "periodStart": period_fmt(start),
            "periodEnd": period_fmt(end),
        }
    )
    url = f"https://web-api.tp.entsoe.eu/api?{q}"
    req = urllib.request.Request(url, headers={"User-Agent": "ops-desk-harvest/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def daily_means(xml_bytes: bytes) -> dict[str, float]:
    root = ET.fromstring(xml_bytes)
    ns = {"ns": root.tag.split("}")[0].strip("{")} if "}" in root.tag else {}
    tag = lambda n: f"ns:{n}" if ns else n
    out: dict[str, list[float]] = defaultdict(list)
    for ts in root.findall(f".//{tag('TimeSeries')}", ns):
        for period in ts.findall(f".//{tag('Period')}", ns):
            start_el = period.find(f".//{tag('start')}", ns)
            if start_el is None or not start_el.text:
                continue
            base = datetime.fromisoformat(start_el.text.replace("Z", "+00:00"))
            for pt in period.findall(f".//{tag('Point')}", ns):
                pos_el = pt.find(tag("position"), ns)
                px_el = pt.find(tag("price.amount"), ns)
                if pos_el is None or px_el is None or not px_el.text:
                    continue
                try:
                    pos = int(pos_el.text)
                    px = float(px_el.text)
                except (TypeError, ValueError):
                    continue
                dt = base + timedelta(hours=pos - 1)
                day = dt.astimezone(timezone.utc).strftime("%Y-%m-%d")
                out[day].append(px)
    return {d: sum(v) / len(v) for d, v in out.items() if v}


def merge_csv(desk_id: str, daily: dict[str, float]) -> int:
    path = CACHE / f"{desk_id}.csv"
    rows: dict[str, float] = {}
    if path.is_file():
        with path.open(encoding="utf-8") as f:
            lines = f.read().splitlines()
        for line in lines[1:]:
            if "," not in line:
                continue
            d, v = line.split(",", 1)
            try:
                rows[d.strip()] = float(v)
            except ValueError:
                continue
    rows.update(daily)
    days = sorted(rows.keys())[-1900:]
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write(f"DATE,{desk_id}\n")
        for d in days:
            f.write(f"{d},{rows[d]:.4f}\n")
    return len(days)


def main() -> int:
    token = load_key()
    if not token:
        print("SKIP entsoe: no token", file=sys.stderr)
        return 2
    CACHE.mkdir(parents=True, exist_ok=True)
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=5)
    ok = 0
    for desk_id, eic in ZONES.items():
        try:
            xml = fetch_xml(token, eic, start, end)
            daily = daily_means(xml)
            if not daily:
                print(f"FAIL {desk_id}: no prices")
                continue
            n = merge_csv(desk_id, daily)
            print(f"OK {desk_id} {len(daily)} new days merged ({n} total)")
            ok += 1
        except Exception as exc:
            print(f"FAIL {desk_id}: {exc}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
