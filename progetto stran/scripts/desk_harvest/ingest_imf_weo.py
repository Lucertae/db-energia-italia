#!/usr/bin/env python3
"""Ingest IMF World Economic Outlook (WEO) SDMX-style CSV into desk cache.

Source (official): https://data.imf.org/en/datasets/IMF.RES:WEO
Accepts a local dump (e.g. from Downloads) or reuses cache/imf/weo_raw.csv.
Writes:
  cache/imf/weo_raw.csv       — full dump (copied)
  cache/imf/weo_key.csv       — long format, key indicators only
  cache/imf/weo_summary.json  — coverage / status for ING page
"""
from __future__ import annotations

import csv
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("DESK_ROOT", HERE.parents[1]))
CACHE = Path(os.environ.get("DESK_CACHE", ROOT / "cache"))
OUT_DIR = CACHE / "imf"
RAW_NAME = "weo_raw.csv"
KEY_NAME = "weo_key.csv"
SUM_NAME = "weo_summary.json"

# Priority indicators always kept even if KEY_INDICATOR is false.
KEEP_CODES = {
    "NGDPD", "NGDPDPC", "NGDP_RPCH", "NGDP_R", "NGDP",
    "PCPI", "PCPIE", "PCPIPCH",
    "LUR", "LP", "LE",
    "BCA", "GGXWDG", "GGXCNL", "GGX", "GGR",
    "PPPGDP", "PPPPC", "PPPSH",
    "TX_RPCH", "TM_RPCH",
}

YEAR_MIN, YEAR_MAX = 1980, 2035


def find_source(arg: str | None) -> Path | None:
    if arg:
        p = Path(arg)
        if p.is_file():
            return p
    cached = OUT_DIR / RAW_NAME
    if cached.is_file():
        return cached
    downloads = Path.home() / "Downloads"
    if downloads.is_dir():
        cands = sorted(
            downloads.glob("*IMF*WEO*.csv"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        if cands:
            return cands[0]
        cands = sorted(
            downloads.glob("*IMF.RES_WEO*.csv"),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        if cands:
            return cands[0]
    return None


def year_cols(fieldnames: list[str]) -> list[str]:
    out: list[str] = []
    for name in fieldnames:
        if name.isdigit():
            y = int(name)
            if YEAR_MIN <= y <= YEAR_MAX:
                out.append(name)
    return out


def parse_val(raw: str) -> float | None:
    s = (raw or "").strip()
    if not s or s.lower() in {"null", "n/a", "na", "--"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def ingest(src: Path) -> dict:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    raw_out = OUT_DIR / RAW_NAME
    if src.resolve() != raw_out.resolve():
        print(f"Copy {src} -> {raw_out} ({src.stat().st_size / 1e6:.1f} MB)")
        shutil.copy2(src, raw_out)
    else:
        print(f"Use existing {raw_out}")

    key_path = OUT_DIR / KEY_NAME
    countries: set[str] = set()
    indicators: set[str] = set()
    n_in = 0
    n_out = 0
    years_seen: set[int] = set()

    with raw_out.open(encoding="utf-8", newline="") as fin, key_path.open(
        "w", encoding="utf-8", newline=""
    ) as fout:
        reader = csv.DictReader(fin)
        if not reader.fieldnames:
            raise SystemExit("empty CSV")
        years = year_cols(list(reader.fieldnames))
        writer = csv.DictWriter(
            fout,
            fieldnames=[
                "country_id",
                "country",
                "indicator_id",
                "indicator",
                "unit",
                "scale",
                "year",
                "value",
                "key_indicator",
            ],
        )
        writer.writeheader()
        for row in reader:
            n_in += 1
            ind_id = (row.get("INDICATOR.ID") or "").strip()
            is_key = (row.get("KEY_INDICATOR") or "").lower() == "true"
            if not ind_id:
                continue
            if not is_key and ind_id not in KEEP_CODES:
                continue
            cid = (row.get("COUNTRY.ID") or "").strip()
            if not cid or len(cid) != 3:
                continue
            countries.add(cid)
            indicators.add(ind_id)
            unit = (row.get("UNIT") or "").strip()
            scale = (row.get("SCALE") or "").strip()
            cname = (row.get("COUNTRY") or "").strip()
            iname = (row.get("INDICATOR") or "").strip()
            for y in years:
                val = parse_val(row.get(y, ""))
                if val is None:
                    continue
                years_seen.add(int(y))
                writer.writerow(
                    {
                        "country_id": cid,
                        "country": cname,
                        "indicator_id": ind_id,
                        "indicator": iname[:120],
                        "unit": unit,
                        "scale": scale,
                        "year": y,
                        "value": f"{val:.6g}",
                        "key_indicator": "true" if is_key else "false",
                    }
                )
                n_out += 1

    summary = {
        "version": 1,
        "source": "IMF.RES:WEO",
        "dataset": "IMF World Economic Outlook",
        "url": "https://data.imf.org/en/datasets/IMF.RES:WEO",
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "raw_path": str(raw_out.as_posix()),
        "key_path": str(key_path.as_posix()),
        "raw_bytes": raw_out.stat().st_size,
        "rows_in": n_in,
        "rows_out": n_out,
        "countries": len(countries),
        "indicators": len(indicators),
        "year_min": min(years_seen) if years_seen else None,
        "year_max": max(years_seen) if years_seen else None,
        "status": "ok",
        "refresh_sec": 86400 * 30,
        "publisher": "IMF",
        "note": "WEO April/October releases — key indicators long CSV for desk SER/PIPE",
    }
    (OUT_DIR / SUM_NAME).write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"OK IMF WEO  countries={summary['countries']} indicators={summary['indicators']} "
        f"long_rows={n_out} years={summary['year_min']}-{summary['year_max']}"
    )
    return summary


def main() -> int:
    src = find_source(sys.argv[1] if len(sys.argv) > 1 else None)
    if not src:
        print(
            "ERRORE: CSV IMF WEO non trovato. Passa il path oppure mettilo in Downloads "
            "(*IMF*WEO*.csv) o in cache/imf/weo_raw.csv"
        )
        return 1
    ingest(src)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
