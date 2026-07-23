#!/usr/bin/env python3
"""Harvest priority missing Italy energy datasets (no paid keys)."""
from __future__ import annotations

import csv
import gzip
import io
import json
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from datetime import date, datetime
from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parents[1]
UA = {
    "User-Agent": "Mozilla/5.0 (compatible; harvest-priority-gaps/1.0; +local research)",
    "Accept": "*/*",
}
MANIFEST: list[dict] = []


def log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"), flush=True)


def download(url: str, dest: Path, *, force: bool = False, timeout: int = 600, min_size: int = 200) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= min_size and not force:
        log(f"  skip {dest.relative_to(DB)} ({dest.stat().st_size/1e6:.2f} MB)")
        MANIFEST.append({"url": url, "path": str(dest.relative_to(DB)), "status": "skip", "bytes": dest.stat().st_size})
        return dest
    log(f"  GET {url[:160]}")
    req = urllib.request.Request(url, headers=UA)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as f:
            shutil.copyfileobj(resp, f)
        # reject HTML error pages
        head = tmp.read_bytes()[:80].lower()
        if head.startswith(b"<!doctype") or head.startswith(b"<html"):
            tmp.unlink(missing_ok=True)
            raise RuntimeError("HTML instead of file")
        if tmp.stat().st_size < min_size:
            sz = tmp.stat().st_size
            tmp.unlink(missing_ok=True)
            raise RuntimeError(f"too small ({sz})")
        tmp.replace(dest)
        log(f"  -> {dest.relative_to(DB)} ({dest.stat().st_size/1e6:.2f} MB)")
        MANIFEST.append({"url": url, "path": str(dest.relative_to(DB)), "status": "ok", "bytes": dest.stat().st_size})
        return dest
    except Exception as e:
        tmp.unlink(missing_ok=True)
        log(f"  FAIL {dest.name}: {e}")
        MANIFEST.append({"url": url, "path": str(dest.relative_to(DB)), "status": f"fail:{e}"})
        raise


def try_download(url: str, dest: Path, **kw) -> bool:
    try:
        download(url, dest, **kw)
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 1) ARERA Portale Offerte — retail indices + PLACET / mercato libero
# ---------------------------------------------------------------------------
def harvest_portale_offerte() -> None:
    log("== Portale Offerte (ARERA) ==")
    out = DB / "consumi-italia" / "sources" / "arera" / "portale_offerte"
    out.mkdir(parents=True, exist_ok=True)
    base = "https://www.ilportaleofferte.it"
    # historical public indices (PUN, PSV, PE, CMEM, ...)
    try_download(
        f"{base}/portaleOfferte/resources/cms/documents/5d6f1085b4d5f20821af55764e647671.csv",
        out / "prezzi_storici_indici.csv",
        min_size=500,
    )
    # scrape open-data page for current + recent monthly dumps
    try:
        html = urllib.request.urlopen(
            urllib.request.Request(f"{base}/portaleOfferte/it/open-data.page", headers=UA),
            timeout=90,
        ).read().decode("utf-8", "replace")
        hrefs = sorted(set(re.findall(r'href="(/portaleOfferte/resources/opendata/[^"]+)"', html)))
        for href in hrefs:
            name = href.rstrip("/").split("/")[-1]
            try_download(base + href, out / name, min_size=200)
            time.sleep(0.2)
        # also pull last ~6 months of dated files by probing YYYY_M folders
        today = date.today()
        for back in range(0, 8):
            y = today.year
            m = today.month - back
            while m <= 0:
                m += 12
                y -= 1
            folder = f"{y}_{m}"
            day = f"{y}{m:02d}{today.day:02d}" if back == 0 else None
            candidates = [
                f"csv/offerte/{folder}/PO_Offerte_E_PLACET_",
                f"csv/offerte/{folder}/PO_Offerte_G_PLACET_",
                f"csv/parametri/{folder}/PO_Parametri_E_",
                f"csv/parametri/{folder}/PO_Parametri_G_",
                f"csv/parametriML/{folder}/PO_Parametri_Mercato_Libero_E_",
                f"csv/parametriML/{folder}/PO_Parametri_Mercato_Libero_G_",
            ]
            # if we already got today's from scrape, skip heavy probing
            if back == 0:
                continue
            # probe first day of month dumps (common pattern YYYYMMDD)
            for prefix in candidates:
                for d in (1, 15, 28):
                    stamp = f"{y}{m:02d}{d:02d}"
                    ext = ".csv" if "Offerte_E_MLIBERO" not in prefix and "Offerte_G_MLIBERO" not in prefix and "Offerte_D_MLIBERO" not in prefix else ".xml"
                    # PLACET/parametri are csv; ML offerte are xml
                    if "offerteML" in prefix:
                        continue
                    name = prefix.split("/")[-1] + stamp + (".csv" if "parametri" in prefix or "PLACET" in prefix else ".csv")
                    url = f"{base}/portaleOfferte/resources/opendata/{prefix}{stamp}.csv"
                    dest = out / f"{prefix.split('/')[-1]}{stamp}.csv"
                    if dest.exists():
                        continue
                    if try_download(url, dest, min_size=100, timeout=60):
                        break
                    time.sleep(0.15)
    except Exception as e:
        log(f"  open-data scrape: {e}")


# ---------------------------------------------------------------------------
# 2) Eurostat retail / oil / gas prices
# ---------------------------------------------------------------------------
def eurostat_italy(code: str, out_dir: Path) -> None:
    italy = out_dir / f"{code}_italy.csv"
    if italy.exists() and italy.stat().st_size > 200:
        log(f"  skip {italy.name}")
        return
    gz = DB / "consumi-italia" / "_tmp" / f"{code}.csv.gz"
    gz.parent.mkdir(parents=True, exist_ok=True)
    urls = [
        f"https://ec.europa.eu/eurostat/api/dissemination/sdmx/2.1/data/{code}/?format=SDMX-CSV&compressed=true",
        (
            "https://ec.europa.eu/eurostat/databrowser-backend/api/extraction/1.0/"
            f"LIVE/false/sdmx/csv/{code}?i&compressed=true"
        ),
    ]
    ok = False
    for url in urls:
        try:
            download(url, gz, force=True, min_size=200)
            ok = True
            break
        except Exception as e:
            log(f"  {code} url fail: {e}")
    if not ok:
        return
    kept = 0
    opener = gzip.open if gz.read_bytes()[:2] == b"\x1f\x8b" else open
    mode = "rt" if opener is gzip.open else "r"
    with opener(gz, mode, encoding="utf-8", errors="replace", newline="") as fh, open(
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
    MANIFEST.append({"dataset": code, "path": str(italy.relative_to(DB)), "status": "ok", "rows": kept})


def harvest_eurostat_prices_oil() -> None:
    log("== Eurostat prices / oil / gas IT ==")
    out = DB / "consumi-italia" / "sources" / "eurostat"
    out.mkdir(parents=True, exist_ok=True)
    for code in [
        "nrg_pc_204",  # electricity prices household
        "nrg_pc_205",  # electricity non-household
        "nrg_pc_202",  # gas household
        "nrg_pc_203",  # gas non-household
        "nrg_pc_202_c",  # gas consumption bands
        "nrg_ti_oil",  # oil trade
        "nrg_cb_oil",  # oil supply
        "nrg_bal_s",  # simplified energy balances
        "env_air_gge",  # GHG
        "nrg_ind_peih",  # primary energy
    ]:
        eurostat_italy(code, out)
        time.sleep(0.25)


# ---------------------------------------------------------------------------
# 3) ISPRA emissions / EF
# ---------------------------------------------------------------------------
def harvest_ispra() -> None:
    log("== ISPRA emissioni / fattori emissione ==")
    out = DB / "consumi-italia" / "sources" / "ispra"
    out.mkdir(parents=True, exist_ok=True)
    urls = [
        "https://emissioni.sina.isprambiente.it/wp-content/uploads/2024/02/FE_energia_elettrica_2023-V1.xlsx",
        "https://emissioni.sina.isprambiente.it/wp-content/uploads/2024/07/EF-combustion-2022.xlsx",
        "https://emissioni.sina.isprambiente.it/wp-content/uploads/2024/07/FE-offroad_2022.xlsx",
        "https://emissioni.sina.isprambiente.it/wp-content/uploads/2024/10/Indicatori-di-efficienza-energetica-in-Italia-Anno-2024.pdf",
        "https://emissioni.sina.isprambiente.it/wp-content/uploads/2024/10/Rapp-404-2024_-Energy-and-Decarbonization_2024.pdf",
        "https://emissioni.sina.isprambiente.it/wp-content/uploads/2023/10/Indicatori-di-efficienza-energetica-in-Italia-Anno-2023_web.pdf",
        "https://emissioni.sina.isprambiente.it/wp-content/uploads/2023/07/Indicatori-di-efficienza-energetica-in-Italia-Anno-2023_web.pdf",
    ]
    # crawl news + inventario for more xlsx/csv/zip
    for page in (
        "https://emissioni.sina.isprambiente.it/inventario-nazionale/",
        "https://emissioni.sina.isprambiente.it/news/",
        "https://emissioni.sina.isprambiente.it/",
    ):
        try:
            html = urllib.request.urlopen(
                urllib.request.Request(page, headers=UA), timeout=90
            ).read().decode("utf-8", "replace")
            found = re.findall(
                r"https://emissioni\.sina\.isprambiente\.it/wp-content/uploads/[^\s\"'<>]+\.(?:xlsx?|csv|zip)",
                html,
                re.I,
            )
            urls.extend(found)
        except Exception as e:
            log(f"  crawl {page}: {e}")
    for url in sorted(set(urls)):
        name = urllib.parse.unquote(url.rstrip("/").split("/")[-1])
        try_download(url, out / name, min_size=500)
        time.sleep(0.2)


# ---------------------------------------------------------------------------
# 4) Ember wholesale + carbon-related
# ---------------------------------------------------------------------------
def harvest_ember() -> None:
    log("== Ember prices / Italy extract ==")
    out = DB / "mercati-italia" / "sources" / "ember"
    out.mkdir(parents=True, exist_ok=True)
    files = [
        "https://files.ember-energy.org/public-downloads/european_wholesale_electricity_price_data_monthly.csv",
        "https://files.ember-energy.org/public-downloads/european_wholesale_electricity_price_data_daily.csv",
        "https://files.ember-energy.org/public-downloads/yearly_full_release_long_format.csv",
        "https://files.ember-energy.org/public-downloads/monthly_full_release_long_format.csv",
        "https://files.ember-energy.org/public-downloads/latest_generation_monthly.csv",
    ]
    for url in files:
        name = url.rsplit("/", 1)[-1]
        dest = out / name
        if not try_download(url, dest, min_size=500):
            continue
        if not name.endswith(".csv"):
            continue
        try:
            df = pd.read_csv(dest, low_memory=False)
            cols = {c.lower(): c for c in df.columns}
            country_col = cols.get("country") or cols.get("area") or cols.get("entity")
            if not country_col:
                continue
            it = df[df[country_col].astype(str).str.lower().eq("italy")].copy()
            tag = name.replace(".csv", "")
            it_path = out / f"italy__{tag}.csv"
            it.to_csv(it_path, index=False)
            log(f"  Italy extract {it_path.name} rows={len(it)}")
        except Exception as e:
            log(f"  filter {name}: {e}")


# ---------------------------------------------------------------------------
# 5) EU ETS — EEX primary auction reports (public Excel archives)
# ---------------------------------------------------------------------------
def harvest_eua() -> None:
    log("== EU ETS / EUA auction prices (best-effort) ==")
    out = DB / "mercati-italia" / "sources" / "ets_eua"
    out.mkdir(parents=True, exist_ok=True)
    # EEX publishes yearly auction report xlsx; probe recent years
    # Common public mirrors / known patterns
    candidates = []
    for year in range(2018, 2027):
        candidates.extend(
            [
                f"https://www.eex.com/fileadmin/EEX/Downloads/Trading/Environmentals/Emission_Spot_Primary_Market_Auction_Report/emission-spot-primary-market-auction-report-{year}-data.xlsx",
                f"https://www.eex.com/fileadmin/EEX/Downloads/Trading/Environmentals/Emission_Spot_Primary_Market_Auction_Report/Emission_Spot_Primary_Market_Auction_Report_{year}.xlsx",
                f"https://www.eex.com/fileadmin/Global/Content/Downloads/Trading/Environmentals/emission-spot-primary-market-auction-report-{year}-data.xlsx",
            ]
        )
    # ICAP weekly averages sometimes exposed as csv endpoints — skip if unknown
    # Zenodo EU ETS package (large) — try frictionless landing via DOI resolve skip
    for url in candidates:
        name = url.rsplit("/", 1)[-1]
        try_download(url, out / name, min_size=2000, timeout=120)
        time.sleep(0.2)

    # Eurostat no carbon price — use Ember daily wholesale as proxy context already saved
    # Also grab European Environment Agency ETS dashboard dump if available
    eea = [
        "https://eea.europa.eu/data-and-maps/data/european-union-emissions-trading-scheme-18/download",
    ]
    for url in eea:
        try_download(url, out / "eea_ets_landing.html", min_size=100, timeout=60)


# ---------------------------------------------------------------------------
# 6) GME secondary markets — daily XML zip via Download pages (probe)
# ---------------------------------------------------------------------------
def harvest_gme_secondary() -> None:
    log("== GME MI/MSD/MB (best-effort download API) ==")
    out = DB / "mercati-italia" / "sources" / "gme"
    # Historical yearly zips only confirmed for MGP. For others, try public domain zip
    # patterns used by some GME mirrors / Open Data aggregators.
    # 1) Keep MGP completeness note
    # 2) Try "Tutto IPEX" style if linked from FAQ paths — not stable.
    # 3) Download sample recent MSD/MI via known GetFile endpoints if any.

    # Probe GME GetMarketResults / public zip for a few recent months
    # (many require session cookies; we still try anonymous).
    markets = {
        "MI": out / "mi",
        "MSD": out / "msd",
        "MB": out / "mb",
        "MPEG": out / "mpeg",
    }
    for m, d in markets.items():
        d.mkdir(parents=True, exist_ok=True)
        (d / "README.txt").write_text(
            f"GME {m}: yearly DatiStorici ZIP not exposed like MGP (HTML returned).\n"
            f"Daily XML downloads require interactive Download UI / API session.\n"
            f"Place manual exports here.\n",
            encoding="utf-8",
        )

    # Attempt GME API v1 RequestData if public (often 401)
    api = "https://gme.mercatoelettrico.org/api/v1/RequestData"
    note = out / "secondary_api_probe.json"
    try:
        req = urllib.request.Request(api, headers={**UA, "Accept": "application/json"}, method="GET")
        with urllib.request.urlopen(req, timeout=30) as resp:
            note.write_bytes(resp.read()[:5000])
            log(f"  API probe status={resp.status}")
    except Exception as e:
        note.write_text(json.dumps({"api": api, "error": str(e)}, indent=2), encoding="utf-8")
        log(f"  API probe: {e}")

    # Wayback / alternate: some years of MI prices published in open aggregators — skip unstable


# ---------------------------------------------------------------------------
# 7) ENTSOG storage + ALSI LNG Italy
# ---------------------------------------------------------------------------
def harvest_entsog_storage_lng() -> None:
    log("== ENTSOG storage / LNG (IT) ==")
    out = DB / "mercati-italia" / "sources" / "entsog_snam"
    out.mkdir(parents=True, exist_ok=True)
    # operators already present; pull storage + LNG operational data
    for year in range(2021, 2027):
        for indicator, slug in [
            ("Storage", "storage"),
            ("Injection", "injection"),
            ("Withdrawal", "withdrawal"),
        ]:
            dest = out / f"italy_{slug}_{year}.csv"
            # country-level aggregation
            url = (
                "https://transparency.entsog.eu/api/v1/operationaldatas.csv"
                f"?indicator={urllib.parse.quote(indicator)}"
                f"&from={year}-01-01&to={year}-12-31"
                "&periodType=day&timezone=CET&limit=-1"
                "&countryKey=IT"
            )
            try_download(url, dest, min_size=80)
            time.sleep(0.35)

    # ALSI (LNG) public about — full data often needs key like AGSI
    alsi = DB / "mercati-italia" / "sources" / "alsi"
    alsi.mkdir(parents=True, exist_ok=True)
    for url, name in [
        ("https://alsi.gie.eu/api", "alsi_api_probe.json"),
        ("https://alsi.gie.eu/api/about", "alsi_about.json"),
        ("https://agsi.gie.eu/api/about", "agsi_about_refresh.json"),
    ]:
        try_download(url, alsi / name, min_size=20, timeout=60)


# ---------------------------------------------------------------------------
# 8) Open-Meteo — zonal centroids (irradiance + wind) for IT market zones
# ---------------------------------------------------------------------------
def harvest_meteo_zones() -> None:
    log("== Open-Meteo zone centroids (solar/wind) ==")
    out = DB / "meteo-italia" / "sources" / "open_meteo_zones"
    out.mkdir(parents=True, exist_ok=True)
    # Approximate zone centroids (lat, lon)
    zones = {
        "IT-North": (45.46, 9.19),
        "IT-Centre-North": (44.49, 11.34),
        "IT-Centre-South": (41.89, 12.49),
        "IT-South": (41.12, 16.87),
        "IT-Sicily": (37.50, 14.00),
        "IT-Sardinia": (40.12, 9.01),
        "IT-Calabria": (38.91, 16.59),
    }
    start = "2015-01-01"
    end = date.today().isoformat()
    hourly = (
        "temperature_2m,shortwave_radiation,direct_radiation,diffuse_radiation,"
        "wind_speed_10m,wind_direction_10m,precipitation,cloud_cover"
    )
    for name, (lat, lon) in zones.items():
        dest = out / f"{name}_hourly.csv"
        if dest.exists() and dest.stat().st_size > 1_000_000:
            log(f"  skip {dest.name}")
            continue
        url = (
            "https://archive-api.open-meteo.com/v1/archive?"
            + urllib.parse.urlencode(
                {
                    "latitude": lat,
                    "longitude": lon,
                    "start_date": start,
                    "end_date": end,
                    "hourly": hourly,
                    "timezone": "Europe/Rome",
                }
            )
        )
        try:
            log(f"  zone {name}")
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as resp:
                payload = json.loads(resp.read().decode())
            h = payload.get("hourly") or {}
            if not h:
                log(f"  empty {name}")
                continue
            df = pd.DataFrame(h)
            df.insert(0, "zone", name)
            df.insert(1, "lat", lat)
            df.insert(2, "lon", lon)
            df.to_csv(dest, index=False)
            log(f"  wrote {dest.name} rows={len(df)}")
            MANIFEST.append({"dataset": f"meteo_zone_{name}", "path": str(dest.relative_to(DB)), "status": "ok", "rows": len(df)})
            time.sleep(1.0)
        except Exception as e:
            log(f"  FAIL {name}: {e}")
            MANIFEST.append({"dataset": f"meteo_zone_{name}", "status": f"fail:{e}"})


# ---------------------------------------------------------------------------
# 9) UNFCCC / EEA GHG Italy CRF tables (open)
# ---------------------------------------------------------------------------
def harvest_unfccc_eea() -> None:
    log("== UNFCCC / EEA GHG Italy ==")
    out = DB / "consumi-italia" / "sources" / "ghg"
    out.mkdir(parents=True, exist_ok=True)
    # EEA data viewer dumps / climate-energy package
    urls = [
        (
            "https://www.eea.europa.eu/data-and-maps/data/national-emissions-reported-to-the-unfccc-and-to-the-eu-greenhouse-gas-monitoring-mechanism-20/"
            "national-greenhouse-gas-inventories-ipcc-common-reporting-format-sector-classification/greenhouse-gas-emissions-under-the-unfccc.csv/at_download/file",
            "eea_unfccc_ghg.csv",
        ),
        (
            "https://sdi.eea.europa.eu/datashare/public/4e1c4c6d-6a0e-4e2e-9a2f-eea_unfccc_placeholder",
            "skip",
        ),
    ]
    for url, name in urls:
        if name == "skip":
            continue
        try_download(url, out / name, min_size=1000, timeout=180)
        time.sleep(0.3)
    # Filter Italy from any large CSV downloaded into out
    for p in out.glob("*.csv"):
        try:
            df = pd.read_csv(p, low_memory=False)
            cols = {c.lower(): c for c in df.columns}
            geo = cols.get("country") or cols.get("geo") or cols.get("countrycode") or cols.get("country_code")
            if not geo:
                continue
            mask = df[geo].astype(str).str.contains("Italy|IT", case=False, na=False)
            it = df[mask]
            if len(it) == 0:
                continue
            dest = out / f"italy__{p.stem}.csv"
            it.to_csv(dest, index=False)
            log(f"  Italy filter {dest.name} rows={len(it)}")
        except Exception as e:
            log(f"  filter {p.name}: {e}")


# ---------------------------------------------------------------------------
# 10) MASE / energy stats PDFs if direct
# ---------------------------------------------------------------------------
def harvest_mase_notes() -> None:
    log("== MASE / note energetiche (best-effort) ==")
    out = DB / "consumi-italia" / "sources" / "mase"
    out.mkdir(parents=True, exist_ok=True)
    (out / "README.txt").write_text(
        "MASE bilanci energetici nazionali: pubblicati come PDF/XLS su sito ministeriale "
        "con URL che cambiano spesso. Aggiungere manualmente i file scaricati qui.\n"
        "Eurostat nrg_bal_* e nrg_cb_oil coprono gran parte del fabbisogno quantitativo.\n",
        encoding="utf-8",
    )


def main() -> int:
    log(f"START priority gaps {datetime.utcnow().isoformat()}Z")
    harvest_portale_offerte()
    harvest_eurostat_prices_oil()
    harvest_ispra()
    harvest_ember()
    harvest_eua()
    harvest_gme_secondary()
    harvest_entsog_storage_lng()
    harvest_meteo_zones()
    harvest_unfccc_eea()
    harvest_mase_notes()

    man = DB / "scripts" / "harvest_priority_gaps_manifest.json"
    man.write_text(json.dumps(MANIFEST, indent=2, ensure_ascii=False), encoding="utf-8")
    ok = sum(1 for m in MANIFEST if str(m.get("status")).startswith("ok") or m.get("status") == "skip")
    fail = sum(1 for m in MANIFEST if str(m.get("status")).startswith("fail"))
    log(f"DONE manifest={man} ok/skip={ok} fail={fail} total={len(MANIFEST)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
