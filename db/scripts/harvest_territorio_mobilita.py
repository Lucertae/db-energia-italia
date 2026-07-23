#!/usr/bin/env python3
"""PIL/VA settoriale, uso suolo, mobilità, povertà OWID, griglia meteo nazionale (daily)."""
from __future__ import annotations

import json
import re
import shutil
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "territorio-mobilita-italia/1.0"}
ESTAT_JSON = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/{code}"
ESTAT_CSV = (
    "https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{code}"
    "?format=SDMX-CSV&compressed=false"
)


def log(msg: str) -> None:
    print(msg, flush=True)


def download(url: str, dest: Path, min_size: int = 200, timeout: int = 300) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= min_size:
        log(f"  skip {dest.name}")
        return True
    log(f"  GET {url[:160]}")
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
            log("  FAIL small")
            return False
        tmp.replace(dest)
        log(f"  -> {dest.name} ({dest.stat().st_size/1e6:.2f} MB)")
        return True
    except Exception as e:
        tmp.unlink(missing_ok=True)
        log(f"  FAIL: {e}")
        return False


def estat_json_to_df(code: str, extra: dict | None = None) -> pd.DataFrame:
    """Download Eurostat JSON filtered to Italy (geo=IT + IT* where useful)."""
    params = {"format": "JSON", "lang": "en", "geo": "IT"}
    if extra:
        params.update(extra)
    url = ESTAT_JSON.format(code=code) + "?" + urllib.parse.urlencode(params)
    log(f"  JSON {code} {params}")
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    value = payload.get("value") or {}
    if not value:
        # try without geo filter restriction (NUTS series use IT*)
        params.pop("geo", None)
        url = ESTAT_JSON.format(code=code) + "?" + urllib.parse.urlencode(params)
        log(f"  JSON retry no-geo {code}")
        with urllib.request.urlopen(req := urllib.request.Request(url, headers=UA), timeout=300) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        value = payload.get("value") or {}

    dims = payload["dimension"]
    ids = payload["id"]
    sizes = payload["size"]
    # build index -> label maps
    maps = {}
    for dim in ids:
        cat = dims[dim]["category"]
        index = cat.get("index", {})
        labels = cat.get("label", {})
        # index may be {code: pos} or list
        if isinstance(index, dict):
            pos_to_code = {int(v): k for k, v in index.items()}
        else:
            pos_to_code = {i: str(v) for i, v in enumerate(index)}
        maps[dim] = {pos: (code_k, labels.get(code_k, code_k)) for pos, code_k in pos_to_code.items()}

    rows = []
    for flat_idx, obs in value.items():
        idx = int(flat_idx)
        coords = {}
        rem = idx
        # row-major from last dim
        for dim, size in zip(reversed(ids), reversed(sizes)):
            pos = rem % size
            rem //= size
            code_k, label = maps[dim][pos]
            coords[dim] = code_k
            coords[f"{dim}_label"] = label
        coords["OBS_VALUE"] = obs
        rows.append(coords)
    df = pd.DataFrame(rows)
    if "geo" in df.columns:
        s = df["geo"].astype(str)
        df = df[s.eq("IT") | s.str.startswith("IT")].copy()
    return df


def save_estat(code: str, slug: str, out: Path, extra: dict | None = None) -> int:
    dest = out / f"{slug}_italy.csv"
    raw = out / f"{code}_italy.json"
    if dest.exists() and dest.stat().st_size > 500:
        log(f"  skip {dest.name}")
        return sum(1 for _ in open(dest, encoding="utf-8", errors="replace")) - 1
    try:
        df = estat_json_to_df(code, extra)
        if df.empty:
            log(f"  empty {code}")
            return 0
        raw.write_text(json.dumps({"n": len(df), "cols": list(df.columns)}, indent=2), encoding="utf-8")
        df.to_csv(dest, index=False)
        log(f"  -> {dest.name} rows={len(df)}")
        return len(df)
    except Exception as e:
        log(f"  FAIL {code}: {e}")
        # fallback SDMX CSV full then filter (small datasets only)
        return 0


def filter_italy_csv(src: Path, dest: Path) -> int:
    df = pd.read_csv(src, low_memory=False)
    geo = next((c for c in df.columns if c.lower() == "geo"), None)
    if geo is None:
        shutil.copy2(src, dest)
        return len(df)
    s = df[geo].astype(str)
    it = df[s.eq("IT") | s.str.startswith("IT")].copy()
    it.to_csv(dest, index=False)
    log(f"  Italy {dest.name} rows={len(it)}")
    return len(it)


def harvest_eurostat_gva() -> None:
    log("== Eurostat PIL / VA settoriale ==")
    out = DB / "socio-italia" / "sources" / "eurostat_gva"
    out.mkdir(parents=True, exist_ok=True)
    mirror = DB / "consumi-italia" / "sources" / "eurostat"
    mirror.mkdir(parents=True, exist_ok=True)

    # Drop huge unfiltered raw if present (>200MB)
    huge = out / "nama_10_a64_raw.csv"
    if huge.exists() and huge.stat().st_size > 200_000_000:
        log(f"  remove oversized {huge.name} ({huge.stat().st_size/1e6:.0f} MB)")
        huge.unlink(missing_ok=True)
    part = out / "nama_10_a64_raw.csv.part"
    part.unlink(missing_ok=True)

    series = [
        ("nama_10_a64", "gva_by_nace_a64"),
        ("nama_10_a10", "gva_by_nace_a10"),
        ("nama_10_a10_e", "employment_by_nace_a10"),
        ("nama_10_a64_e", "employment_by_nace_a64"),
        ("nama_10_gdp", "gdp_national"),
        ("nama_10r_2gdp", "gdp_nuts2"),
        ("nama_10r_3gdp", "gdp_nuts3"),
        ("nama_10r_3gva", "gva_nuts3"),
        ("nama_10r_2gvagr", "gva_growth_nuts2"),
        ("nama_10r_2hhinc", "hh_income_nuts2"),
        ("nama_10r_3popgdp", "gdp_per_capita_nuts3"),
        ("nama_10_pc", "gdp_per_capita_national"),
    ]
    for code, slug in series:
        n = save_estat(code, slug, out)
        dest = out / f"{slug}_italy.csv"
        if n and code in ("nama_10_a64", "nama_10_a10", "nama_10r_3gva", "nama_10_gdp"):
            shutil.copy2(dest, mirror / f"{code}_italy.csv")
            log(f"  mirrored {code}_italy.csv -> consumi-italia/eurostat")

    # If existing consumi extract is good, keep as backup reference
    legacy = mirror / "nama_10_a64_italy.csv"
    if legacy.exists():
        log(f"  legacy consumi nama_10_a64_italy.csv size={legacy.stat().st_size/1e6:.2f} MB")


def harvest_land_use() -> None:
    log("== Uso suolo / superfici ==")
    out = DB / "socio-italia" / "sources" / "land_use"
    out.mkdir(parents=True, exist_ok=True)

    for code, slug in [
        ("lan_lcv_ovw", "land_cover_overview"),
        ("lan_lcv_art", "land_cover_artificial"),
        ("agr_r_landuse", "agricultural_land_use"),
        ("reg_area3", "nuts3_area"),
        ("demo_r_d3area", "nuts3_area_demo"),
    ]:
        # SDMX with geo query works for lan_*; JSON for regional
        raw = out / f"{code}_raw.csv"
        url = ESTAT_CSV.format(code=code)
        # Prefer filtered CSV via statistics JSON
        n = save_estat(code, slug, out)
        if n == 0 and download(url, raw, min_size=300, timeout=400):
            try:
                filter_italy_csv(raw, out / f"{slug}_italy.csv")
            except Exception as e:
                log(f"  filter {code}: {e}")

    # ISTAT administrative boundaries (land surface geometry)
    for url in [
        "https://www.istat.it/storage/cartografia/confini_amministrativi/generalizzati/2025/Limiti01012025_g.zip",
        "https://www.istat.it/storage/cartografia/confini_amministrativi/generalizzati/2024/Limiti01012024_g.zip",
        "https://www.istat.it/storage/cartografia/confini_amministrativi/non_generalizzati/2024/Limiti01012024.zip",
        "https://raw.githubusercontent.com/openpolis/geojson-italy/master/geojson/limits_IT_regions.geojson",
        "https://raw.githubusercontent.com/openpolis/geojson-italy/master/geojson/limits_IT_provinces.geojson",
    ]:
        name = url.rstrip("/").split("/")[-1]
        dest_name = f"istat_{name}" if name.startswith("Limiti") else name
        download(url, out / dest_name, min_size=50_000, timeout=600)

    # EEA Corine country fact sheet / land accounting — probe downloadable assets
    pages = [
        "https://www.eea.europa.eu/en/analysis/maps-and-charts/copy_of_land-cover-country-fact-sheets-2000-2018-land-cover-country-fact-sheets",
        "https://www.eea.europa.eu/en/datahub/datahubitem-view/a5b950b0-8e3d-4f0c-9f5a-9a9f0e0e0e0e",
        "https://land.copernicus.eu/en/products/corine-land-cover",
    ]
    found: list[str] = []
    for page in pages:
        try:
            req = urllib.request.Request(page, headers=UA)
            html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
            for m in re.findall(r'href=["\']([^"\']+\.(?:xlsx?|csv|zip|json))["\']', html, re.I):
                found.append(urllib.parse.urljoin(page, m))
        except Exception as e:
            log(f"  page {page[:60]}: {e}")
    # Known EEA land cover accounting / CLC change tables (best-effort)
    known = [
        "https://www.eea.europa.eu/data-and-maps/data/corine-land-cover-accounting-layers/corine-land-cover-accounting-layers/clc-accounting-layers.zip/at_download/file",
        "https://sdi.eea.europa.eu/datashare/s/CLC_ACCOUNTING/download",
    ]
    for url in known + sorted(set(found))[:25]:
        name = urllib.parse.unquote(url.rstrip("/").split("/")[-1])
        name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)[:120] or "file.bin"
        if not name.lower().endswith((".csv", ".xlsx", ".xls", ".zip", ".json")):
            name += ".bin"
        download(url, out / "corine_eea" / name, min_size=800, timeout=300)

    # World Bank land indicators Italy
    for code, slug in [
        ("AG.LND.AGRI.ZS", "ag_land_pct"),
        ("AG.LND.FRST.ZS", "forest_land_pct"),
        ("AG.LND.TOTL.K2", "land_area_km2"),
        ("AG.LND.ARBL.ZS", "arable_land_pct"),
        ("AG.LND.CROP.ZS", "permanent_crops_pct"),
    ]:
        url = f"https://api.worldbank.org/v2/country/IT/indicator/{code}?format=json&per_page=30000"
        dest = out / f"wb_{code}.json"
        if download(url, dest, min_size=50):
            try:
                payload = json.loads(dest.read_text(encoding="utf-8"))
                data = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
                pd.DataFrame(
                    [{"year": i.get("date"), "value": i.get("value")} for i in (data or [])]
                ).to_csv(out / f"{slug}.csv", index=False)
            except Exception as e:
                log(f"  wb parse {code}: {e}")

    (out / "README.txt").write_text(
        "Land use / surfaces for Italy.\n"
        "- Eurostat lan_* + agr_r_landuse + NUTS area\n"
        "- ISTAT confini amministrativi (zip)\n"
        "- World Bank land %\n"
        "- Corine/CLC: raster/vector full Europe needs Copernicus CLMS login; "
        "here we keep Eurostat LCV accounting + any EEA attachments found.\n"
        "Manual CLC2018 Italy: https://land.copernicus.eu/en/products/corine-land-cover/clc2018\n",
        encoding="utf-8",
    )


def harvest_mobility() -> None:
    log("== Traffico / mobilità ==")
    out = DB / "socio-italia" / "sources" / "mobility"
    out.mkdir(parents=True, exist_ok=True)

    for code, slug in [
        ("road_eqs_carhab", "cars_per_1000"),
        ("road_eqs_lorlor", "lorries"),
        ("road_tf_vehmov", "vehicle_movements"),
        ("road_go_ta_tott", "road_freight"),
        ("tran_r_vehst", "vehicles_stock_nuts"),
        ("rail_pa_total", "rail_passengers_total"),
        ("avia_paoc", "air_passengers"),
    ]:
        n = save_estat(code, slug, out)
        if n == 0:
            raw = out / f"{code}_raw.csv"
            if download(ESTAT_CSV.format(code=code), raw, min_size=200, timeout=400):
                try:
                    filter_italy_csv(raw, out / f"{slug}_italy.csv")
                except Exception as e:
                    log(f"  filter {code}: {e}")

    # ISPRA trasporti indicator pages
    ispra_pages = [
        "https://indicatoriambientali.isprambiente.it/it/trasporti",
        "https://www.isprambiente.gov.it/it/attivita/biodiversita/il-contributo-italiano-alla-gestione-della-biodiversita/strumenti-e-dati/uso-del-suolo",
    ]
    found: list[str] = []
    for page in ispra_pages:
        try:
            req = urllib.request.Request(page, headers=UA)
            html = urllib.request.urlopen(req, timeout=90).read().decode("utf-8", "replace")
            for m in re.findall(r'href=["\']([^"\']+\.(?:xlsx?|csv|zip))["\']', html, re.I):
                found.append(urllib.parse.urljoin(page, m))
        except Exception as e:
            log(f"  ispra page: {e}")
    for url in sorted(set(found))[:40]:
        name = urllib.parse.unquote(url.rstrip("/").split("/")[-1])
        name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)[:140]
        download(url, out / "ispra" / name, min_size=500)

    # OpenStreetMap transport skeleton (motorway/trunk length proxy via count)
    query = """
[out:json][timeout:120];
area["ISO3166-1"="IT"][admin_level=2]->.it;
(
  way["highway"="motorway"](area.it);
  way["highway"="trunk"](area.it);
);
out count;
"""
    try:
        req = urllib.request.Request(
            "https://overpass-api.de/api/interpreter",
            data=urllib.parse.urlencode({"data": query}).encode("utf-8"),
            headers={**UA, "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = resp.read()
        (out / "osm_motorway_trunk_count.json").write_bytes(data)
        log("  OSM motorway/trunk count saved")
    except Exception as e:
        log(f"  OSM mobility FAIL: {e}")

    (out / "README.txt").write_text(
        "Mobility / traffic proxies for urban load.\n"
        "- Eurostat road/rail/air series (Italy filter)\n"
        "- ISPRA attachments from indicator pages (if any)\n"
        "- OSM Overpass motorway/trunk element counts\n"
        "OpenTransportMap / TomTom-style live flows need separate API keys.\n",
        encoding="utf-8",
    )


def harvest_owid_poverty() -> None:
    log("== OWID poverty / reddito ==")
    out = DB / "owid-italia" / "sources" / "poverty-data"
    out.mkdir(parents=True, exist_ok=True)
    socio = DB / "socio-italia" / "sources" / "poverty"
    socio.mkdir(parents=True, exist_ok=True)

    # Refresh Italy extract from existing pip if present
    existing = out / "italy_poverty.csv"
    if existing.exists() and existing.stat().st_size > 1000:
        shutil.copy2(existing, socio / "italy_poverty.csv")
        log(f"  copied existing italy_poverty.csv -> socio-italia ({existing.stat().st_size} B)")

    urls = [
        (
            "https://catalog.ourworldindata.org/garden/poverty-inequality/2025-04-10/pip_extended/pip_extended.csv",
            "pip_extended.csv",
        ),
        (
            "https://raw.githubusercontent.com/owid/poverty-data/main/datasets/pip_dataset.csv",
            "pip_dataset.csv",
        ),
    ]
    for url, name in urls:
        dest = out / name
        if download(url, dest, min_size=1000, timeout=300):
            try:
                df = pd.read_csv(dest, low_memory=False)
                cols = {c.lower(): c for c in df.columns}
                ent = cols.get("country") or cols.get("entity") or cols.get("location")
                if ent:
                    it = df[df[ent].astype(str).isin(["Italy", "Italia"])].copy()
                    it.to_csv(out / "italy_poverty.csv", index=False)
                    it.to_csv(socio / "italy_poverty.csv", index=False)
                    log(f"  Italy poverty rows={len(it)} from {name}")
                    break
            except Exception as e:
                log(f"  filter {name}: {e}")

    for code, slug in [
        ("SI.POV.DDAY", "poverty_215"),
        ("SI.POV.LMIC", "poverty_365"),
        ("SI.POV.UMIC", "poverty_685"),
        ("SI.POV.NAHC", "poverty_national"),
        ("SI.POV.GINI", "gini"),
        ("NY.GNP.PCAP.CD", "gni_pc"),
        ("SI.DST.10TH.10", "income_share_top10"),
        ("SI.DST.FRST.10", "income_share_bottom10"),
    ]:
        url = f"https://api.worldbank.org/v2/country/IT/indicator/{code}?format=json&per_page=30000"
        dest = socio / f"wb_{code}.json"
        if download(url, dest, min_size=40):
            try:
                payload = json.loads(dest.read_text(encoding="utf-8"))
                data = payload[1] if isinstance(payload, list) and len(payload) > 1 else []
                pd.DataFrame(
                    [{"year": i.get("date"), "value": i.get("value")} for i in (data or [])]
                ).to_csv(socio / f"{slug}.csv", index=False)
            except Exception as e:
                log(f"  wb {code}: {e}")


def harvest_meteo_grid() -> None:
    log("== Open-Meteo griglia nazionale (daily, sparse) ==")
    out = DB / "meteo-italia" / "sources" / "open_meteo_grid"
    out.mkdir(parents=True, exist_ok=True)

    # Probe rate limit with one tiny call
    probe = {
        "latitude": 41.9,
        "longitude": 12.5,
        "start_date": "2024-01-01",
        "end_date": "2024-01-03",
        "daily": "precipitation_sum",
        "timezone": "Europe/Rome",
    }
    probe_url = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(probe)
    try:
        req = urllib.request.Request(probe_url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as resp:
            json.loads(resp.read().decode())
        log("  Open-Meteo probe OK")
    except Exception as e:
        log(f"  Open-Meteo still limited ({e}) — skip grid this run")
        (out / "README.txt").write_text(
            f"Grid harvest skipped: {e}\nRetry: python db/scripts/harvest_territorio_mobilita.py\n",
            encoding="utf-8",
        )
        return

    points: list[tuple[float, float]] = []
    for lat in [36.5, 37.5, 38.5, 39.5, 40.5, 41.5, 42.5, 43.5, 44.5, 45.5, 46.5]:
        for lon in [7.0, 8.5, 10.0, 11.5, 13.0, 14.5, 16.0, 17.5]:
            if lat < 37 and lon < 12:
                continue
            if lat > 46 and lon > 14:
                continue
            points.append((round(lat, 2), round(lon, 2)))

    daily_vars = (
        "temperature_2m_mean,temperature_2m_max,temperature_2m_min,"
        "precipitation_sum,rain_sum,snowfall_sum,shortwave_radiation_sum,"
        "wind_speed_10m_max,weather_code"
    )
    end = (date.today() - timedelta(days=2)).isoformat()
    start = "2015-01-01"
    frames = []
    ok = 0
    for i, (lat, lon) in enumerate(points):
        dest = out / f"grid_{lat}_{lon}_daily.csv"
        if dest.exists() and dest.stat().st_size > 5000:
            try:
                frames.append(pd.read_csv(dest))
                ok += 1
                continue
            except Exception:
                pass
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": start,
            "end_date": end,
            "daily": daily_vars,
            "timezone": "Europe/Rome",
            "precipitation_unit": "mm",
        }
        url = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as resp:
                payload = json.loads(resp.read().decode())
            if "daily" not in payload:
                log(f"  no daily {lat},{lon}: {payload.get('reason')}")
                time.sleep(5)
                continue
            df = pd.DataFrame(payload["daily"])
            df.insert(0, "lat", lat)
            df.insert(1, "lon", lon)
            df.to_csv(dest, index=False)
            frames.append(df)
            ok += 1
            log(f"  grid {i+1}/{len(points)} {lat},{lon} rows={len(df)}")
            time.sleep(4.0)
        except Exception as e:
            log(f"  FAIL {lat},{lon}: {e}")
            if "429" in str(e):
                log("  rate-limit — stop grid for now")
                break
            time.sleep(10)

    if frames:
        all_df = pd.concat(frames, ignore_index=True)
        all_path = out / "italy_grid_daily_2015_present.csv"
        all_df.to_csv(all_path, index=False)
        log(f"  wrote {all_path.name} rows={len(all_df)} points={ok}")
    (out / "README.txt").write_text(
        f"Sparse ~1deg daily Open-Meteo grid over Italy.\npoints_ok={ok}/{len(points)}\n"
        f"period={start}..{end}\n",
        encoding="utf-8",
    )


def write_readme() -> None:
    root = DB / "socio-italia"
    readme = root / "README.md"
    extra = (
        "\n## Extra (PIL/suolo/mobilità/povertà)\n\n"
        "- `sources/eurostat_gva/` — VA/PIL settoriale e NUTS (API geo=IT)\n"
        "- `sources/land_use/` — land cover Eurostat + WB + confini ISTAT\n"
        "- `sources/mobility/` — veicoli/traffico Eurostat + ISPRA + OSM\n"
        "- `sources/poverty/` — OWID/WB poverty Italy\n"
        "- Griglia meteo: `../meteo-italia/sources/open_meteo_grid/`\n"
        "- Script: `../scripts/harvest_territorio_mobilita.py`\n"
    )
    if readme.exists():
        t = readme.read_text(encoding="utf-8")
        if "eurostat_gva" not in t:
            readme.write_text(t + extra, encoding="utf-8")
    else:
        readme.write_text("# Socio-Italia\n" + extra, encoding="utf-8")


def main() -> None:
    harvest_eurostat_gva()
    harvest_land_use()
    harvest_mobility()
    harvest_owid_poverty()
    harvest_meteo_grid()
    write_readme()
    log("DONE territorio / mobilita / poverta / grid")


if __name__ == "__main__":
    main()
