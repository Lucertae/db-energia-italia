#!/usr/bin/env python3
"""Harvest Italy consumption datasets: ARERA + Terna/ISPRA + Eurostat."""
from __future__ import annotations

import gzip
import io
import json
import re
import shutil
import sys
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"
TMP = ROOT / "_tmp"
UA = {
    "User-Agent": "Mozilla/5.0 (compatible; consumi-italia/1.0)",
    "Accept": "*/*",
}
ARERA_BASE = "https://www.arera.it"

CATALOG: list[dict] = []


def log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"), flush=True)


def download(url: str, dest: Path, *, force: bool = False) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0 and not force:
        log(f"  skip {dest.name} ({dest.stat().st_size/1e6:.2f} MB)")
        return dest
    log(f"  download {url}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)
    log(f"  -> {dest} ({dest.stat().st_size/1e6:.2f} MB)")
    return dest


def add_catalog(**kwargs) -> None:
    CATALOG.append(kwargs)


def abs_arera(href: str) -> str:
    if href.startswith("http"):
        return href
    return urllib.parse.urljoin(ARERA_BASE, href)


def scrape_arera_zips(page_url: str) -> list[str]:
    req = urllib.request.Request(page_url, headers=UA)
    html = urllib.request.urlopen(req, timeout=120).read().decode("utf-8", "replace")
    hrefs = re.findall(
        r'href=["\']([^"\']+\.zip)["\']',
        html,
        flags=re.I,
    )
    return sorted({abs_arera(h) for h in hrefs})


def harvest_arera() -> None:
    log("== ARERA ==")
    pages = {
        "domestici": "https://www.arera.it/dati-e-statistiche/dettaglio/analisi-dei-consumi-dei-clienti-domestici",
        "non_domestici_ateco": "https://www.arera.it/dati-e-statistiche/dettaglio/analisi-dei-consumi-dei-clienti-domestici-ateco",
    }
    for kind, page in pages.items():
        out = SOURCES / "arera" / kind
        out.mkdir(parents=True, exist_ok=True)
        zips = scrape_arera_zips(page)
        log(f"  {kind}: {len(zips)} zip")
        (out / "sources.json").write_text(json.dumps(zips, indent=2), encoding="utf-8")
        for url in zips:
            name = Path(urllib.parse.urlparse(url).path).name
            dest = out / name
            try:
                download(url, dest)
                add_catalog(
                    source="arera",
                    dataset=kind,
                    file=str(dest.relative_to(ROOT)).replace("\\", "/"),
                    url=url,
                    bytes=dest.stat().st_size,
                    status="ok",
                )
            except Exception as e:
                log(f"  FAIL {name}: {e}")
                add_catalog(
                    source="arera",
                    dataset=kind,
                    file=name,
                    url=url,
                    status=f"fail:{e}",
                )


def harvest_terna_ispra() -> None:
    log("== Terna/ISPRA bilanci settoriali ==")
    out = SOURCES / "terna" / "bilanci"
    out.mkdir(parents=True, exist_ok=True)
    url = (
        "https://indicatoriambientali.isprambiente.it/sites/default/files/"
        "indicatori_ambientali/2026-06-23/"
        "Tabella1_Consumi%20finali%20di%20energia%20elettrica%20per%20settore_1990_2024.xls"
    )
    xls = download(url, out / "ispr_terna_consumi_elettrici_settore_1990_2024.xls")
    # convert to csv
    csv_path = out / "consumi_elettrici_per_settore_1990_2024.csv"
    try:
        df = pd.read_excel(xls)
        df.to_csv(csv_path, index=False)
        log(f"  csv rows={len(df)} cols={list(df.columns)[:8]}")
        add_catalog(
            source="terna_ispra",
            dataset="consumi_elettrici_per_settore",
            file=str(csv_path.relative_to(ROOT)).replace("\\", "/"),
            url=url,
            rows=len(df),
            years="1990-2024",
            granularity="annual_national_sector",
            status="ok",
        )
    except Exception as e:
        log(f"  excel convert failed ({e}); keeping xls only")
        add_catalog(
            source="terna_ispra",
            dataset="consumi_elettrici_per_settore",
            file=str(xls.relative_to(ROOT)).replace("\\", "/"),
            url=url,
            status=f"xls_only:{e}",
        )

    # note about IMCEI/IMSER API
    note = SOURCES / "terna" / "IMCEI_IMSER_README.txt"
    note.parent.mkdir(parents=True, exist_ok=True)
    note.write_text(
        "\n".join(
            [
                "Terna IMCEI (industria energivori) e IMSER (servizi ATECO):",
                "  Dashboard: https://dati.terna.it/en/load/imcei",
                "             https://dati.terna.it/en/load/imser",
                "  API pubblica (richiede registrazione + token):",
                "             https://developer.terna.it/docs/read/apis_catalog",
                "  Endpoint catalogato: Monthly Index Industrial Electrical Consumption",
                "",
                "In questo harvest è incluso il bilancio annuale per settore (fonte Terna via ISPRA).",
                "Per serie mensili IMCEI/IMSER: crea app su developer.terna.it e metti il token in",
                "  db/consumi-italia/terna.token  (una riga), poi ri-lancia harvest_all.py",
                "",
            ]
        ),
        encoding="utf-8",
    )
    try_terna_api()


def try_terna_api() -> None:
    token_path = ROOT / "terna.token"
    if not token_path.exists():
        log("  Terna API: no terna.token — skip IMCEI/IMSER API pull")
        add_catalog(
            source="terna",
            dataset="imcei_imser",
            status="skipped_no_token",
            note="put OAuth token in terna.token",
        )
        return
    token = token_path.read_text(encoding="utf-8").strip()
    log("  Terna API: token found — attempting IMCEI (best-effort)")
    # Public gateway patterns used by Terna developer portal (may evolve).
    candidates = [
        "https://api.terna.it/load/v1.0/imcei",
        "https://api.terna.it/transparency/v1.0/getImcei",
        "https://api.terna.it/load/v2.0/monthly-index-industrial-electrical-consumption",
    ]
    out = SOURCES / "terna" / "imcei"
    out.mkdir(parents=True, exist_ok=True)
    headers = {
        **UA,
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
    }
    for url in candidates:
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=60) as resp:
                data = resp.read()
            dest = out / (urllib.parse.urlparse(url).path.strip("/").replace("/", "_") + ".json")
            dest.write_bytes(data)
            log(f"  OK {url} -> {dest.name} ({len(data)} bytes)")
            add_catalog(source="terna", dataset="imcei", file=str(dest.relative_to(ROOT)), url=url, status="ok")
            return
        except Exception as e:
            log(f"  try fail {url}: {e}")
    add_catalog(source="terna", dataset="imcei", status="api_endpoints_failed")


def harvest_eurostat() -> None:
    log("== Eurostat nrg_bal_c (Italy) ==")
    out = SOURCES / "eurostat"
    out.mkdir(parents=True, exist_ok=True)
    TMP.mkdir(parents=True, exist_ok=True)

    # Bulk CSV (gzip) — works more reliably than filtered JSON from this network.
    bulk_url = (
        "https://ec.europa.eu/eurostat/databrowser-backend/api/extraction/1.0/"
        "LIVE/false/sdmx/csv/nrg_bal_c?i&compressed=true"
    )
    gz_path = TMP / "nrg_bal_c.csv.gz"
    download(bulk_url, gz_path)

    italy_path = out / "nrg_bal_c_italy.csv"
    log("  filtering geo=IT ...")
    # Stream gzip CSV and keep Italy rows (column name usually 'geo')
    kept = 0
    header = None
    geo_idx = None
    with gzip.open(gz_path, "rt", encoding="utf-8", errors="replace", newline="") as fh, open(
        italy_path, "w", encoding="utf-8", newline=""
    ) as out_f:
        for i, line in enumerate(fh):
            if i == 0:
                header = line
                cols = next(csv_split(line))
                # find geo column
                lower = [c.strip().strip('"').lower() for c in cols]
                if "geo" in lower:
                    geo_idx = lower.index("geo")
                else:
                    raise RuntimeError(f"no geo column in {cols[:20]}")
                out_f.write(line if line.endswith("\n") else line + "\n")
                continue
            # cheap filter before full parse
            if ',IT,' in line or line.rstrip().endswith(',IT') or ',"IT"' in line or ',IT\n' in line:
                # verify geo cell
                try:
                    cells = next(csv_split(line))
                    if cells[geo_idx].strip().strip('"') == "IT":
                        out_f.write(line if line.endswith("\n") else line + "\n")
                        kept += 1
                except Exception:
                    continue
            if i % 2_000_000 == 0 and i:
                log(f"  scanned {i:,} lines, kept {kept:,}")

    log(f"  italy rows={kept:,} -> {italy_path}")
    add_catalog(
        source="eurostat",
        dataset="nrg_bal_c",
        file=str(italy_path.relative_to(ROOT)).replace("\\", "/"),
        url=bulk_url,
        rows=kept,
        granularity="annual_energy_balance_sectors_fuels",
        status="ok",
    )

    # also try lighter final-energy-focused extract if pandas can load
    try:
        sample = pd.read_csv(italy_path, nrows=5)
        log(f"  columns: {list(sample.columns)}")
        # build a thinner final-consumption slice if nrg_bal / nrg_cons column exists
        df = pd.read_csv(italy_path, low_memory=False)
        bal_col = None
        for c in df.columns:
            if c.lower() in ("nrg_bal", "nrg_cons", "indic_nrg"):
                bal_col = c
                break
        if bal_col:
            # keep final consumption-ish codes
            mask = df[bal_col].astype(str).str.startswith(("FC_", "FEC", "FC"))
            thin = df[mask].copy()
            thin_path = out / "nrg_bal_c_italy_final_consumption.csv"
            thin.to_csv(thin_path, index=False)
            log(f"  final-consumption slice rows={len(thin)}")
            add_catalog(
                source="eurostat",
                dataset="nrg_bal_c_final_consumption",
                file=str(thin_path.relative_to(ROOT)).replace("\\", "/"),
                rows=len(thin),
                status="ok",
            )
    except Exception as e:
        log(f"  thin slice skipped: {e}")


def csv_split(line: str):
    """Yield one row of cells from a CSV line via pandas engine-free csv module."""
    import csv as _csv

    yield from _csv.reader([line])


def write_outputs() -> None:
    cat = ROOT / "catalog.csv"
    pd.DataFrame(CATALOG).to_csv(cat, index=False)
    log(f"catalog -> {cat}")

    lines = [
        "Consumi Italia — Terna/ISPRA + ARERA + Eurostat",
        f"Root: {ROOT}",
        "",
        "Refresh: python db/consumi-italia/scripts/harvest_all.py",
        "",
        "Sorgenti:",
    ]
    for src in sorted(SOURCES.iterdir()) if SOURCES.exists() else []:
        if not src.is_dir():
            continue
        files = [f for f in src.rglob("*") if f.is_file()]
        size = sum(f.stat().st_size for f in files)
        lines.append(f"  {src.name}: {len(files)} files, {size/1e6:.2f} MB")
    lines += [
        "",
        "Note Terna IMCEI/IMSER: richiede token developer.terna.it -> terna.token",
        "",
    ]
    (ROOT / "METADATI.txt").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    SOURCES.mkdir(parents=True, exist_ok=True)
    harvest_arera()
    harvest_terna_ispra()
    harvest_eurostat()
    write_outputs()
    log("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
