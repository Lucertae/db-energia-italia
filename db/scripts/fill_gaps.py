#!/usr/bin/env python3
"""Fill remaining bulk gaps: Ember monthly, Eurostat prices, ISTAT, GME 2007, more Terna."""
from __future__ import annotations

import json
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parents[1]  # db/
UA = {"User-Agent": "Mozilla/5.0 (compatible; fill-gaps/1.0)"}


def log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"), flush=True)


def download(url: str, dest: Path, *, force: bool = False, timeout: int = 600) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 1000 and not force:
        log(f"  skip {dest} ({dest.stat().st_size/1e6:.2f} MB)")
        return dest
    log(f"  GET {url[:140]}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)
    log(f"  -> {dest.name} ({dest.stat().st_size/1e6:.2f} MB)")
    return dest


def harvest_ember_monthly() -> None:
    log("== Ember monthly electricity ==")
    out = DB / "mercati-italia" / "sources" / "ember"
    out.mkdir(parents=True, exist_ok=True)
    url = "https://files.ember-energy.org/public-downloads/monthly_full_release_long_format.csv"
    dest = out / "monthly_full_release_long_format.csv"
    download(url, dest)
    head = dest.read_bytes()[:40].lower()
    if b"<html" in head:
        raise RuntimeError("Ember monthly returned HTML")
    df = pd.read_csv(dest, low_memory=False)
    col = next(c for c in df.columns if c.lower() in ("country", "area", "entity"))
    it = df[df[col].astype(str).str.lower().eq("italy")].copy()
    it_path = out / "italy_monthly.csv"
    it.to_csv(it_path, index=False)
    log(f"  Italy monthly rows={len(it)}")


def harvest_eurostat_prices() -> None:
    log("== Eurostat electricity/gas prices IT ==")
    out = DB / "consumi-italia" / "sources" / "eurostat"
    out.mkdir(parents=True, exist_ok=True)
    # bulk then filter — same pattern as nrg_bal_c
    datasets = [
        "nrg_pc_204",  # household electricity prices
        "nrg_pc_205",  # industry electricity prices
        "nrg_pc_202",  # household gas
        "nrg_pc_203",  # industry gas
    ]
    for code in datasets:
        gz = DB / "consumi-italia" / "_tmp" / f"{code}.csv.gz"
        gz.parent.mkdir(parents=True, exist_ok=True)
        url = (
            "https://ec.europa.eu/eurostat/databrowser-backend/api/extraction/1.0/"
            f"LIVE/false/sdmx/csv/{code}?i&compressed=true"
        )
        try:
            download(url, gz)
        except Exception as e:
            log(f"  FAIL {code}: {e}")
            continue
        italy = out / f"{code}_italy.csv"
        import gzip
        import csv as _csv

        kept = 0
        with gzip.open(gz, "rt", encoding="utf-8", errors="replace", newline="") as fh, open(
            italy, "w", encoding="utf-8", newline=""
        ) as out_f:
            geo_idx = None
            for i, line in enumerate(fh):
                if i == 0:
                    cols = next(_csv.reader([line]))
                    lower = [c.strip().strip('"').lower() for c in cols]
                    geo_idx = lower.index("geo") if "geo" in lower else None
                    out_f.write(line if line.endswith("\n") else line + "\n")
                    continue
                if geo_idx is None:
                    break
                if ",IT," in line or ',"IT"' in line or line.rstrip().endswith(",IT"):
                    cells = next(_csv.reader([line]))
                    if cells[geo_idx].strip().strip('"') == "IT":
                        out_f.write(line if line.endswith("\n") else line + "\n")
                        kept += 1
        log(f"  {code} Italy rows={kept}")


def harvest_istat_pop() -> None:
    log("== ISTAT popolazione comuni (demo API) ==")
    out = DB / "consumi-italia" / "sources" / "istat"
    out.mkdir(parents=True, exist_ok=True)
    # Istat data browser SDMX for population by municipality — try common dataflow
    candidates = [
        # Population on 1st January by municipality (demo.istat.it / dati.istat.it)
        "https://sdmx.istat.it/SDMXWS/rest/data/22_289/?format=csv&detail=dataonly",
        "https://www.istat.it/storage/datainformativi/comuni/Elenco-comuni-italiani.xls",
        "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.xls",
        "https://raw.githubusercontent.com/openpolis/geojson-italy/master/geojson/limits_IT_municipalities.geojson",
    ]
    for url in candidates:
        name = url.rstrip("/").split("/")[-1].split("?")[0] or "istat_data.csv"
        if not Path(name).suffix:
            name += ".csv"
        dest = out / name
        try:
            download(url, dest)
        except Exception as e:
            log(f"  skip {name}: {e}")


def harvest_gme_2007() -> None:
    log("== GME Anno2007 retry ==")
    out = DB / "mercati-italia" / "sources" / "gme" / "mgp_storici"
    out.mkdir(parents=True, exist_ok=True)
    url = (
        "https://gme.mercatoelettrico.org/it-it/Home/Esiti/Elettricita/MGP/"
        "Statistiche/DatiStorici/moduleId/10874/controller/GmeDatiStoriciItem/"
        "action/DownloadFile?fileName=Anno2007.zip"
    )
    dest = out / "Anno2007.zip"
    for attempt in range(5):
        try:
            download(url, dest, force=True, timeout=900)
            d = out / "Anno2007"
            d.mkdir(exist_ok=True)
            with zipfile.ZipFile(dest) as zf:
                zf.extractall(d)
            log(f"  extracted {[p.name for p in d.glob('*')]}")
            return
        except Exception as e:
            log(f"  attempt {attempt+1} fail: {e}")
            time.sleep(8 + attempt * 5)
    log("  Anno2007 still unavailable")


def harvest_terna_more() -> None:
    log("== Terna extra APIs ==")
    import importlib.util

    path = DB / "consumi-italia" / "scripts" / "harvest_terna_api.py"
    spec = importlib.util.spec_from_file_location("harvest_terna_api", path)
    assert spec and spec.loader
    t = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t)

    cid, sec = t.load_creds()
    client = t.TernaClient(cid, sec)
    client.refresh()
    out = DB / "consumi-italia" / "sources" / "terna"

    # yearly simple endpoints
    yearly = [
        ("energy-balance", "energy_balance"),
        ("installed-capacity", "installed_capacity"),
        ("electrical-energy-in-italy", "electrical_energy_in_italy"),
        ("electrical-energy-by-type", "electrical_energy_by_type"),
        ("renewable-source-capacity", "renewable_source_capacity"),
    ]
    for path, key in yearly:
        rows: list[dict] = []
        for year in range(2015, 2026):
            url = f"https://api.terna.it/load/v2.0/{path}?year={year}"
            # some use generation API
            alts = [
                url,
                f"https://api.terna.it/generation/v2.0/{path}?year={year}",
            ]
            ok = False
            for u in alts:
                try:
                    data = client.get(u)
                    # find list payload
                    items = None
                    for k, v in data.items():
                        if isinstance(v, list):
                            items = v
                            key = k
                            break
                    if items is None:
                        items = data.get(key) or []
                    rows.extend(items)
                    log(f"  {path} {year}: {len(items)}")
                    ok = True
                    break
                except Exception as e:
                    last = e
            if not ok:
                log(f"  {path} {year} FAIL {last}")
            time.sleep(t.SLEEP)
        if rows:
            dest = out / path.replace("-", "_") / f"{path.replace('-', '_')}_all.csv"
            dest.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(rows).to_csv(dest, index=False)
            log(f"  wrote {dest} rows={len(rows)}")

    # total-load monthly chunks (heavy) — last 3 years only to fill price/load gap with Terna
    load_rows: list[dict] = []
    for year in range(2023, 2027):
        for month in range(1, 13):
            if year == 2026 and month > 7:
                break
            # last day approx
            from calendar import monthrange

            last = monthrange(year, month)[1]
            date_from = f"01/{month:02d}/{year}"
            date_to = f"{last:02d}/{month:02d}/{year}"
            url = (
                "https://api.terna.it/load/v2.0/total-load"
                f"?dateFrom={date_from}&dateTo={date_to}"
            )
            try:
                data = client.get(url)
                items = data.get("total_load") or []
                load_rows.extend(items)
                log(f"  total-load {year}-{month:02d}: {len(items)}")
            except Exception as e:
                log(f"  total-load {year}-{month:02d} FAIL {e}")
            time.sleep(t.SLEEP)
    if load_rows:
        dest = out / "total_load" / "total_load_2023_2026.csv"
        dest.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(load_rows).to_csv(dest, index=False)
        log(f"  wrote {dest} rows={len(load_rows)}")


def harvest_entsog_aggregated() -> None:
    log("== ENTSOG aggregated Italy ==")
    out = DB / "mercati-italia" / "sources" / "entsog_snam"
    out.mkdir(parents=True, exist_ok=True)
    # country-level aggregated physical flow
    for year in range(2018, 2027):
        dest = out / f"italy_aggregated_physical_flow_{year}.csv"
        url = (
            "https://transparency.entsog.eu/api/v1/aggregatedData.csv"
            f"?indicator=Physical%20Flow&countryKey=IT"
            f"&from={year}-01-01&to={year}-12-31"
            "&periodType=day&timezone=CET&limit=-1"
        )
        try:
            download(url, dest)
            n = sum(1 for _ in open(dest, encoding="utf-8", errors="replace")) - 1
            log(f"  agg IT {year}: {n} rows")
            if n <= 0:
                dest.unlink(missing_ok=True)
        except Exception as e:
            log(f"  FAIL agg {year}: {e}")
        time.sleep(0.4)


def write_gap_report() -> None:
    report = DB / "docs" / "harvest_fill_notes.md"
    lines = [
        "# Gap fill status",
        "",
        "## Filled / attempted by fill_gaps.py",
        "- Ember monthly Italy",
        "- Eurostat nrg_pc_204/205/202/203 Italy",
        "- ISTAT comuni list / geojson",
        "- GME Anno2007 retry",
        "- Terna extra APIs + total-load 2023-2026",
        "- ENTSOG aggregated Italy physical flow",
        "",
        "## Still open (need keys / portal UI)",
        "- AGSI gas storage (GIE API key gratuita)",
        "- GSE open-data CSV (ASP.NET postback)",
        "- GSE Atlaimpianti impianti (export UI)",
        "- ENTSOG SNAM point-level <2022 (API 404)",
        "- Meteo (ERA5/Open-Meteo) — non ancora avviato",
        "",
    ]
    report.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    harvest_ember_monthly()
    harvest_eurostat_prices()
    harvest_istat_pop()
    harvest_gme_2007()
    harvest_entsog_aggregated()
    harvest_terna_more()
    write_gap_report()
    log("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
