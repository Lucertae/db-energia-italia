#!/usr/bin/env python3
"""Harvest OWID public data repos → Italy-only extracts under db/owid-italia/."""
from __future__ import annotations

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
UA = {"User-Agent": "owid-italia-harvest/1.0"}

COUNTRY_COLS = {
    "country",
    "entity",
    "location",
    "nation",
    "nation_name",
    "country_name",
    "geo",
    "area",
}
ITALY_VALUES = {"italy", "italia", "italian republic", "ita"}


def log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"), flush=True)


def download(url: str, dest: Path) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        log(f"  skip existing {dest.name} ({dest.stat().st_size/1e6:.2f} MB)")
        return dest
    log(f"  download {url}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=600) as resp, open(dest, "wb") as f:
        shutil.copyfileobj(resp, f)
    log(f"  -> {dest} ({dest.stat().st_size/1e6:.2f} MB)")
    return dest


def find_country_col(columns: list[str]) -> str | None:
    lower = {c.lower().strip(): c for c in columns}
    for key in COUNTRY_COLS:
        if key in lower:
            return lower[key]
    # fuzzy: column name contains country/entity
    for low, orig in lower.items():
        if any(k in low for k in ("country", "entity", "location", "nation")):
            return orig
    return None


def is_italy(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip().str.lower()
    return s.isin(ITALY_VALUES)


def filter_italy_csv(
    src: Path,
    dest: Path,
    *,
    chunksize: int | None = None,
) -> dict:
    """Filter Italy rows from CSV. Returns catalog stats."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        peek = pd.read_csv(src, nrows=5, low_memory=False)
    except Exception as e:
        return {"ok": False, "error": f"read_fail: {e}", "rows": 0}

    col = find_country_col(list(peek.columns))
    if not col:
        return {"ok": False, "error": "no_country_col", "rows": 0, "columns": list(peek.columns)[:20]}

    parts: list[pd.DataFrame] = []
    total_in = 0
    if chunksize:
        for chunk in pd.read_csv(src, chunksize=chunksize, low_memory=False):
            total_in += len(chunk)
            parts.append(chunk[is_italy(chunk[col])])
        it = pd.concat(parts, ignore_index=True) if parts else peek.iloc[0:0]
    else:
        df = pd.read_csv(src, low_memory=False)
        total_in = len(df)
        it = df[is_italy(df[col])].copy()

    if len(it) == 0:
        return {"ok": True, "has_italy": False, "rows": 0, "country_col": col, "rows_in": total_in}

    it.to_csv(dest, index=False)
    return {
        "ok": True,
        "has_italy": True,
        "rows": len(it),
        "country_col": col,
        "rows_in": total_in,
        "out": str(dest.relative_to(ROOT)).replace("\\", "/"),
    }


def melt_italy(wide: Path, long_path: Path, id_candidates: tuple[str, ...]) -> None:
    df = pd.read_csv(wide, low_memory=False)
    id_cols = [c for c in id_candidates if c in df.columns]
    if not id_cols:
        id_cols = [c for c in df.columns if c.lower() in COUNTRY_COLS | {"year", "iso_code", "date"}][:5]
    value_cols = [c for c in df.columns if c not in id_cols]
    long = df.melt(id_vars=id_cols, value_vars=value_cols, var_name="metric", value_name="value")
    long = long.dropna(subset=["value"])
    long.to_csv(long_path, index=False)


def harvest_energy() -> None:
    log("== energy-data ==")
    out = SOURCES / "energy-data"
    out.mkdir(parents=True, exist_ok=True)
    base = "https://raw.githubusercontent.com/owid/energy-data/master"
    download(f"{base}/owid-energy-data.csv", out / "owid-energy-data.csv")
    download(f"{base}/owid-energy-codebook.csv", out / "owid-energy-codebook.csv")
    stats = filter_italy_csv(out / "owid-energy-data.csv", out / "italy_energy.csv")
    log(f"  italy: {stats}")
    if stats.get("has_italy"):
        melt_italy(
            out / "italy_energy.csv",
            out / "italy_energy_long.csv",
            ("country", "year", "iso_code", "population", "gdp"),
        )


def harvest_co2() -> None:
    log("== co2-data ==")
    out = SOURCES / "co2-data"
    out.mkdir(parents=True, exist_ok=True)
    base = "https://raw.githubusercontent.com/owid/co2-data/master"
    download(f"{base}/owid-co2-data.csv", out / "owid-co2-data.csv")
    download(f"{base}/owid-co2-codebook.csv", out / "owid-co2-codebook.csv")
    stats = filter_italy_csv(out / "owid-co2-data.csv", out / "italy_co2.csv")
    log(f"  italy: {stats}")
    if stats.get("has_italy"):
        melt_italy(
            out / "italy_co2.csv",
            out / "italy_co2_long.csv",
            ("country", "year", "iso_code", "population", "gdp"),
        )
    # drop bulky global after extract (approach A)
    global_csv = out / "owid-co2-data.csv"
    if global_csv.exists() and (out / "italy_co2.csv").exists():
        global_csv.unlink()
        log("  removed global owid-co2-data.csv (kept italy + codebook)")


def harvest_poverty() -> None:
    log("== poverty-data ==")
    out = SOURCES / "poverty-data"
    out.mkdir(parents=True, exist_ok=True)
    base = "https://raw.githubusercontent.com/owid/poverty-data/main/datasets"
    download(f"{base}/pip_dataset.csv", out / "pip_dataset.csv")
    download(f"{base}/pip_codebook.csv", out / "pip_codebook.csv")
    download(f"{base}/pip_README.md", out / "pip_README.md")
    stats = filter_italy_csv(out / "pip_dataset.csv", out / "italy_poverty.csv")
    log(f"  italy: {stats}")
    global_csv = out / "pip_dataset.csv"
    if global_csv.exists() and (out / "italy_poverty.csv").exists():
        global_csv.unlink()
        log("  removed global pip_dataset.csv")


def harvest_covid() -> None:
    log("== covid-19-data ==")
    out = SOURCES / "covid-19-data"
    out.mkdir(parents=True, exist_ok=True)
    base = "https://raw.githubusercontent.com/owid/covid-19-data/master/public/data"
    download(f"{base}/owid-covid-codebook.csv", out / "owid-covid-codebook.csv")
    global_path = out / "owid-covid-data.csv"
    download(f"{base}/owid-covid-data.csv", global_path)
    stats = filter_italy_csv(global_path, out / "italy_covid.csv", chunksize=50_000)
    log(f"  italy: {stats}")
    if global_path.exists() and (out / "italy_covid.csv").exists():
        global_path.unlink()
        log("  removed global owid-covid-data.csv")


def harvest_energy_use_products() -> None:
    log("== energy-use-products ==")
    out = SOURCES / "energy-use-products"
    out.mkdir(parents=True, exist_ok=True)
    base = "https://raw.githubusercontent.com/owid/energy-use-products/main"
    for name in (
        "products_data.json",
        "Energy use of products.xlsx",
        "README.md",
        "Methodology_Sources.txt",
    ):
        try:
            download(f"{base}/{urllib.parse.quote(name)}", out / name)
        except Exception as e:
            log(f"  warn {name}: {e}")


def safe_slug(name: str) -> str:
    import hashlib

    s = re.sub(r"[^\w\-]+", "_", name, flags=re.UNICODE).strip("_")
    s = s[:100] or "dataset"
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
    return f"{s}_{digest}"



def ensure_owid_datasets_zip() -> Path:
    """Download owid-datasets zipball (Windows-safe: no full extract)."""
    TMP.mkdir(parents=True, exist_ok=True)
    zip_path = TMP / "owid-datasets.zip"
    # cleanup broken git clone leftovers
    bad = TMP / "owid-datasets"
    if bad.exists():
        shutil.rmtree(bad, ignore_errors=True)
    download(
        "https://codeload.github.com/owid/owid-datasets/zip/refs/heads/master",
        zip_path,
    )
    return zip_path


def filter_italy_from_zip_member(zf: zipfile.ZipFile, member: str, dest: Path) -> dict:
    """Filter Italy rows reading CSV directly from zip (avoids illegal Windows paths)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    try:
        with zf.open(member) as fh:
            peek = pd.read_csv(fh, nrows=5, low_memory=False)
    except Exception as e:
        return {"ok": False, "error": f"read_fail: {e}", "rows": 0}

    col = find_country_col(list(peek.columns))
    if not col:
        return {"ok": False, "error": "no_country_col", "rows": 0}

    try:
        with zf.open(member) as fh:
            df = pd.read_csv(fh, low_memory=False)
    except Exception as e:
        return {"ok": False, "error": f"read_fail: {e}", "rows": 0}

    it = df[is_italy(df[col])].copy()
    if len(it) == 0:
        return {
            "ok": True,
            "has_italy": False,
            "rows": 0,
            "country_col": col,
            "rows_in": len(df),
        }
    it.to_csv(dest, index=False)
    return {
        "ok": True,
        "has_italy": True,
        "rows": len(it),
        "country_col": col,
        "rows_in": len(df),
        "out": str(dest.relative_to(ROOT)).replace("\\", "/"),
    }


def harvest_owid_datasets() -> None:
    log("== owid-datasets ==")
    zip_path = ensure_owid_datasets_zip()
    out_root = SOURCES / "owid-datasets"
    italy_dir = out_root / "italy"
    italy_dir.mkdir(parents=True, exist_ok=True)

    catalog: list[dict] = []
    with zipfile.ZipFile(zip_path, "r") as zf:
        # group csv members by dataset folder under .../datasets/<name>/
        by_dataset: dict[str, list[zipfile.ZipInfo]] = {}
        for info in zf.infolist():
            if info.is_dir() or not info.filename.lower().endswith(".csv"):
                continue
            parts = info.filename.replace("\\", "/").split("/")
            # owid-datasets-master/datasets/<dataset>/<file>.csv
            if len(parts) < 4 or parts[1] != "datasets":
                continue
            ds_name = parts[2]
            by_dataset.setdefault(ds_name, []).append(info)

        names = sorted(by_dataset.keys())
        log(f"  scanning {len(names)} dataset folders in zip")

        for i, ds_name in enumerate(names, 1):
            infos = by_dataset[ds_name]
            info = max(infos, key=lambda z: z.file_size)
            slug = safe_slug(ds_name)
            dest = italy_dir / f"{slug}.csv"
            stats = filter_italy_from_zip_member(zf, info.filename, dest)
            row = {
                "dataset": ds_name,
                "source_csv": Path(info.filename).name,
                "has_italy": bool(stats.get("has_italy")),
                "rows": int(stats.get("rows") or 0),
                "country_col": stats.get("country_col"),
                "status": "ok" if stats.get("ok") else stats.get("error", "fail"),
                "out": stats.get("out", ""),
            }
            catalog.append(row)
            if i % 50 == 0 or stats.get("has_italy"):
                flag = "ITA" if stats.get("has_italy") else "—"
                log(f"  [{i}/{len(names)}] {flag} {ds_name[:60]} rows={row['rows']}")
            if not stats.get("has_italy") and dest.exists():
                dest.unlink(missing_ok=True)

    cat_path = out_root / "catalog.csv"
    pd.DataFrame(catalog).to_csv(cat_path, index=False)
    n_ita = sum(1 for r in catalog if r.get("has_italy"))
    log(f"  catalog: {len(catalog)} datasets, {n_ita} with Italy -> {cat_path}")
    (out_root / "summary.json").write_text(
        json.dumps(
            {
                "datasets_scanned": len(catalog),
                "datasets_with_italy": n_ita,
                "italy_files": n_ita,
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def write_metadati() -> None:
    lines = [
        "OWID Italia — estratti solo Italia (approccio A)",
        f"Root: {ROOT}",
        "",
        "Sorgenti:",
        "  energy-data, co2-data, poverty-data, covid-19-data,",
        "  energy-use-products, owid-datasets",
        "",
        "Refresh:",
        "  python db/owid-italia/scripts/harvest_all.py",
        "",
    ]
    for src in sorted(SOURCES.iterdir()) if SOURCES.exists() else []:
        if not src.is_dir():
            continue
        files = list(src.rglob("*"))
        n_files = sum(1 for f in files if f.is_file())
        size = sum(f.stat().st_size for f in files if f.is_file())
        lines.append(f"  {src.name}: {n_files} files, {size/1e6:.2f} MB")
    (ROOT / "METADATI.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    SOURCES.mkdir(parents=True, exist_ok=True)
    harvest_energy()
    harvest_co2()
    harvest_poverty()
    harvest_covid()
    harvest_energy_use_products()
    harvest_owid_datasets()
    write_metadati()
    log("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
