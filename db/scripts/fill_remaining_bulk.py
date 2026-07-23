#!/usr/bin/env python3
"""Fill remaining large bulk gaps (no API keys required)."""
from __future__ import annotations

import csv
import gzip
import json
import shutil
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
UA = {
    "User-Agent": "Mozilla/5.0 (compatible; fill-remaining-bulk/1.0; +local research)",
    "Accept": "*/*",
}


def log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"), flush=True)


def download(url: str, dest: Path, *, force: bool = False, timeout: int = 600, min_size: int = 500) -> Path:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= min_size and not force:
        log(f"  skip {dest.name} ({dest.stat().st_size/1e6:.2f} MB)")
        return dest
    log(f"  GET {url[:160]}")
    req = urllib.request.Request(url, headers=UA)
    tmp = dest.with_suffix(dest.suffix + ".part")
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as f:
        shutil.copyfileobj(resp, f)
    if tmp.stat().st_size < min_size:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"too small: {dest.name}")
    tmp.replace(dest)
    log(f"  -> {dest.name} ({dest.stat().st_size/1e6:.2f} MB)")
    return dest


def eurostat_italy(code: str, out_dir: Path) -> None:
    gz = DB / "consumi-italia" / "_tmp" / f"{code}.csv.gz"
    italy = out_dir / f"{code}_italy.csv"
    if italy.exists() and italy.stat().st_size > 200:
        log(f"  skip {italy.name}")
        return
    url = (
        "https://ec.europa.eu/eurostat/databrowser-backend/api/extraction/1.0/"
        f"LIVE/false/sdmx/csv/{code}?i&compressed=true"
    )
    try:
        download(url, gz, force=True)
    except Exception as e:
        log(f"  FAIL {code}: {e}")
        return
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


def harvest_eurostat_more() -> None:
    log("== Eurostat extra energy IT ==")
    out = DB / "consumi-italia" / "sources" / "eurostat"
    out.mkdir(parents=True, exist_ok=True)
    # large / high-value energy tables not yet pulled (or complements to nrg_bal_c / prices)
    codes = [
        "nrg_ind_eff",  # energy efficiency indicators
        "nrg_ind_331a",  # electricity production capacities
        "nrg_ind_epcrf",  # electricity production capacity renewable
        "nrg_cb_e",  # electricity supply/consumption monthly
        "nrg_cb_gasm",  # gas monthly
        "nrg_ti_sff",  # solid fossil fuel trade
        "nrg_ti_oil",  # oil trade
        "nrg_ti_gbg",  # gas trade
        "nrg_inf_epcrf",  # renewable capacity infra
        "env_air_gge",  # GHG emissions
    ]
    for code in codes:
        eurostat_italy(code, out)
        time.sleep(0.3)


def harvest_world_bank_energy() -> None:
    log("== World Bank energy indicators Italy ==")
    out = DB / "consumi-italia" / "sources" / "worldbank"
    out.mkdir(parents=True, exist_ok=True)
    indicators = [
        "EG.USE.ELEC.KH.PC",  # electric power consumption per capita
        "EG.ELC.ACCS.ZS",  # access to electricity
        "EG.ELC.PROD.KH",  # electricity production
        "EG.ELC.LOSS.ZS",  # electric power transmission losses
        "EG.FEC.RNEW.ZS",  # renewable energy consumption %
        "EG.USE.PCAP.KG.OE",  # energy use per capita
        "EN.ATM.CO2E.KT",  # CO2 emissions
        "EG.IMP.CONS.ZS",  # energy imports
    ]
    frames: list[pd.DataFrame] = []
    for ind in indicators:
        url = (
            f"https://api.worldbank.org/v2/country/IT/indicator/{ind}"
            f"?format=json&per_page=20000&date=1960:{date.today().year}"
        )
        dest = out / f"{ind}.json"
        try:
            download(url, dest, force=True, min_size=50)
            payload = json.loads(dest.read_text(encoding="utf-8"))
            if not isinstance(payload, list) or len(payload) < 2:
                log(f"  empty {ind}")
                continue
            rows = payload[1] or []
            df = pd.DataFrame(rows)
            if df.empty:
                continue
            df["indicator_id"] = ind
            frames.append(df)
            log(f"  {ind}: {len(df)} rows")
        except Exception as e:
            log(f"  FAIL {ind}: {e}")
        time.sleep(0.25)
    if frames:
        all_df = pd.concat(frames, ignore_index=True)
        path = out / "italy_energy_indicators.csv"
        keep = [c for c in ["indicator_id", "date", "value", "countryiso3code", "unit", "obs_status"] if c in all_df.columns]
        # flatten nested indicator/country fields if present
        if "indicator" in all_df.columns:
            all_df["indicator_name"] = all_df["indicator"].apply(
                lambda x: x.get("value") if isinstance(x, dict) else x
            )
            keep.append("indicator_name")
        all_df[keep].to_csv(path, index=False)
        log(f"  wrote {path} rows={len(all_df)}")


def harvest_edgar_co2() -> None:
    log("== EDGAR / JRC CO2 fossil Italy (recent release) ==")
    out = DB / "consumi-italia" / "sources" / "edgar"
    out.mkdir(parents=True, exist_ok=True)
    # Public yearly country totals CSV mirrors often hosted on edgar.jrc.ec.europa.eu
    candidates = [
        (
            "https://jeodpp.jrc.ec.europa.eu/ftp/jrc-opendata/EDGAR/datasets/"
            "v80_FT2022_GHG/EDGARv8.0_FT2022_GHG_booklet_2023.xlsx",
            "EDGARv8.0_FT2022_GHG_booklet_2023.xlsx",
        ),
        (
            "https://raw.githubusercontent.com/owid/co2-data/master/owid-co2-data.csv",
            "owid-co2-data.csv",
        ),
    ]
    for url, name in candidates:
        dest = out / name
        try:
            download(url, dest, min_size=1000)
            if name.endswith(".csv") and "owid-co2" in name:
                df = pd.read_csv(dest, low_memory=False)
                col = next(c for c in df.columns if c.lower() in ("country", "iso_code"))
                if col.lower() == "iso_code":
                    it = df[df[col].astype(str).str.upper().eq("ITA")].copy()
                else:
                    it = df[df[col].astype(str).str.lower().eq("italy")].copy()
                it_path = out / "italy_owid_co2.csv"
                it.to_csv(it_path, index=False)
                log(f"  Italy CO2 rows={len(it)}")
        except Exception as e:
            log(f"  skip {name}: {e}")


def harvest_isprambiente() -> None:
    log("== ISPRA open energy/emissions files ==")
    out = DB / "consumi-italia" / "sources" / "ispra"
    out.mkdir(parents=True, exist_ok=True)
    # SINAnet / ISPRA frequently publish fixed URLs for national inventory annex tables
    urls = [
        # National Inventory Report related open tables (may 404; skip ok)
        "https://www.isprambiente.gov.it/files2024/pubblicazioni/rapporti/nir2024_italy.xlsx",
        "https://www.isprambiente.gov.it/files2023/pubblicazioni/rapporti/nir2023_italy.xlsx",
        "https://www.isprambiente.gov.it/it/attivita/rischi-ambientali-tecnologici/inventario-nazionale-emissioni/inventario_emissioni_ita.zip",
    ]
    for url in urls:
        name = url.rstrip("/").split("/")[-1]
        dest = out / name
        try:
            download(url, dest, min_size=2000)
        except Exception as e:
            log(f"  skip {name}: {e}")


def harvest_entsog_monthly() -> None:
    """Pre-2022 yearly often 404; try monthly chunks for SNAM physical flow."""
    log("== ENTSOG SNAM monthly backfill 2018-2021 ==")
    out = DB / "mercati-italia" / "sources" / "entsog_snam" / "monthly"
    out.mkdir(parents=True, exist_ok=True)
    for year in range(2018, 2022):
        for month in range(1, 13):
            dest = out / f"snam_physical_flow_{year}_{month:02d}.csv"
            if dest.exists() and dest.stat().st_size > 200:
                continue
            # first/last day
            if month == 12:
                last = 31
            else:
                last = (date(year, month + 1, 1).toordinal() - 1)
                last = date.fromordinal(last).day
            url = (
                "https://transparency.entsog.eu/api/v1/operationaldatas.csv"
                f"?operatorKey=IT-TSO-0001&indicator=Physical%20Flow"
                f"&from={year}-{month:02d}-01&to={year}-{month:02d}-{last:02d}"
                "&periodType=day&timezone=CET&limit=-1"
            )
            try:
                download(url, dest, min_size=80)
                n = sum(1 for _ in open(dest, encoding="utf-8", errors="replace")) - 1
                log(f"  {year}-{month:02d}: {n} rows")
                if n <= 0:
                    dest.unlink(missing_ok=True)
            except Exception as e:
                log(f"  FAIL {year}-{month:02d}: {e}")
            time.sleep(0.35)


def harvest_gme_2007() -> None:
    log("== GME Anno2007 force re-download (curl) ==")
    import subprocess

    out = DB / "mercati-italia" / "sources" / "gme" / "mgp_storici"
    out.mkdir(parents=True, exist_ok=True)
    dest = out / "Anno2007.zip"
    urls = [
        (
            "https://gme.mercatoelettrico.org/it-it/Home/Esiti/Elettricita/MGP/"
            "Statistiche/DatiStorici/moduleId/10874/controller/GmeDatiStoriciItem/"
            "action/DownloadFile?fileName=Anno2007.zip"
        ),
        # Internet Archive snapshots sometimes hold the full zip when origin truncates
        "https://web.archive.org/web/2020/https://gme.mercatoelettrico.org/it-it/Home/Esiti/Elettricita/MGP/Statistiche/DatiStorici/moduleId/10874/controller/GmeDatiStoriciItem/action/DownloadFile?fileName=Anno2007.zip",
    ]
    for attempt, url in enumerate(urls * 2):
        dest.unlink(missing_ok=True)
        part = dest.with_suffix(".zip.part")
        part.unlink(missing_ok=True)
        try:
            cmd = [
                "curl.exe",
                "-L",
                "--fail",
                "--retry",
                "2",
                "--retry-delay",
                "5",
                "--connect-timeout",
                "30",
                "--max-time",
                "300",
                "-A",
                UA["User-Agent"],
                "-o",
                str(part),
                url,
            ]
            log(f"  curl attempt {attempt+1} {url[:80]}...")
            proc = subprocess.run(cmd, capture_output=True, text=True)
            size = part.stat().st_size if part.exists() else 0
            if proc.returncode != 0 or size < 50_000:
                raise RuntimeError(f"curl rc={proc.returncode} size={size} err={(proc.stderr or '')[-200:]}")
            part.replace(dest)
            with zipfile.ZipFile(dest) as zf:
                bad = zf.testzip()
                if bad is not None:
                    raise RuntimeError(f"corrupt member {bad}")
                extract_dir = out / "Anno2007"
                if extract_dir.exists():
                    shutil.rmtree(extract_dir)
                extract_dir.mkdir(parents=True, exist_ok=True)
                zf.extractall(extract_dir)
                names = [p.name for p in extract_dir.rglob("*") if p.is_file()]
            log(f"  ZIP OK size={dest.stat().st_size/1e6:.2f} MB files={names[:8]}")
            return
        except Exception as e:
            log(f"  attempt {attempt+1} fail: {e}")
            dest.unlink(missing_ok=True)
            part.unlink(missing_ok=True)
            time.sleep(4 + attempt * 3)
    log("  Anno2007 still unavailable — leave marker")
    (out / "Anno2007.FAILED.txt").write_text(
        "GME server drops connection mid-download for Anno2007.zip. Retry manually later.\n",
        encoding="utf-8",
    )


def harvest_gme_other_markets() -> None:
    """Try MI / MSD yearly archives with same GME controller pattern."""
    log("== GME MI/MSD storici (best-effort) ==")
    base = (
        "https://gme.mercatoelettrico.org/it-it/Home/Esiti/Elettricita/{market}/"
        "Statistiche/DatiStorici/moduleId/{mid}/controller/GmeDatiStoriciItem/"
        "action/DownloadFile?fileName="
    )
    # moduleIds observed historically for MGP=10874; MI/MSD may differ — probe common names
    probes = [
        ("MGP", 10874, DB / "mercati-italia" / "sources" / "gme" / "mgp_storici"),
    ]
    for market, mid, out in probes:
        out.mkdir(parents=True, exist_ok=True)
        for year in range(2004, 2027):
            for fname in (f"Anno{year}.zip", f"Anno {year}.zip"):
                dest = out / fname.replace(" ", "")
                if dest.exists() and dest.stat().st_size > 50_000:
                    # validate zip
                    try:
                        with zipfile.ZipFile(dest) as zf:
                            if zf.testzip() is None:
                                break
                    except zipfile.BadZipFile:
                        pass
                url = base.format(market=market, mid=mid) + urllib.parse.quote(fname)
                try:
                    download(url, dest, force=True, timeout=900, min_size=20_000)
                    with zipfile.ZipFile(dest) as zf:
                        if zf.testzip() is not None:
                            raise RuntimeError("bad zip")
                    log(f"  OK {market} {fname}")
                    break
                except Exception:
                    continue
            time.sleep(0.2)


def harvest_ember_extras() -> None:
    log("== Ember extras ==")
    out = DB / "mercati-italia" / "sources" / "ember"
    out.mkdir(parents=True, exist_ok=True)
    urls = [
        "https://files.ember-energy.org/public-downloads/yearly_full_release_long_format.csv",
        "https://files.ember-energy.org/public-downloads/monthly_full_release_long_format.csv",
        "https://files.ember-energy.org/public-downloads/european_electricity_review_data.xlsx",
        "https://files.ember-energy.org/public-downloads/latest_generation_monthly.csv",
    ]
    for url in urls:
        name = url.rsplit("/", 1)[-1]
        dest = out / name
        try:
            download(url, dest, min_size=500)
            if name.endswith(".csv") and "long_format" in name:
                head = dest.read_bytes()[:40].lower()
                if b"<html" in head:
                    log(f"  HTML for {name}, skip filter")
                    continue
                df = pd.read_csv(dest, low_memory=False)
                col = next(c for c in df.columns if c.lower() in ("country", "area", "entity"))
                it = df[df[col].astype(str).str.lower().eq("italy")].copy()
                tag = "yearly" if "yearly" in name else "monthly"
                it_path = out / f"italy_{tag}.csv"
                it.to_csv(it_path, index=False)
                log(f"  Italy {tag} rows={len(it)}")
        except Exception as e:
            log(f"  skip {name}: {e}")


def write_report(extra_notes: list[str]) -> None:
    path = DB / "docs" / "harvest_fill_notes.md"
    lines = [
        "# Gap fill status",
        "",
        f"Updated: {date.today().isoformat()}",
        "",
        "## Filled / attempted",
        "- Ember yearly + monthly Italy",
        "- Eurostat prices + extra nrg_* / env_air_gge Italy",
        "- World Bank energy indicators Italy",
        "- EDGAR/OWID CO2 Italy extract",
        "- ISPRA NIR candidates (best-effort URLs)",
        "- ENTSOG SNAM monthly 2018–2021 backfill attempt",
        "- GME Anno2007 re-download + zip validate",
        "- Open-Meteo 6+ cities (see meteo-italia)",
        "- ENTSO-E harvest still running (zones)",
        "",
        "## Still blocked / need keys or UI",
        "- AGSI gas storage — GIE API key (free)",
        "- GSE open-data CSV — ASP.NET postback only",
        "- GSE Atlaimpianti — export UI",
        "- ENTSOG point-level pre-2022 — may remain empty",
        "- Terna energy-balance — API 406 / params",
        "",
    ]
    lines.extend(extra_notes)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log(f"wrote {path}")


def main() -> int:
    notes: list[str] = []
    # Do reliable bulk first; GME 2007 last (server often hangs)
    harvest_eurostat_more()
    harvest_world_bank_energy()
    harvest_edgar_co2()
    harvest_isprambiente()
    harvest_entsog_monthly()
    harvest_ember_extras()
    harvest_gme_2007()
    write_report(notes)
    log("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
