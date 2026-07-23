#!/usr/bin/env python3
"""Harvest complementary Italy plant / GHG datasets (Wikidata, WRI GPPD, PowerAtlas, EEA)."""
from __future__ import annotations

import csv
import io
import json
import re
import shutil
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parents[1]
OUT = DB / "impianti-italia" / "sources"
UA = {"User-Agent": "impianti-italia/1.0 (research; local harvest)"}


def log(msg: str) -> None:
    print(msg, flush=True)


def get(url: str, timeout: int = 180) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def download(url: str, dest: Path, min_size: int = 500) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= min_size:
        log(f"  skip {dest.name} ({dest.stat().st_size/1e6:.2f} MB)")
        return True
    log(f"  GET {url[:160]}")
    try:
        data = get(url, timeout=300)
        if len(data) < min_size:
            log(f"  FAIL small {len(data)}")
            return False
        if data[:15].lower().startswith(b"<!doctype") or data[:6].lower().startswith(b"<html"):
            log("  FAIL HTML")
            return False
        dest.write_bytes(data)
        log(f"  -> {dest.name} ({dest.stat().st_size/1e6:.2f} MB)")
        return True
    except Exception as e:
        log(f"  FAIL: {e}")
        return False


def harvest_wikidata() -> None:
    log("== Wikidata power plants / generators IT ==")
    out = OUT / "wikidata"
    out.mkdir(parents=True, exist_ok=True)
    # Power stations in Italy (or located in IT) with coords + capacity when present
    query = """
SELECT ?item ?itemLabel ?coord ?capacity ?fuelLabel ?operatorLabel ?commissioning
       ?wikipedia WHERE {
  ?item wdt:P31/wdt:P279* wd:Q159719 .
  ?item wdt:P17 wd:Q38 .
  OPTIONAL { ?item wdt:P625 ?coord . }
  OPTIONAL { ?item wdt:P2109 ?capacity . }
  OPTIONAL { ?item wdt:P618 ?fuel . }
  OPTIONAL { ?item wdt:P137 ?operator . }
  OPTIONAL { ?item wdt:P571 ?commissioning . }
  OPTIONAL {
    ?wikipedia schema:about ?item ;
               schema:isPartOf <https://it.wikipedia.org/> .
  }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "it,en". }
}
"""
    url = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode(
        {"query": query, "format": "json"}
    )
    try:
        raw = get(url, timeout=180)
        (out / "wikidata_power_stations_it.json").write_bytes(raw)
        payload = json.loads(raw.decode("utf-8"))
        rows = []
        for b in payload.get("results", {}).get("bindings", []):
            def val(k: str):
                return b.get(k, {}).get("value")

            coord = val("coord")
            lat = lon = None
            if coord and coord.startswith("Point("):
                # Point(lon lat)
                m = re.match(r"Point\(([-\d.]+)\s+([-\d.]+)\)", coord)
                if m:
                    lon, lat = float(m.group(1)), float(m.group(2))
            rows.append(
                {
                    "qid": (val("item") or "").rsplit("/", 1)[-1],
                    "name": val("itemLabel"),
                    "lat": lat,
                    "lon": lon,
                    "capacity_mw": val("capacity"),
                    "fuel": val("fuelLabel"),
                    "operator": val("operatorLabel"),
                    "commissioning": val("commissioning"),
                    "wikipedia_it": val("wikipedia"),
                }
            )
        df = pd.DataFrame(rows).drop_duplicates(subset=["qid"])
        dest = out / "wikidata_power_stations_it.csv"
        df.to_csv(dest, index=False)
        log(f"  wrote {dest.name} rows={len(df)}")
    except Exception as e:
        log(f"  Wikidata FAIL: {e}")

    # Also generators (Q2516117) / wind farms / solar farms
    query2 = """
SELECT ?item ?itemLabel ?coord ?capacity ?typeLabel WHERE {
  VALUES ?type { wd:Q159719 wd:Q2516117 wd:Q194356 wd:Q217593 }
  ?item wdt:P31/wdt:P279* ?type .
  ?item wdt:P17 wd:Q38 .
  OPTIONAL { ?item wdt:P625 ?coord . }
  OPTIONAL { ?item wdt:P2109 ?capacity . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "it,en". }
}
"""
    url2 = "https://query.wikidata.org/sparql?" + urllib.parse.urlencode(
        {"query": query2, "format": "json"}
    )
    try:
        raw = get(url2, timeout=180)
        (out / "wikidata_power_assets_it.json").write_bytes(raw)
        payload = json.loads(raw.decode("utf-8"))
        rows = []
        for b in payload.get("results", {}).get("bindings", []):
            def val(k: str):
                return b.get(k, {}).get("value")

            coord = val("coord")
            lat = lon = None
            if coord and "Point(" in coord:
                m = re.search(r"Point\(([-\d.]+)\s+([-\d.]+)\)", coord)
                if m:
                    lon, lat = float(m.group(1)), float(m.group(2))
            rows.append(
                {
                    "qid": (val("item") or "").rsplit("/", 1)[-1],
                    "name": val("itemLabel"),
                    "type": val("typeLabel"),
                    "lat": lat,
                    "lon": lon,
                    "capacity_mw": val("capacity"),
                }
            )
        df = pd.DataFrame(rows).drop_duplicates(subset=["qid"])
        dest = out / "wikidata_power_assets_it.csv"
        df.to_csv(dest, index=False)
        log(f"  wrote {dest.name} rows={len(df)}")
    except Exception as e:
        log(f"  Wikidata assets FAIL: {e}")


def harvest_wri_gppd() -> None:
    log("== WRI Global Power Plant Database (Italy filter) ==")
    out = OUT / "wri_gppd"
    out.mkdir(parents=True, exist_ok=True)
    urls = [
        "https://raw.githubusercontent.com/wri/global-power-plant-database/master/output_database/global_power_plant_database.csv",
        "https://github.com/wri/global-power-plant-database/raw/master/output_database/global_power_plant_database.csv",
    ]
    raw = out / "global_power_plant_database.csv"
    ok = False
    for url in urls:
        if download(url, raw, min_size=100_000):
            ok = True
            break
    if not ok:
        return
    df = pd.read_csv(raw, low_memory=False)
    it = df[df["country_long"].astype(str).str.fullmatch("Italy", case=False)].copy()
    if it.empty and "country" in df.columns:
        it = df[df["country"].astype(str).str.upper().eq("ITA")].copy()
    dest = out / "italy_power_plants.csv"
    it.to_csv(dest, index=False)
    log(f"  wrote {dest.name} rows={len(it)}")


def harvest_poweratlas() -> None:
    log("== PowerAtlas Italy plants ==")
    out = OUT / "poweratlas"
    out.mkdir(parents=True, exist_ok=True)
    download(
        "https://inzonex.co.uk/poweratlas/italy/plants.csv",
        out / "italy_plants.csv",
        min_size=1000,
    )


def harvest_gem_github() -> None:
    log("== GEM Integrated Power (GitHub snapshot if available) ==")
    out = OUT / "gem"
    out.mkdir(parents=True, exist_ok=True)
    # Public mirrors / known release names (best-effort)
    candidates = [
        "https://github.com/myougotti/gem_per_country/raw/main/Global-Integrated-Power-February-2025-update-II.xlsx",
        "https://raw.githubusercontent.com/myougotti/gem_per_country/main/Global-Integrated-Power-February-2025-update-II.xlsx",
    ]
    dest = out / "Global-Integrated-Power.xlsx"
    for url in candidates:
        if download(url, dest, min_size=100_000):
            try:
                xl = pd.ExcelFile(dest)
                # find sheet with Country column
                for sheet in xl.sheet_names:
                    df = pd.read_excel(dest, sheet_name=sheet)
                    cols = {c.lower(): c for c in df.columns.astype(str)}
                    ccol = cols.get("country/area") or cols.get("country") or cols.get("country/area ")
                    if not ccol:
                        continue
                    it = df[df[ccol].astype(str).str.contains("Italy", case=False, na=False)].copy()
                    if len(it) == 0:
                        continue
                    safe = re.sub(r"[^\w]+", "_", sheet)[:40]
                    it_path = out / f"gem_italy_{safe}.csv"
                    it.to_csv(it_path, index=False)
                    log(f"  wrote {it_path.name} rows={len(it)} sheet={sheet}")
            except Exception as e:
                log(f"  GEM parse warn: {e}")
            return
    log("  GEM xlsx not reachable — leave marker")
    (out / "GEM_DOWNLOAD_MANUAL.txt").write_text(
        "Download from https://globalenergymonitor.org/download-data (GIPT)\n"
        "Then place xlsx here and re-run filter.\n",
        encoding="utf-8",
    )


def harvest_eea_ghg() -> None:
    log("== EEA / UNFCCC GHG (best-effort) ==")
    out = DB / "consumi-italia" / "sources" / "ghg" / "eea"
    out.mkdir(parents=True, exist_ok=True)
    # EEA datahub CSV exports change; try Climate Watch + Our World in Data Italy already elsewhere
    urls = [
        (
            "https://www.eea.europa.eu/data-and-maps/data/national-emissions-reported-to-the-unfccc-and-to-the-eu-greenhouse-gas-monitoring-mechanism-21/"
            "national-greenhouse-gas-inventories-ipcc-common-reporting-format-sector-classification/"
            "greenhouse-gas-emissions-under-the-unfccc.csv/at_download/file",
            "eea_unfccc_ghg.csv",
        ),
    ]
    for url, name in urls:
        download(url, out / name, min_size=500)

    # Climate Watch historical emissions Italy JSON/CSV API
    cw = (
        "https://www.climatewatchdata.org/api/v1/data/historical_emissions?"
        "regions[]=ITA&page=1&per_page=2000"
    )
    try:
        raw = get(cw, timeout=120)
        (out / "climatewatch_ita.json").write_bytes(raw)
        payload = json.loads(raw.decode("utf-8"))
        data = payload.get("data") or payload
        if isinstance(data, list) and data:
            # flatten emissions
            rows = []
            for item in data:
                em = item.get("emissions") or []
                for e in em:
                    rows.append(
                        {
                            "source": item.get("source"),
                            "sector": item.get("sector"),
                            "gas": item.get("gas"),
                            "year": e.get("year"),
                            "value": e.get("value"),
                        }
                    )
            if rows:
                pd.DataFrame(rows).to_csv(out / "climatewatch_ita_flat.csv", index=False)
                log(f"  climatewatch rows={len(rows)}")
    except Exception as e:
        log(f"  climatewatch FAIL: {e}")


def harvest_osm_power_overpass() -> None:
    log("== OSM Overpass power=plant IT bbox ==")
    out = OUT / "osm"
    out.mkdir(parents=True, exist_ok=True)
    # Italy approximate bbox
    query = """
[out:json][timeout:180];
area["ISO3166-1"="IT"][admin_level=2]->.it;
(
  node["power"="plant"](area.it);
  way["power"="plant"](area.it);
  relation["power"="plant"](area.it);
  node["power"="generator"](area.it);
  way["power"="generator"](area.it);
);
out center tags;
"""
    url = "https://overpass-api.de/api/interpreter"
    dest = out / "osm_power_plants_generators_it.json"
    if dest.exists() and dest.stat().st_size > 10_000:
        log(f"  skip {dest.name}")
        return
    try:
        req = urllib.request.Request(
            url,
            data=query.encode("utf-8"),
            headers={**UA, "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=300) as resp:
            data = resp.read()
        dest.write_bytes(data)
        payload = json.loads(data.decode("utf-8"))
        els = payload.get("elements") or []
        rows = []
        for el in els:
            tags = el.get("tags") or {}
            lat = el.get("lat") or (el.get("center") or {}).get("lat")
            lon = el.get("lon") or (el.get("center") or {}).get("lon")
            rows.append(
                {
                    "osm_type": el.get("type"),
                    "osm_id": el.get("id"),
                    "name": tags.get("name"),
                    "power": tags.get("power"),
                    "plant_source": tags.get("plant:source") or tags.get("generator:source"),
                    "plant_method": tags.get("plant:method") or tags.get("generator:method"),
                    "output_mw": tags.get("plant:output:electricity")
                    or tags.get("generator:output:electricity"),
                    "lat": lat,
                    "lon": lon,
                }
            )
        pd.DataFrame(rows).to_csv(out / "osm_power_plants_generators_it.csv", index=False)
        log(f"  OSM elements={len(rows)}")
    except Exception as e:
        log(f"  OSM FAIL: {e}")


def write_readme() -> None:
    root = DB / "impianti-italia"
    root.mkdir(parents=True, exist_ok=True)
    (root / "README.md").write_text(
        "# Impianti Italia\n\n"
        "Anagrafica impianti / centrali da fonti complementari a OIM e GSE.\n\n"
        "## Refresh\n\n```powershell\n"
        "python db/scripts/harvest_impianti_complementari.py\n```\n\n"
        "## Sorgenti\n\n"
        "- `sources/wikidata/` — SPARQL centrali e asset power IT\n"
        "- `sources/wri_gppd/` — WRI Global Power Plant Database (filter Italy)\n"
        "- `sources/poweratlas/` — PowerAtlas Italy CSV\n"
        "- `sources/gem/` — Global Energy Monitor (se scaricabile)\n"
        "- `sources/osm/` — Overpass power=plant/generator\n",
        encoding="utf-8",
    )
    (root / "METADATI.txt").write_text(
        "METADATI — impianti-italia\n"
        "Aggiornato: auto\n"
        "Licenze: Wikidata CC0; WRI GPPD CC-BY; OSM ODbL; GEM CC-BY 4.0 se presente.\n",
        encoding="utf-8",
    )


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    harvest_wikidata()
    time.sleep(1)
    harvest_wri_gppd()
    harvest_poweratlas()
    harvest_gem_github()
    harvest_eea_ghg()
    harvest_osm_power_overpass()
    write_readme()
    log("DONE impianti complementari")


if __name__ == "__main__":
    main()
