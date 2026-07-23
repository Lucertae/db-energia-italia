#!/usr/bin/env python3
"""
US weekly inventories from EIA public pages (no API key).

FRED series WCESTUS1/NGSTUS return 404. EIA API needs registration.
LeafHandler HTML tables are public and carry the same weekly data.
"""
from __future__ import annotations

import os
import re
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
CACHE = Path(os.environ.get("DESK_CACHE", ROOT / "cache"))
EIA_DIR = CACHE / "eia"
FRED_DIR = CACHE / "fred"

SERIES = {
    "CRU": "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?f=W&n=PET&s=WCESTUS1",
    "NGS": "https://www.eia.gov/dnav/ng/hist/nw2_epg0_swo_r48_bcfw.htm",
}


def fetch_html(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "ops-desk-harvest/1.0"})
    last_err = ""
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except Exception as e:
            last_err = str(e)
            time.sleep(1.5 * (attempt + 1))
    raise RuntimeError(last_err)


def _clean_cell(text: str) -> str:
    return text.replace("&nbsp;", " ").strip()


def parse_leaf_html(html: str) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    tr_blocks = re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.I | re.S)
    date_re = re.compile(r"^\d{2}/\d{2}$")
    val_re = re.compile(r"^[\d,]+(?:\.\d+)?$")

    for tr in tr_blocks:
        ym = re.search(r"(\d{4})-([A-Za-z]{3})", tr)
        if not ym:
            continue
        year = int(ym.group(1))
        cells = [_clean_cell(m) for m in re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.I | re.S)]
        i = 0
        while i + 1 < len(cells):
            dcell, vcell = cells[i], cells[i + 1]
            if date_re.match(dcell) and val_re.match(vcell.replace(" ", "")):
                mm, dd = dcell.split("/")
                try:
                    dt = datetime(year, int(mm), int(dd))
                except ValueError:
                    i += 1
                    continue
                val = float(vcell.replace(",", "").replace(" ", ""))
                rows.append((dt.strftime("%Y-%m-%d"), val))
                i += 2
            else:
                i += 1

    rows.sort(key=lambda x: x[0])
    seen: set[str] = set()
    out: list[tuple[str, float]] = []
    for d, v in rows:
        if d in seen:
            continue
        seen.add(d)
        out.append((d, v))
    return out


def write_csv(path: Path, rows: list[tuple[str, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write("DATE,VALUE\n")
        for ymd, val in rows:
            f.write(f"{ymd},{val}\n")


def harvest_one(desk_id: str, url: str) -> bool:
    try:
        html = fetch_html(url)
        rows = parse_leaf_html(html)
    except Exception as e:
        print(f"FAIL {desk_id}: {e}", file=sys.stderr)
        return False
    if len(rows) < 52:
        print(f"FAIL {desk_id}: only {len(rows)} rows parsed", file=sys.stderr)
        return False
    for p in (CACHE / f"{desk_id}.csv", EIA_DIR / f"{desk_id}.csv", FRED_DIR / f"{desk_id}.csv"):
        write_csv(p, rows)
    print(f"OK {desk_id} via EIA public ({len(rows)} weeks, latest {rows[-1][0]} = {rows[-1][1]})")
    return True


def main() -> int:
    ok = 0
    for desk_id, url in SERIES.items():
        if harvest_one(desk_id, url):
            ok += 1
        time.sleep(0.8)
    return 0 if ok == len(SERIES) else 1


if __name__ == "__main__":
    raise SystemExit(main())
