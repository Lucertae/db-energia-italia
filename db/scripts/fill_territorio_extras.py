#!/usr/bin/env python3
"""Fill ISPRA attachments + Eurostat mobility extras; schedule meteo grid probe."""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "territorio-mobilita-italia/1.0"}


def log(msg: str) -> None:
    print(msg, flush=True)


def harvest_ispra() -> None:
    log("== ISPRA allegati ==")
    mobility = DB / "socio-italia" / "sources" / "mobility" / "ispra"
    land = DB / "socio-italia" / "sources" / "land_use" / "ispra"
    mobility.mkdir(parents=True, exist_ok=True)
    land.mkdir(parents=True, exist_ok=True)
    pages = [
        "https://indicatoriambientali.isprambiente.it/it/trasporti",
        "https://indicatoriambientali.isprambiente.it/it/suolo-e-territorio",
        "https://www.isprambiente.gov.it/it/banche-dati",
        "https://www.isprambiente.gov.it/it/pubblicazioni/rapporti/consumo-di-suolo-dinamiche-territoriali-e-servizi-ecosistemici-edizione-2025",
        "https://www.isprambiente.gov.it/it/pubblicazioni/rapporti/consumo-di-suolo-dinamiche-territoriali-e-servizi-ecosistemici-edizione-2024",
    ]
    all_links: set[str] = set()
    for page in pages:
        try:
            req = urllib.request.Request(page, headers=UA)
            html = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
            links = re.findall(r"""href=["']([^"']+)["']""", html, re.I)
            log(f"  page {page.split('/')[-1][:50]} links={len(links)}")
            for m in links:
                full = urllib.parse.urljoin(page, m)
                low = full.lower()
                if any(low.endswith(ext) for ext in (".csv", ".xlsx", ".xls", ".zip", ".ods", ".pdf")):
                    all_links.add(full)
        except Exception as e:
            log(f"  FAIL page: {e}")

    n = 0
    for u in sorted(all_links):
        low = u.lower()
        # Prefer tabular; keep small set of soil PDFs
        is_tab = any(low.endswith(ext) for ext in (".csv", ".xlsx", ".xls", ".zip", ".ods"))
        is_soil_pdf = low.endswith(".pdf") and any(k in low for k in ("suolo", "soil", "consumo", "trasport"))
        if not (is_tab or is_soil_pdf):
            continue
        name = urllib.parse.unquote(u.rstrip("/").split("/")[-1])
        name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)[:140]
        dest_dir = land if any(k in low for k in ("suolo", "soil", "land", "corine", "clc", "territorio")) else mobility
        dest = dest_dir / name
        if dest.exists() and dest.stat().st_size > 500:
            continue
        try:
            req = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as resp:
                data = resp.read()
            if data[:15].lower().startswith(b"<!doctype") or len(data) < 500:
                continue
            dest.write_bytes(data)
            log(f"  -> {dest.parent.name}/{dest.name} ({len(data)/1e6:.2f} MB)")
            n += 1
        except Exception as e:
            log(f"  FAIL {name}: {e}")
    log(f"  ispra files saved={n}")


def harvest_extra_eurostat() -> None:
    log("== Eurostat mobility/land extras ==")
    out_m = DB / "socio-italia" / "sources" / "mobility"
    out_g = DB / "socio-italia" / "sources" / "eurostat_gva"
    out_l = DB / "socio-italia" / "sources" / "land_use"
    codes = [
        (out_m, "road_eqs_carpda", "cars_per_1000_alt"),
        (out_m, "road_eqr_carhab", "cars_hab_region"),
        (out_m, "tran_hv_ms_psmod", "passenger_modalsplit"),
        (out_m, "nrg_d_hhq", "energy_hh_survey"),  # may 404
        (out_g, "nama_10r_2gdp", "gdp_nuts2"),
        (out_l, "lan_lcv_oec", "land_cover_oec"),
        (out_l, "ef_lus_allcrops", "farm_land_use"),
    ]
    for out, code, slug in codes:
        dest = out / f"{slug}_italy.csv"
        if dest.exists() and dest.stat().st_size > 500 and slug != "gdp_nuts2":
            # gdp_nuts2 already filled
            if slug == "gdp_nuts2":
                continue
            log(f"  skip {dest.name}")
            continue
        if dest.exists() and slug == "gdp_nuts2":
            log(f"  skip {dest.name}")
            continue
        url = (
            "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/"
            f"{code}?format=JSON&lang=en&geo=IT"
        )
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=120) as resp:
                payload = json.loads(resp.read().decode())
            value = payload.get("value") or {}
            if not value:
                log(f"  empty {code}")
                continue
            dims = payload["dimension"]
            ids = payload["id"]
            sizes = payload["size"]
            maps = {}
            for dim in ids:
                cat = dims[dim]["category"]
                index = cat.get("index", {})
                labels = cat.get("label", {})
                pos_to_code = {int(v): k for k, v in index.items()} if isinstance(index, dict) else {
                    i: str(v) for i, v in enumerate(index)
                }
                maps[dim] = {pos: (ck, labels.get(ck, ck)) for pos, ck in pos_to_code.items()}
            rows = []
            for flat_idx, obs in value.items():
                idx = int(flat_idx)
                rem = idx
                coords = {}
                for dim, size in zip(reversed(ids), reversed(sizes)):
                    pos = rem % size
                    rem //= size
                    ck, lab = maps[dim][pos]
                    coords[dim] = ck
                    coords[f"{dim}_label"] = lab
                coords["OBS_VALUE"] = obs
                rows.append(coords)
            df = pd.DataFrame(rows)
            if "geo" in df.columns:
                s = df["geo"].astype(str)
                df = df[s.eq("IT") | s.str.startswith("IT")].copy()
            df.to_csv(dest, index=False)
            log(f"  -> {dest.name} rows={len(df)}")
        except Exception as e:
            log(f"  FAIL {code}: {e}")


def try_meteo_grid_partial(max_points: int = 12) -> None:
    log("== Open-Meteo grid probe (partial) ==")
    out = DB / "meteo-italia" / "sources" / "open_meteo_grid"
    out.mkdir(parents=True, exist_ok=True)
    probe = {
        "latitude": 41.9,
        "longitude": 12.5,
        "start_date": "2024-06-01",
        "end_date": "2024-06-05",
        "daily": "precipitation_sum,temperature_2m_mean",
        "timezone": "Europe/Rome",
    }
    url = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(probe)
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as resp:
            json.loads(resp.read().decode())
        log("  probe OK — fetching partial grid")
    except Exception as e:
        log(f"  still 429/blocked: {e}")
        return

    points = [
        (45.5, 8.5),
        (45.5, 11.5),
        (44.5, 10.0),
        (44.5, 11.5),
        (43.5, 11.5),
        (42.5, 12.5),
        (41.5, 12.5),
        (41.5, 14.5),
        (40.5, 16.0),
        (39.5, 16.0),
        (38.5, 16.0),
        (37.5, 14.5),
        (39.5, 8.5),
        (40.5, 8.5),
    ][:max_points]
    daily = (
        "temperature_2m_mean,temperature_2m_max,temperature_2m_min,"
        "precipitation_sum,rain_sum,snowfall_sum,shortwave_radiation_sum,"
        "wind_speed_10m_max,weather_code"
    )
    end = (date.today() - timedelta(days=2)).isoformat()
    frames = []
    for i, (lat, lon) in enumerate(points):
        dest = out / f"grid_{lat}_{lon}_daily.csv"
        if dest.exists() and dest.stat().st_size > 5000:
            frames.append(pd.read_csv(dest))
            continue
        params = {
            "latitude": lat,
            "longitude": lon,
            "start_date": "2015-01-01",
            "end_date": end,
            "daily": daily,
            "timezone": "Europe/Rome",
            "precipitation_unit": "mm",
        }
        u = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(params)
        try:
            req = urllib.request.Request(u, headers=UA)
            with urllib.request.urlopen(req, timeout=180) as resp:
                payload = json.loads(resp.read().decode())
            df = pd.DataFrame(payload["daily"])
            df.insert(0, "lat", lat)
            df.insert(1, "lon", lon)
            df.to_csv(dest, index=False)
            frames.append(df)
            log(f"  grid {i+1}/{len(points)} {lat},{lon}")
            time.sleep(5)
        except Exception as e:
            log(f"  FAIL {lat},{lon}: {e}")
            if "429" in str(e):
                break
            time.sleep(12)
    if frames:
        all_df = pd.concat(frames, ignore_index=True)
        all_df.to_csv(out / "italy_grid_daily_partial.csv", index=False)
        log(f"  partial grid rows={len(all_df)} files={len(frames)}")


def main() -> None:
    harvest_ispra()
    harvest_extra_eurostat()
    try_meteo_grid_partial()
    log("DONE fill")


if __name__ == "__main__":
    main()
