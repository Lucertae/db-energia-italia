#!/usr/bin/env python3
"""Open-Meteo archive: richer hourly + daily weather for IT cities and ENTSO zones.

Includes precipitation split (rain / snowfall / showers), snow depth, weather codes,
humidity, pressure, gusts, and solar fields useful for load/renewables.

Fetches full 2015->today per location (few API calls) then splits city files by year.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT_CITIES = ROOT / "sources" / "meteo"
OUT_ZONES = ROOT / "sources" / "open_meteo_zones"
OUT_DAILY_CITIES = ROOT / "sources" / "meteo_daily"
OUT_DAILY_ZONES = ROOT / "sources" / "open_meteo_zones_daily"
UA = {"User-Agent": "meteo-italia/2.0"}

CITIES = {
    "Roma": (41.9028, 12.4964),
    "Milano": (45.4642, 9.1900),
    "Napoli": (40.8518, 14.2681),
    "Torino": (45.0703, 7.6869),
    "Palermo": (38.1157, 13.3615),
    "Bologna": (44.4949, 11.3426),
    "Firenze": (43.7696, 11.2558),
    "Venezia": (45.4408, 12.3155),
    "Genova": (44.4056, 8.9463),
    "Bari": (41.1171, 16.8719),
    "Cagliari": (39.2238, 9.1217),
    "Verona": (45.4384, 10.9916),
}

ZONES = {
    "IT-North": (45.46, 9.19),
    "IT-Centre-North": (44.49, 11.34),
    "IT-Centre-South": (41.89, 12.49),
    "IT-South": (41.12, 16.87),
    "IT-Sicily": (37.50, 14.00),
    "IT-Sardinia": (40.12, 9.01),
    "IT-Calabria": (38.91, 16.59),
}

REQUIRED_COLS = {"rain", "snowfall", "snow_depth", "weather_code", "precipitation"}

HOURLY_VARS = [
    "temperature_2m",
    "relative_humidity_2m",
    "dew_point_2m",
    "apparent_temperature",
    "precipitation",
    "rain",
    "showers",
    "snowfall",
    "snow_depth",
    "weather_code",
    "pressure_msl",
    "surface_pressure",
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "wind_speed_10m",
    "wind_direction_10m",
    "wind_gusts_10m",
    "shortwave_radiation",
    "direct_radiation",
    "diffuse_radiation",
    "direct_normal_irradiance",
    "sunshine_duration",
    "et0_fao_evapotranspiration",
    "vapour_pressure_deficit",
    "soil_temperature_0_to_7cm",
    "soil_moisture_0_to_7cm",
]

DAILY_VARS = [
    "weather_code",
    "temperature_2m_max",
    "temperature_2m_min",
    "temperature_2m_mean",
    "apparent_temperature_max",
    "apparent_temperature_min",
    "apparent_temperature_mean",
    "precipitation_sum",
    "rain_sum",
    "snowfall_sum",
    "precipitation_hours",
    "wind_speed_10m_max",
    "wind_gusts_10m_max",
    "wind_direction_10m_dominant",
    "shortwave_radiation_sum",
    "et0_fao_evapotranspiration",
    "sunshine_duration",
]


def log(msg: str) -> None:
    print(msg, flush=True)


def _get_json(url: str, retries: int = 8) -> dict:
    last: Exception | None = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=300) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            last = e
            if e.code == 429:
                sleep = min(300, 90 + i * 45)
            else:
                sleep = min(90, 2**i)
            log(f"  retry {i+1}/{retries} sleep {sleep}s: {e}")
            time.sleep(sleep)
        except Exception as e:
            last = e
            sleep = min(90, 2**i)
            log(f"  retry {i+1}/{retries} sleep {sleep}s: {e}")
            time.sleep(sleep)
    raise RuntimeError(f"request failed: {last}")


def _schema_ok(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 2000:
        return False
    try:
        return REQUIRED_COLS.issubset(set(pd.read_csv(path, nrows=0).columns))
    except Exception:
        return False


def _daily_ok(path: Path) -> bool:
    if not path.exists() or path.stat().st_size < 500:
        return False
    try:
        cols = set(pd.read_csv(path, nrows=0).columns)
        return {"rain_sum", "snowfall_sum", "precipitation_sum"}.issubset(cols)
    except Exception:
        return False


def fetch_archive(
    lat: float,
    lon: float,
    start: str,
    end: str,
    *,
    hourly: bool = True,
    daily: bool = False,
) -> dict:
    params: dict[str, str] = {
        "latitude": str(lat),
        "longitude": str(lon),
        "start_date": start,
        "end_date": end,
        "timezone": "Europe/Rome",
        "precipitation_unit": "mm",
        "wind_speed_unit": "kmh",
    }
    if hourly:
        params["hourly"] = ",".join(HOURLY_VARS)
    if daily:
        params["daily"] = ",".join(DAILY_VARS)
    url = "https://archive-api.open-meteo.com/v1/archive?" + urllib.parse.urlencode(params)
    return _get_json(url)


def _split_and_write_years(
    df: pd.DataFrame,
    out_dir: Path,
    name: str,
    *,
    lat: float,
    lon: float,
    id_col: str,
    is_daily: bool,
) -> list[pd.DataFrame]:
    out_dir.mkdir(parents=True, exist_ok=True)
    df = df.copy()
    df[id_col] = name
    df["lat"] = lat
    df["lon"] = lon
    ts = pd.to_datetime(df["time"])
    parts: list[pd.DataFrame] = []
    for year, g in df.groupby(ts.dt.year):
        dest = out_dir / f"{name}_{int(year)}.csv"
        g2 = g.copy()
        g2["time"] = (
            pd.to_datetime(g2["time"]).dt.strftime("%Y-%m-%d")
            if is_daily
            else pd.to_datetime(g2["time"]).dt.strftime("%Y-%m-%dT%H:%M")
        )
        g2.to_csv(dest, index=False)
        parts.append(g2)
        log(f"  wrote {dest.name} rows={len(g2)}")
    return parts


def harvest_cities(*, force: bool = False, daily: bool = True) -> None:
    OUT_CITIES.mkdir(parents=True, exist_ok=True)
    if daily:
        OUT_DAILY_CITIES.mkdir(parents=True, exist_ok=True)
    frames: list[pd.DataFrame] = []
    daily_frames: list[pd.DataFrame] = []
    today = date.today()
    # Archive API often lags 1–2 days; avoid 400 on "today"
    end_day = today - __import__("datetime").timedelta(days=2)
    years = list(range(2015, today.year + 1))
    start, end = "2015-01-01", end_day.isoformat()

    for name, (lat, lon) in CITIES.items():
        need_h = force or any(
            (not _schema_ok(OUT_CITIES / f"{name}_{y}.csv")) or y == today.year for y in years
        )
        need_d = daily and (
            force
            or any(
                (not _daily_ok(OUT_DAILY_CITIES / f"{name}_{y}.csv")) or y == today.year
                for y in years
            )
        )
        if not need_h and not need_d:
            log(f"  skip city {name}")
            for y in years:
                frames.append(pd.read_csv(OUT_CITIES / f"{name}_{y}.csv"))
                if daily:
                    daily_frames.append(pd.read_csv(OUT_DAILY_CITIES / f"{name}_{y}.csv"))
            continue

        log(f"  fetch city {name} {start}->{end}")
        try:
            payload = fetch_archive(lat, lon, start, end, hourly=need_h, daily=need_d)
            if need_h:
                frames.extend(
                    _split_and_write_years(
                        pd.DataFrame(payload["hourly"]),
                        OUT_CITIES,
                        name,
                        lat=lat,
                        lon=lon,
                        id_col="city",
                        is_daily=False,
                    )
                )
            else:
                for y in years:
                    frames.append(pd.read_csv(OUT_CITIES / f"{name}_{y}.csv"))
            if need_d and "daily" in payload:
                daily_frames.extend(
                    _split_and_write_years(
                        pd.DataFrame(payload["daily"]),
                        OUT_DAILY_CITIES,
                        name,
                        lat=lat,
                        lon=lon,
                        id_col="city",
                        is_daily=True,
                    )
                )
            elif daily:
                for y in years:
                    p = OUT_DAILY_CITIES / f"{name}_{y}.csv"
                    if p.exists():
                        daily_frames.append(pd.read_csv(p))
        except Exception as e:
            log(f"  FAIL city {name}: {e}")
            for y in years:
                hp = OUT_CITIES / f"{name}_{y}.csv"
                if _schema_ok(hp):
                    frames.append(pd.read_csv(hp))
                dp = OUT_DAILY_CITIES / f"{name}_{y}.csv"
                if daily and _daily_ok(dp):
                    daily_frames.append(pd.read_csv(dp))
            time.sleep(60)
        time.sleep(12.0)

    if frames:
        all_path = OUT_CITIES / "italy_cities_hourly_2015_2026.csv"
        all_df = pd.concat(frames, ignore_index=True)
        all_df.to_csv(all_path, index=False)
        log(f"wrote {all_path.name} rows={len(all_df)} cols={len(all_df.columns)}")
    if daily and daily_frames:
        all_d = OUT_DAILY_CITIES / "italy_cities_daily_2015_2026.csv"
        ddf = pd.concat(daily_frames, ignore_index=True)
        ddf.to_csv(all_d, index=False)
        log(f"wrote {all_d.name} rows={len(ddf)} cols={len(ddf.columns)}")


def harvest_zones(*, force: bool = False, daily: bool = True) -> None:
    OUT_ZONES.mkdir(parents=True, exist_ok=True)
    if daily:
        OUT_DAILY_ZONES.mkdir(parents=True, exist_ok=True)
    today = date.today()
    end_day = today - __import__("datetime").timedelta(days=2)
    start, end = "2015-01-01", end_day.isoformat()
    for name, (lat, lon) in ZONES.items():
        dest = OUT_ZONES / f"{name}_hourly.csv"
        daily_dest = OUT_DAILY_ZONES / f"{name}_daily.csv"
        need = force or not _schema_ok(dest)
        need_daily = daily and (force or not _daily_ok(daily_dest))
        if not need and not need_daily:
            log(f"  skip zone {name}")
            continue
        log(f"  fetch zone {name} {start}->{end}")
        try:
            payload = fetch_archive(lat, lon, start, end, hourly=need, daily=need_daily)
            if need:
                df = pd.DataFrame(payload["hourly"])
                df.insert(0, "zone", name)
                df.insert(1, "lat", lat)
                df.insert(2, "lon", lon)
                df.to_csv(dest, index=False)
                log(f"  zone hourly {name}: {len(df)} rows")
            if need_daily and "daily" in payload:
                ddf = pd.DataFrame(payload["daily"])
                ddf.insert(0, "zone", name)
                ddf.insert(1, "lat", lat)
                ddf.insert(2, "lon", lon)
                ddf.to_csv(daily_dest, index=False)
                log(f"  zone daily  {name}: {len(ddf)} rows")
        except Exception as e:
            log(f"  FAIL zone {name}: {e}")
            time.sleep(60)
        time.sleep(12.0)


def write_metadati() -> None:
    text = f"""================================================================================
METADATI — Meteo Italia (Open-Meteo Archive)
================================================================================
Aggiornato: {date.today().isoformat()}
Path:       db/meteo-italia/

--------------------------------------------------------------------------------
1. DESCRIZIONE
--------------------------------------------------------------------------------
Serie orarie e giornaliere da Open-Meteo Historical Weather API (ERA5 / archive)
per 12 città IT e 7 centroidi zone di mercato elettrico ENTSO-E.
Include quantità di precipitazione totale, pioggia, neve (snowfall), snow_depth,
weather_code, umidità, pressione, raffiche, irraggiamento.

--------------------------------------------------------------------------------
2. REFRESH
--------------------------------------------------------------------------------
python db/meteo-italia/scripts/harvest_open_meteo.py
python db/meteo-italia/scripts/harvest_open_meteo.py --force
python db/meteo-italia/scripts/harvest_open_meteo.py --cities-only
python db/meteo-italia/scripts/harvest_open_meteo.py --zones-only

Resume: riscarica se mancano rain/snowfall/snow_depth o file daily.

--------------------------------------------------------------------------------
3. LOCATION
--------------------------------------------------------------------------------
Città: {', '.join(CITIES)}
Zone:  {', '.join(ZONES)}
Timezone: Europe/Rome
Unità precip: mm | snowfall: cm | snow_depth: m | vento: km/h

--------------------------------------------------------------------------------
4. VARIABILI ORARIE
--------------------------------------------------------------------------------
{chr(10).join(HOURLY_VARS)}

Note:
  precipitation = rain + showers + snowfall (water equivalent, mm)
  rain / showers = mm liquidi
  snowfall = cm neve
  snow_depth = m
  weather_code = WMO synop code

--------------------------------------------------------------------------------
5. VARIABILI GIORNALIERE (quantità)
--------------------------------------------------------------------------------
{chr(10).join(DAILY_VARS)}

--------------------------------------------------------------------------------
6. OUTPUT
--------------------------------------------------------------------------------
sources/meteo/<Citta>_<anno>.csv
sources/meteo/italy_cities_hourly_2015_2026.csv
sources/meteo_daily/<Citta>_<anno>.csv
sources/meteo_daily/italy_cities_daily_2015_2026.csv
sources/open_meteo_zones/<ZONE>_hourly.csv
sources/open_meteo_zones_daily/<ZONE>_daily.csv

Periodo: 2015-01-01 -> oggi

--------------------------------------------------------------------------------
7. LICENZA
--------------------------------------------------------------------------------
Open-Meteo + ERA5 (Copernicus/ECMWF). Attribuire Open-Meteo / C3S.
================================================================================
"""
    (ROOT / "METADATI.txt").write_text(text, encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--cities-only", action="store_true")
    ap.add_argument("--zones-only", action="store_true")
    ap.add_argument("--no-daily", action="store_true")
    args = ap.parse_args()
    do_cities = not args.zones_only
    do_zones = not args.cities_only
    daily = not args.no_daily
    if do_cities:
        log("== cities ==")
        harvest_cities(force=args.force, daily=daily)
    if do_zones:
        log("== zones ==")
        harvest_zones(force=args.force, daily=daily)
    write_metadati()
    log("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
