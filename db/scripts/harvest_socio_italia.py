#!/usr/bin/env python3
"""High-coverage socio-demographic / economic complements for Italy energy analysis."""
from __future__ import annotations

import json
import shutil
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parents[1]
OUT = DB / "socio-italia" / "sources"
UA = {"User-Agent": "socio-italia/1.0"}


def log(msg: str) -> None:
    print(msg, flush=True)


def download(url: str, dest: Path, min_size: int = 200, timeout: int = 180) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= min_size:
        log(f"  skip {dest.name}")
        return True
    log(f"  GET {url[:150]}")
    req = urllib.request.Request(url, headers=UA)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as f:
            shutil.copyfileobj(resp, f)
        head = tmp.read_bytes()[:20].lower()
        if head.startswith(b"<!doctype") or head.startswith(b"<html"):
            tmp.unlink(missing_ok=True)
            log("  FAIL HTML")
            return False
        if tmp.stat().st_size < min_size:
            tmp.unlink(missing_ok=True)
            log(f"  FAIL small {tmp.stat().st_size if tmp.exists() else 0}")
            return False
        tmp.replace(dest)
        log(f"  -> {dest.name} ({dest.stat().st_size/1e6:.2f} MB)")
        return True
    except Exception as e:
        tmp.unlink(missing_ok=True)
        log(f"  FAIL: {e}")
        return False


def eurostat_filter_italy(src: Path, dest: Path) -> None:
    df = pd.read_csv(src, low_memory=False)
    # Eurostat SDMX-CSV usually has geo column
    geo_col = None
    for c in df.columns:
        if c.lower() in ("geo", "geo\\time", "geography"):
            geo_col = c
            break
        if "geo" in c.lower():
            geo_col = c
            break
    if geo_col is None:
        dest.write_bytes(src.read_bytes())
        return
    it = df[df[geo_col].astype(str).isin(["IT", "ITA", "Italy"])].copy()
    if it.empty:
        it = df[df[geo_col].astype(str).str.startswith("IT")].copy()
    it.to_csv(dest, index=False)
    log(f"  Italy filter {dest.name} rows={len(it)}")


def harvest_eurostat_demo() -> None:
    log("== Eurostat population / demo / economy ==")
    out = OUT / "eurostat"
    out.mkdir(parents=True, exist_ok=True)
    # SDMX 2.1 CSV compressed or plain
    codes = [
        ("demo_pjan", "population_1jan"),  # population on 1 January
        ("demo_r_pjangroup", "population_nuts_age"),  # regional
        ("demo_r_d3dens", "population_density_nuts3"),
        ("nama_10_gdp", "gdp"),
        ("nama_10_pc", "gdp_per_capita"),
        ("lfsi_emp_a", "employment"),
        ("ilc_lvho05a", "avg_household_size"),
        ("urb_lpop1", "urban_population"),
        ("tgs00096", "population_nuts2"),  # may 404
        ("demo_gind", "population_change"),
        ("cens_11ag_r2", "census_age_region"),  # may be heavy/404
    ]
    base = "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{code}?format=SDMX-CSV&compressed=false"
    for code, slug in codes:
        dest = out / f"{code}_raw.csv"
        url = base.format(code=code)
        if download(url, dest, min_size=300, timeout=300):
            try:
                eurostat_filter_italy(dest, out / f"{slug}_italy.csv")
            except Exception as e:
                log(f"  filter fail {code}: {e}")


def harvest_worldbank_pop() -> None:
    log("== World Bank population / socio ==")
    out = OUT / "worldbank"
    out.mkdir(parents=True, exist_ok=True)
    indicators = [
        ("SP.POP.TOTL", "population_total"),
        ("SP.POP.GROW", "population_growth"),
        ("SP.URB.TOTL.IN.ZS", "urban_population_pct"),
        ("EN.POP.DNST", "population_density"),
        ("NY.GDP.MKTP.CD", "gdp_current_usd"),
        ("NY.GDP.PCAP.CD", "gdp_per_capita_usd"),
        ("NY.GDP.MKTP.KD.ZG", "gdp_growth"),
        ("SL.TLF.TOTL.IN", "labor_force"),
        ("SL.UEM.TOTL.ZS", "unemployment"),
        ("SP.DYN.LE00.IN", "life_expectancy"),
        ("AG.LND.TOTL.K2", "land_area_km2"),
        ("EG.USE.ELEC.KH.PC", "electric_power_consumption_pc"),
    ]
    rows = []
    for code, slug in indicators:
        url = f"https://api.worldbank.org/v2/country/IT/indicator/{code}?format=json&per_page=30000"
        dest = out / f"{code}.json"
        if not download(url, dest, min_size=50, timeout=120):
            continue
        try:
            payload = json.loads(dest.read_text(encoding="utf-8"))
            data = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
            for item in data or []:
                rows.append(
                    {
                        "indicator": code,
                        "slug": slug,
                        "year": item.get("date"),
                        "value": item.get("value"),
                        "country": (item.get("country") or {}).get("id"),
                    }
                )
            # also flat csv per indicator
            pdf = pd.DataFrame(
                [{"year": i.get("date"), "value": i.get("value")} for i in (data or [])]
            )
            pdf.to_csv(out / f"{slug}.csv", index=False)
        except Exception as e:
            log(f"  parse {code}: {e}")
    if rows:
        pd.DataFrame(rows).to_csv(out / "italy_socio_indicators_long.csv", index=False)
        log(f"  long rows={len(rows)}")


def harvest_istat() -> None:
    log("== ISTAT popolazione / comuni ==")
    out = OUT / "istat"
    out.mkdir(parents=True, exist_ok=True)
    # reuse / refresh comuni list
    for url, name in [
        (
            "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.xls",
            "Elenco-comuni-italiani.xls",
        ),
        (
            "https://www.istat.it/storage/datainformativi/comuni/Elenco-comuni-italiani.xls",
            "Elenco-comuni-italiani_alt.xls",
        ),
    ]:
        download(url, out / name, min_size=10_000)

    # SDMX population datasets (best-effort codes)
    sdmx = [
        (
            "https://sdmx.istat.it/SDMXWS/rest/data/22_289/?format=csv&detail=dataonly",
            "istat_22_289_pop.csv",
        ),
        (
            "https://sdmx.istat.it/SDMXWS/rest/data/DCIS_POPRES1/?format=csv&detail=dataonly",
            "istat_DCIS_POPRES1.csv",
        ),
        (
            "https://sdmx.istat.it/SDMXWS/rest/data/DCIS_POPORESBIL1/?format=csv&detail=dataonly",
            "istat_pop_bilancio.csv",
        ),
    ]
    for url, name in sdmx:
        download(url, out / name, min_size=100, timeout=300)

    # Copy geojson from consumi if present
    geo = DB / "consumi-italia" / "sources" / "istat" / "limits_IT_municipalities.geojson"
    if geo.exists():
        dest = out / "limits_IT_municipalities.geojson"
        if not dest.exists():
            try:
                dest.symlink_to(geo)
            except OSError:
                shutil.copy2(geo, dest)
            log("  linked municipalities geojson")


def harvest_owid_pop() -> None:
    log("== OWID population ==")
    out = OUT / "owid"
    out.mkdir(parents=True, exist_ok=True)
    url = "https://catalog.ourworldindata.org/garden/demography/2024-07-15/population/population.csv"
    # fallback classic
    alts = [
        url,
        "https://raw.githubusercontent.com/owid/owid-datasets/master/datasets/Population%20(Gapminder%2C%20HYDE%20%26%20UN)/Population%20(Gapminder%2C%20HYDE%20%26%20UN).csv",
        "https://covid.ourworldindata.org/data/owid-covid-data.csv",
    ]
    for u in alts[:2]:
        dest = out / "population_raw.csv"
        if download(u, dest, min_size=1000):
            try:
                df = pd.read_csv(dest, low_memory=False)
                cols = {c.lower(): c for c in df.columns}
                entity = cols.get("entity") or cols.get("country") or cols.get("location")
                if entity:
                    it = df[df[entity].astype(str).isin(["Italy", "Italia"])].copy()
                    it.to_csv(out / "population_italy.csv", index=False)
                    log(f"  OWID Italy rows={len(it)}")
            except Exception as e:
                log(f"  OWID filter: {e}")
            break


def write_readme() -> None:
    root = DB / "socio-italia"
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text(
        "# Socio-Italia\n\n"
        "Popolazione, densità, PIL, lavoro — driver di domanda elettrica.\n\n"
        "## Refresh\n\n```powershell\n"
        "python db/scripts/harvest_socio_italia.py\n```\n\n"
        "## Sorgenti\n\n"
        "- `sources/eurostat/` — demo_pjan, densità NUTS, GDP, employment\n"
        "- `sources/worldbank/` — SP.POP.*, GDP, unemployment, land area\n"
        "- `sources/istat/` — comuni + SDMX popolazione (se API risponde)\n"
        "- `sources/owid/` — population Italy\n",
        encoding="utf-8",
    )
    (root / "METADATI.txt").write_text(
        "METADATI — socio-italia\nLicenze: Eurostat, World Bank, ISTAT, OWID open terms.\n",
        encoding="utf-8",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    harvest_worldbank_pop()
    harvest_eurostat_demo()
    harvest_istat()
    harvest_owid_pop()
    write_readme()
    log("DONE socio-italia")


if __name__ == "__main__":
    main()
