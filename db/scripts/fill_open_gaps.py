#!/usr/bin/env python3
"""Fill remaining open gaps that are still programmatically reachable."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import date
from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "Mozilla/5.0 (compatible; fill-open-gaps/1.0)"}


def log(msg: str) -> None:
    print(msg, flush=True)


def download(url: str, dest: Path, *, min_size: int = 500, timeout: int = 300, force: bool = False) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= min_size and not force:
        log(f"  skip {dest.name} ({dest.stat().st_size/1e6:.2f} MB)")
        return True
    log(f"  GET {url[:160]}")
    req = urllib.request.Request(url, headers=UA)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as f:
            shutil.copyfileobj(resp, f)
        head = tmp.read_bytes()[:60].lower()
        if head.startswith(b"<!doctype") or head.startswith(b"<html"):
            tmp.unlink(missing_ok=True)
            log(f"  FAIL HTML {dest.name}")
            return False
        if tmp.stat().st_size < min_size:
            tmp.unlink(missing_ok=True)
            log(f"  FAIL small {dest.name}")
            return False
        tmp.replace(dest)
        log(f"  -> {dest.name} ({dest.stat().st_size/1e6:.2f} MB)")
        return True
    except Exception as e:
        tmp.unlink(missing_ok=True)
        log(f"  FAIL {dest.name}: {e}")
        return False


def harvest_ispra_ghg() -> None:
    log("== ISPRA / SINAnet GHG tables ==")
    out = DB / "consumi-italia" / "sources" / "ispra" / "ghg"
    out.mkdir(parents=True, exist_ok=True)
    pages = [
        "https://emissioni.sina.isprambiente.it/inventario-nazionale/",
        "https://emissioni.sina.isprambiente.it/inventari-locali/",
        "https://emissioni.sina.isprambiente.it/news/",
        "https://emissioni.sina.isprambiente.it/",
    ]
    urls: set[str] = set()
    for page in pages:
        try:
            req = urllib.request.Request(page, headers=UA)
            html = urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "replace")
            for m in re.findall(
                r"https://emissioni\.sina\.isprambiente\.it/wp-content/uploads/[^\s\"'<>]+\.(?:xlsx?|csv|zip|pdf)",
                html,
                re.I,
            ):
                urls.add(m)
            # relative uploads
            for m in re.findall(r"/wp-content/uploads/[^\s\"'<>]+\.(?:xlsx?|csv|zip)", html, re.I):
                urls.add("https://emissioni.sina.isprambiente.it" + m)
        except Exception as e:
            log(f"  crawl {page}: {e}")

    # Known UNFCCC CRF / EEA open dumps for Italy filter later
    extra = [
        "https://www.eea.europa.eu/data-and-maps/data/national-emissions-reported-to-the-unfccc-and-to-the-eu-greenhouse-gas-monitoring-mechanism-21/national-greenhouse-gas-inventories-ipcc-common-reporting-format-sector-classification/greenhouse-gas-emissions-under-the-unfccc.csv/at_download/file",
        "https://sdi.eea.europa.eu/catalogue/srv/api/records/9b0e0e8a-8d0f-4f0d-9b0e-greenhouse/attachments",
    ]
    for u in sorted(urls):
        name = urllib.parse.unquote(u.rstrip("/").split("/")[-1])
        # prefer GHG / inventory / NIR / NFR / SNAP naming
        low = name.lower()
        if any(k in low for k in ("ghg", "nfr", "snap", "nir", "emiss", "invent", "co2", "crf", "serie")) or low.endswith((".xlsx", ".xls", ".csv", ".zip")):
            download(u, out / name, min_size=800)
            time.sleep(0.2)

    # UNFCCC Annex I Italy flexible query via climate.copernicus / EDGAR already have some
    # Try climatewatch / CAIT Italy GHG
    download(
        "https://www.climatewatchdata.org/api/v1/data/historical_emissions?regions[]=ITA&source_ids[]=59&gas_ids[]=252&page=1&per_page=1000",
        out / "climatewatch_italy_probe.json",
        min_size=50,
        timeout=120,
    )


def harvest_eua() -> None:
    log("== EUA / carbon prices ==")
    out = DB / "mercati-italia" / "sources" / "ets_eua"
    out.mkdir(parents=True, exist_ok=True)
    # ICAP allowance price explorer weekly CSV (EU ETS) — probe public endpoints
    candidates = [
        # EEX auction reports alternate paths
        "https://www.eex.com/fileadmin/EEX/Downloads/Trading/Market_Data/Environmentals/emission-spot-primary-market-auction-report-2024-data.xlsx",
        "https://www.eex.com/fileadmin/EEX/Downloads/Trading/Market_Data/Environmentals/emission-spot-primary-market-auction-report-2025-data.xlsx",
        "https://www.eex.com/fileadmin/EEX/Downloads/Trading/Environmentals/emission-spot-primary-market-auction-report-2023-data.xlsx",
        "https://www.eex.com/fileadmin/EEX/Downloads/Trading/Environmentals/emission-spot-primary-market-auction-report-2022-data.xlsx",
        # Ember European prices already have carbon sometimes in tools — try dedicated
        "https://files.ember-energy.org/public-downloads/european_electricity_review_2025_data.xlsx",
        "https://files.ember-energy.org/public-downloads/european_electricity_review_2024_data.xlsx",
        # Our World in Data energy price / carbon if published as CSV
        "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv",
    ]
    for url in candidates:
        name = url.rsplit("/", 1)[-1]
        download(url, out / name, min_size=1000, timeout=180)
        time.sleep(0.3)

    # Yahoo Finance EUA futures continuous (free) via query1
    # ticker: CFI2Z25.EX or similar — try EU carbon
    yurls = [
        (
            "https://query1.finance.yahoo.com/v7/finance/download/CFI2Z24.EX"
            "?period1=1420070400&period2=9999999999&interval=1d&events=history"
        ),
        (
            "https://query1.finance.yahoo.com/v8/finance/chart/CFI2Z25.EX"
            "?period1=1420070400&period2=9999999999&interval=1d"
        ),
    ]
    for i, url in enumerate(yurls):
        download(url, out / f"yahoo_eua_probe_{i}.csv", min_size=100, timeout=60)


def harvest_mase() -> None:
    log("== MASE / bilanci energetici ==")
    out = DB / "consumi-italia" / "sources" / "mase"
    out.mkdir(parents=True, exist_ok=True)
    # Ministry pages / known open data mirrors
    pages = [
        "https://dgsaie.mise.gov.it/bilancio-energetico-nazionale",
        "https://dgsaie.mise.gov.it/",
        "https://www.mase.gov.it/energia/statistiche",
    ]
    found: set[str] = set()
    for page in pages:
        try:
            req = urllib.request.Request(page, headers=UA)
            html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
            for m in re.findall(r'href=["\']([^"\']+\.(?:xlsx?|csv|pdf|zip))["\']', html, re.I):
                url = urllib.parse.urljoin(page, m)
                found.add(url)
            log(f"  page {page}: {len(found)} links so far")
        except Exception as e:
            log(f"  page fail {page}: {e}")
    keep = [u for u in found if any(k in u.lower() for k in ("bilan", "energia", "petrol", "consumo", "ben", "statist"))]
    for url in sorted(keep)[:40]:
        name = urllib.parse.unquote(url.rstrip("/").split("/")[-1]) or "file.bin"
        name = re.sub(r"[^\w.\-]+", "_", name)[:120]
        download(url, out / name, min_size=500, timeout=120)
        time.sleep(0.2)
    (out / "discovered_links.json").write_text(json.dumps(sorted(found), indent=2), encoding="utf-8")


def harvest_gme_2007() -> None:
    log("== GME Anno2007 retry ==")
    out = DB / "mercati-italia" / "sources" / "gme" / "mgp_storici"
    out.mkdir(parents=True, exist_ok=True)
    dest = out / "Anno2007.zip"
    url = (
        "https://gme.mercatoelettrico.org/it-it/Home/Esiti/Elettricita/MGP/"
        "Statistiche/DatiStorici/moduleId/10874/controller/GmeDatiStoriciItem/"
        "action/DownloadFile?fileName=Anno2007.zip"
    )
    part = dest.with_suffix(".zip.part")
    part.unlink(missing_ok=True)
    cmd = [
        "curl.exe", "-L", "--fail", "--retry", "3", "--retry-delay", "5",
        "--connect-timeout", "30", "--max-time", "600",
        "-A", UA["User-Agent"], "-o", str(part), url,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    size = part.stat().st_size if part.exists() else 0
    if proc.returncode != 0 or size < 100_000:
        log(f"  still fail rc={proc.returncode} size={size}")
        part.unlink(missing_ok=True)
        return
    try:
        with zipfile.ZipFile(part) as zf:
            if zf.testzip() is not None:
                raise RuntimeError("corrupt zip")
        part.replace(dest)
        extract = out / "Anno2007"
        if extract.exists():
            shutil.rmtree(extract)
        extract.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest) as zf:
            zf.extractall(extract)
        log(f"  Anno2007 OK {dest.stat().st_size/1e6:.2f} MB")
        (out / "Anno2007.FAILED.txt").unlink(missing_ok=True)
    except Exception as e:
        log(f"  zip invalid: {e}")
        part.unlink(missing_ok=True)


def harvest_gme_secondary_probe() -> None:
    """Probe GME public result endpoints / historical pages for MI MSD."""
    log("== GME MI/MSD/MB probe ==")
    out = DB / "mercati-italia" / "sources" / "gme"
    note = {
        "status": "blocked_interactive",
        "note": (
            "Yearly DatiStorici ZIP only works for MGP. MI/MSD/MB require the Download UI "
            "(period XML zip) or authenticated API. Place manual exports under mi/, msd/, mb/."
        ),
        "ui": [
            "https://www.mercatoelettrico.org/it-it/Home/Esiti/Elettricita/MI/Download/Download",
            "https://www.mercatoelettrico.org/it-it/Home/Esiti/Elettricita/MSD/ExPost/Download/Download",
            "https://www.mercatoelettrico.org/it-it/Home/Esiti/Elettricita/MSD/ExAnte/Download/Download",
        ],
    }
    # Try common moduleIds for MI/MSD yearly if any still work
    base = (
        "https://gme.mercatoelettrico.org/it-it/Home/Esiti/Elettricita/{market}/"
        "Statistiche/DatiStorici/moduleId/{mid}/controller/GmeDatiStoriciItem/"
        "action/DownloadFile?fileName=Anno2023.zip"
    )
    hits = []
    for market, mids in [("MI", range(10870, 10890)), ("MSD", range(10870, 10890)), ("MB", range(10870, 10890))]:
        for mid in mids:
            url = base.format(market=market, mid=mid)
            try:
                req = urllib.request.Request(url, headers=UA)
                with urllib.request.urlopen(req, timeout=25) as resp:
                    chunk = resp.read(4)
                    ctype = resp.headers.get("Content-Type", "")
                if chunk.startswith(b"PK"):
                    hits.append({"market": market, "moduleId": mid, "url": url})
                    log(f"  HIT zip {market} mid={mid}")
                    dest = out / market.lower() / f"Anno2023_mid{mid}.zip"
                    download(url, dest, min_size=20_000, timeout=300)
                    break
            except Exception:
                continue
            time.sleep(0.05)
    note["zip_hits"] = hits
    (out / "secondary_markets_status.json").write_text(json.dumps(note, indent=2), encoding="utf-8")
    log(f"  zip hits: {len(hits)}")


def harvest_eurostat_more() -> None:
    log("== Eurostat remaining energy IT ==")
    out = DB / "consumi-italia" / "sources" / "eurostat"
    out.mkdir(parents=True, exist_ok=True)
    codes = [
        "nrg_bal_c",
        "nrg_ind_epcrf",
        "nrg_inf_epcrf",
        "nrg_cb_oilm",
        "nrg_ti_oilm",
        "env_ac_ainah_r2",
    ]
    for code in codes:
        italy = out / f"{code}_italy.csv"
        if italy.exists() and italy.stat().st_size > 500:
            log(f"  skip {italy.name}")
            continue
        gz = DB / "consumi-italia" / "_tmp" / f"{code}.csv.gz"
        gz.parent.mkdir(parents=True, exist_ok=True)
        url = f"https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{code}/?format=SDMX-CSV&compressed=true"
        if not download(url, gz, min_size=200, force=True, timeout=300):
            continue
        import csv
        import gzip

        kept = 0
        with gzip.open(gz, "rt", encoding="utf-8", errors="replace", newline="") as fh, open(
            italy, "w", encoding="utf-8", newline=""
        ) as out_f:
            geo_idx = None
            for i, line in enumerate(fh):
                if i == 0:
                    cols = next(csv.reader([line]))
                    lower = [c.strip().strip('"').lower() for c in cols]
                    geo_idx = lower.index("geo") if "geo" in lower else None
                    out_f.write(line if line.endswith("\n") else line + "\n")
                    continue
                if geo_idx is None:
                    break
                if ",IT," in line or ',"IT"' in line or line.rstrip().endswith(",IT"):
                    cells = next(csv.reader([line]))
                    if cells[geo_idx].strip().strip('"') == "IT":
                        out_f.write(line if line.endswith("\n") else line + "\n")
                        kept += 1
        log(f"  {code} Italy rows={kept}")
        time.sleep(0.25)


def main() -> int:
    harvest_ispra_ghg()
    harvest_eua()
    harvest_mase()
    harvest_eurostat_more()
    harvest_gme_2007()
    harvest_gme_secondary_probe()
    log("DONE fill_open_gaps")
    return 0


if __name__ == "__main__":
    sys.exit(main())
