#!/usr/bin/env python3
"""Harvest GME historical prices + ENTSOG/SNAM gas flows (+ GSE catalog)."""
from __future__ import annotations

import json
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources"
UA = {"User-Agent": "Mozilla/5.0 (compatible; mercati-italia/1.0)"}
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
    log(f"  download {url[:120]}...")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)
    log(f"  -> {dest.name} ({dest.stat().st_size/1e6:.2f} MB)")
    return dest


def add_cat(**kw) -> None:
    CATALOG.append(kw)


def harvest_gme() -> None:
    log("== GME MGP dati storici ==")
    out = SOURCES / "gme" / "mgp_storici"
    out.mkdir(parents=True, exist_ok=True)
    base = (
        "https://gme.mercatoelettrico.org/it-it/Home/Esiti/Elettricita/MGP/"
        "Statistiche/DatiStorici/moduleId/10874/controller/GmeDatiStoriciItem/"
        "action/DownloadFile?fileName="
    )
    for year in range(2004, 2027):
        name = f"Anno{year}.zip"
        dest = out / name
        try:
            download(base + name, dest)
            # extract xlsx
            extract_dir = out / f"Anno{year}"
            extract_dir.mkdir(exist_ok=True)
            with zipfile.ZipFile(dest, "r") as zf:
                zf.extractall(extract_dir)
            xlsx = list(extract_dir.glob("*.xlsx")) + list(extract_dir.glob("*.xls"))
            add_cat(
                source="gme",
                dataset="mgp_storici",
                year=year,
                file=str(dest.relative_to(ROOT)).replace("\\", "/"),
                extracted=[str(p.relative_to(ROOT)).replace("\\", "/") for p in xlsx],
                status="ok",
            )
        except Exception as e:
            log(f"  FAIL {year}: {e}")
            add_cat(source="gme", dataset="mgp_storici", year=year, status=f"fail:{e}")
        time.sleep(0.3)


def harvest_entsog_snam() -> None:
    log("== ENTSOG / SNAM gas ==")
    out = SOURCES / "entsog_snam"
    out.mkdir(parents=True, exist_ok=True)

    # operators catalog (IT filter)
    ops = download(
        "https://transparency.entsog.eu/api/v1/operators.csv?limit=-1",
        out / "operators_all.csv",
    )
    # filter Italy rows to a thin file
    it_lines = []
    with open(ops, encoding="utf-8", errors="replace") as fh:
        header = fh.readline()
        it_lines.append(header)
        for line in fh:
            if ",IT," in line or "Italy" in line:
                it_lines.append(line)
    it_path = out / "operators_italy.csv"
    it_path.write_text("".join(it_lines), encoding="utf-8")
    add_cat(source="entsog", dataset="operators_italy", file=str(it_path.relative_to(ROOT)), status="ok")

    # points for SNAM
    download(
        "https://transparency.entsog.eu/api/v1/operatorpointdirections.csv?operatorKey=IT-TSO-0001&hasData=1&limit=-1",
        out / "snam_rete_gas_points.csv",
    )
    add_cat(
        source="entsog",
        dataset="snam_points",
        file="sources/entsog_snam/snam_rete_gas_points.csv",
        status="ok",
    )

    # physical flows by year (daily) for Snam Rete Gas
    # Note: ENTSOG often 404 for older years / storage operators without Physical Flow
    targets = [
        ("IT-TSO-0001", "snam_rete_gas"),
    ]
    for op_key, slug in targets:
        for year in range(2015, 2027):
            dest = out / f"{slug}_physical_flow_{year}.csv"
            url = (
                "https://transparency.entsog.eu/api/v1/operationaldatas.csv"
                f"?operatorKey={op_key}&indicator=Physical%20Flow"
                f"&from={year}-01-01&to={year}-12-31"
                "&periodType=day&timezone=CET&limit=-1"
            )
            try:
                download(url, dest)
                n = sum(1 for _ in open(dest, encoding="utf-8", errors="replace")) - 1
                if n <= 0:
                    dest.unlink(missing_ok=True)
                    add_cat(
                        source="entsog",
                        dataset=f"{slug}_physical_flow",
                        year=year,
                        status="empty",
                    )
                    continue
                add_cat(
                    source="entsog",
                    dataset=f"{slug}_physical_flow",
                    year=year,
                    file=str(dest.relative_to(ROOT)).replace("\\", "/"),
                    rows=n,
                    status="ok",
                )
                log(f"  {slug} {year}: {n} rows")
            except Exception as e:
                log(f"  FAIL {slug} {year}: {e}")
                add_cat(
                    source="entsog",
                    dataset=f"{slug}_physical_flow",
                    year=year,
                    status=f"fail:{e}",
                )
            time.sleep(0.5)


def harvest_gse_catalog() -> None:
    log("== GSE open data catalog ==")
    out = SOURCES / "gse"
    out.mkdir(parents=True, exist_ok=True)
    home = "https://opendata.gse.it/"
    req = urllib.request.Request(home, headers=UA)
    html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
    ids = sorted({int(m) for m in re.findall(r"VisualizzaDataset\.aspx\?itemId=(\d+)", html)})
    # also scan DataSet.aspx
    try:
        req = urllib.request.Request("https://opendata.gse.it/SitePages/DataSet.aspx", headers=UA)
        html2 = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        ids = sorted(set(ids) | {int(m) for m in re.findall(r"VisualizzaDataset\.aspx\?itemId=(\d+)", html2)})
    except Exception as e:
        log(f"  DataSet.aspx: {e}")

    catalog = []
    for item_id in ids:
        url = f"https://opendata.gse.it/SitePages/VisualizzaDataset.aspx?itemId={item_id}"
        try:
            req = urllib.request.Request(url, headers=UA)
            page = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
            # title
            title_m = re.search(r"<title>([^<]+)</title>", page, re.I)
            title = (title_m.group(1).strip() if title_m else "")[:200]
            # file names mentioned
            files = re.findall(r"([A-Za-z0-9_\-]+\.(?:csv|xls|xlsx|json|xml))", page, re.I)
            catalog.append({"itemId": item_id, "url": url, "title": title, "files_mentioned": sorted(set(files))})
            log(f"  item {item_id}: {title[:80]} files={files[:5]}")
        except Exception as e:
            catalog.append({"itemId": item_id, "url": url, "error": str(e)})
        time.sleep(0.2)

    cat_path = out / "opendata_catalog.json"
    cat_path.write_text(json.dumps(catalog, indent=2, ensure_ascii=False), encoding="utf-8")
    note = out / "README.txt"
    note.write_text(
        "\n".join(
            [
                "GSE Open Data (opendata.gse.it) elenca dataset incentivi/beneficiari.",
                "I download CSV usano postback ASP.NET (non URL statiche).",
                "Catalogo itemId in opendata_catalog.json.",
                "Per bulk impianti georiferiti: Atlaimpianti (export manuale/XLS dal portale GSE).",
                "URL catalogo: https://opendata.gse.it/",
                "",
            ]
        ),
        encoding="utf-8",
    )
    add_cat(
        source="gse",
        dataset="opendata_catalog",
        file=str(cat_path.relative_to(ROOT)).replace("\\", "/"),
        n_datasets=len(catalog),
        status="catalog_only_aspnet_postback",
    )


def harvest_ember() -> None:
    """Bonus: Ember yearly electricity (easy Italy filter)."""
    log("== Ember Europe electricity (bonus) ==")
    out = SOURCES / "ember"
    out.mkdir(parents=True, exist_ok=True)
    candidates = [
        "https://files.ember-energy.org/public-downloads/yearly_full_release_long_format.csv",
        "https://files.ember-energy.org/public-downloads/european_electricity_review_data.xlsx",
    ]
    dest = out / "yearly_full_release_long_format.csv"
    ok = False
    last_err = None
    for url in candidates:
        if not url.endswith(".csv"):
            continue
        try:
            download(url, dest, force=True)
            # reject HTML masquerading as CSV
            head = dest.read_bytes()[:200].lower()
            if b"<html" in head or b"<!doctype" in head:
                dest.unlink(missing_ok=True)
                raise RuntimeError("got HTML instead of CSV")
            ok = True
            add_cat(
                source="ember",
                dataset="yearly_electricity",
                file=str(dest.relative_to(ROOT)).replace("\\", "/"),
                url=url,
                status="ok",
            )
            break
        except Exception as e:
            last_err = e
            log(f"  try fail: {e}")
    if not ok:
        add_cat(source="ember", dataset="yearly_electricity", status=f"download_failed:{last_err}")
        return
    import pandas as pd

    df = pd.read_csv(dest, low_memory=False)
    country_col = None
    for c in df.columns:
        if c.lower() in ("country", "area", "entity"):
            country_col = c
            break
    if country_col:
        it = df[df[country_col].astype(str).str.lower().eq("italy")].copy()
        it_path = out / "italy_yearly.csv"
        it.to_csv(it_path, index=False)
        log(f"  Italy rows={len(it)}")
        add_cat(
            source="ember",
            dataset="italy_yearly",
            file=str(it_path.relative_to(ROOT)).replace("\\", "/"),
            rows=len(it),
            status="ok",
        )


def write_meta() -> None:
    pd_rows = CATALOG
    try:
        import pandas as pd

        pd.DataFrame(pd_rows).to_csv(ROOT / "catalog.csv", index=False)
    except Exception:
        (ROOT / "catalog.json").write_text(json.dumps(pd_rows, indent=2), encoding="utf-8")

    lines = [
        "Mercati Italia — GME + ENTSOG/SNAM (+ GSE catalog + Ember)",
        f"Root: {ROOT}",
        "Refresh: python db/mercati-italia/scripts/harvest_all.py",
        "",
    ]
    for src in sorted(SOURCES.iterdir()) if SOURCES.exists() else []:
        if not src.is_dir():
            continue
        files = [f for f in src.rglob("*") if f.is_file()]
        size = sum(f.stat().st_size for f in files)
        lines.append(f"  {src.name}: {len(files)} files, {size/1e6:.2f} MB")
    (ROOT / "METADATI.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    SOURCES.mkdir(parents=True, exist_ok=True)
    harvest_gme()
    harvest_entsog_snam()
    harvest_gse_catalog()
    harvest_ember()
    write_meta()
    log("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
