#!/usr/bin/env python3
"""Alternative meteo harvest when Open-Meteo is rate-limited.

Sources (no API key):
  1) NASA POWER daily point API — national sparse grid + cities + ENTSO zones
  2) Meteostat bulk daily — Italian weather stations (~237)

Outputs under meteo-italia/sources/nasa_power_* and meteo_stations_meteostat/.
"""
from __future__ import annotations

import gzip
import io
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "meteo-italia-alt/1.0 (nasa-power+meteostat)"}
START = "20150101"
# POWER usually lags a few days
END = (date.today() - timedelta(days=5)).strftime("%Y%m%d")
END_ISO = (date.today() - timedelta(days=5)).isoformat()

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

POWER_PARAMS = "T2M,T2M_MAX,T2M_MIN,PRECTOTCORR,WS10M,WD10M,ALLSKY_SFC_SW_DWN,RH2M,PS"


def log(msg: str) -> None:
    print(msg, flush=True)


def get_bytes(url: str, timeout: int = 180, retries: int = 5) -> bytes:
    last: Exception | None = None
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=UA)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read()
        except urllib.error.HTTPError as e:
            # Never retry missing objects
            if e.code in (404, 410):
                raise
            last = e
            wait = min(90, 8 * (i + 1))
            log(f"  retry {i+1}/{retries} sleep {wait}s: {e}")
            time.sleep(wait)
        except Exception as e:
            last = e
            wait = min(90, 8 * (i + 1))
            log(f"  retry {i+1}/{retries} sleep {wait}s: {e}")
            time.sleep(wait)
    raise RuntimeError(f"request failed: {last}")


def italy_grid_points() -> list[tuple[float, float]]:
    points: list[tuple[float, float]] = []
    for lat in [36.5, 37.5, 38.5, 39.5, 40.5, 41.5, 42.5, 43.5, 44.5, 45.5, 46.5]:
        for lon in [7.0, 8.5, 10.0, 11.5, 13.0, 14.5, 16.0, 17.5]:
            if lat < 37 and lon < 12:
                continue
            if lat > 46 and lon > 14:
                continue
            points.append((round(lat, 2), round(lon, 2)))
    return points


def power_daily(lat: float, lon: float) -> pd.DataFrame:
    params = {
        "parameters": POWER_PARAMS,
        "community": "RE",
        "longitude": lon,
        "latitude": lat,
        "start": START,
        "end": END,
        "format": "JSON",
    }
    url = "https://power.larc.nasa.gov/api/temporal/daily/point?" + urllib.parse.urlencode(params)
    payload = json.loads(get_bytes(url).decode("utf-8"))
    series = payload["properties"]["parameter"]
    # dates as YYYYMMDD keys
    dates = sorted(series[next(iter(series))].keys())
    rows = []
    for d in dates:
        row = {"date": f"{d[:4]}-{d[4:6]}-{d[6:8]}", "lat": lat, "lon": lon}
        for key, vals in series.items():
            v = vals.get(d)
            # POWER uses -999 for missing
            row[key] = None if v is None or v == -999 or v == -999.0 else v
        rows.append(row)
    df = pd.DataFrame(rows)
    rename = {
        "T2M": "temp_mean_c",
        "T2M_MAX": "temp_max_c",
        "T2M_MIN": "temp_min_c",
        "PRECTOTCORR": "precipitation_mm",
        "WS10M": "wind_speed_10m_ms",
        "WD10M": "wind_dir_10m_deg",
        "ALLSKY_SFC_SW_DWN": "shortwave_kwh_m2_day",
        "RH2M": "relative_humidity_pct",
        "PS": "surface_pressure_kpa",
    }
    return df.rename(columns=rename)


def harvest_nasa_power() -> None:
    log("== NASA POWER daily (grid + cities + zones) ==")
    out_grid = ROOT / "sources" / "nasa_power_grid"
    out_cities = ROOT / "sources" / "nasa_power_cities"
    out_zones = ROOT / "sources" / "nasa_power_zones"
    for d in (out_grid, out_cities, out_zones):
        d.mkdir(parents=True, exist_ok=True)

    frames_grid = []
    points = italy_grid_points()
    for i, (lat, lon) in enumerate(points):
        dest = out_grid / f"grid_{lat}_{lon}_daily.csv"
        if dest.exists() and dest.stat().st_size > 5000:
            frames_grid.append(pd.read_csv(dest))
            log(f"  skip grid {i+1}/{len(points)} {lat},{lon}")
            continue
        try:
            df = power_daily(lat, lon)
            df.to_csv(dest, index=False)
            frames_grid.append(df)
            log(f"  grid {i+1}/{len(points)} {lat},{lon} rows={len(df)}")
            time.sleep(1.2)
        except Exception as e:
            log(f"  FAIL grid {lat},{lon}: {e}")
            time.sleep(5)

    if frames_grid:
        all_df = pd.concat(frames_grid, ignore_index=True)
        all_path = out_grid / "italy_grid_daily_2015_present.csv"
        all_df.to_csv(all_path, index=False)
        log(f"  wrote {all_path.name} rows={len(all_df)} points={len(frames_grid)}")

    frames_c = []
    for name, (lat, lon) in CITIES.items():
        dest = out_cities / f"{name}_daily.csv"
        if dest.exists() and dest.stat().st_size > 5000:
            frames_c.append(pd.read_csv(dest))
            log(f"  skip city {name}")
            continue
        try:
            df = power_daily(lat, lon)
            df.insert(0, "city", name)
            df.to_csv(dest, index=False)
            frames_c.append(df)
            log(f"  city {name} rows={len(df)}")
            time.sleep(1.2)
        except Exception as e:
            log(f"  FAIL city {name}: {e}")

    if frames_c:
        pd.concat(frames_c, ignore_index=True).to_csv(
            out_cities / "italy_cities_daily_2015_present.csv", index=False
        )

    frames_z = []
    for name, (lat, lon) in ZONES.items():
        dest = out_zones / f"{name}_daily.csv"
        if dest.exists() and dest.stat().st_size > 5000:
            frames_z.append(pd.read_csv(dest))
            log(f"  skip zone {name}")
            continue
        try:
            df = power_daily(lat, lon)
            df.insert(0, "zone", name)
            df.to_csv(dest, index=False)
            frames_z.append(df)
            log(f"  zone {name} rows={len(df)}")
            time.sleep(1.2)
        except Exception as e:
            log(f"  FAIL zone {name}: {e}")

    if frames_z:
        pd.concat(frames_z, ignore_index=True).to_csv(
            out_zones / "italy_zones_daily_2015_present.csv", index=False
        )

    (out_grid / "README.txt").write_text(
        "NASA POWER daily reanalysis/satellite blend (no API key).\n"
        f"period={START}..{END}\n"
        "precipitation_mm = PRECTOTCORR (bias-corrected), temp °C, wind m/s, SW kWh/m2/day.\n"
        "Docs: https://power.larc.nasa.gov/\n",
        encoding="utf-8",
    )


def harvest_meteostat() -> None:
    log("== Meteostat daily stations (Italy) ==")
    out = ROOT / "sources" / "meteostat_stations"
    out.mkdir(parents=True, exist_ok=True)

    inv_path = out / "stations_IT.json"
    if not inv_path.exists():
        raw = get_bytes("https://bulk.meteostat.net/v2/stations/full.json.gz")
        stations = json.loads(gzip.decompress(raw).decode("utf-8"))
        it = [s for s in stations if s.get("country") == "IT"]
        inv_path.write_text(json.dumps(it, indent=2), encoding="utf-8")
        log(f"  stations IT={len(it)}")
    else:
        it = json.loads(inv_path.read_text(encoding="utf-8"))
        log(f"  loaded stations IT={len(it)}")

    # meta table
    meta_rows = []
    for s in it:
        loc = s.get("location") or {}
        name = s.get("name") or {}
        if isinstance(name, dict):
            name = name.get("en") or name.get("it") or next(iter(name.values()), s["id"])
        inv = (s.get("inventory") or {}).get("daily") or {}
        meta_rows.append(
            {
                "id": s["id"],
                "name": name,
                "lat": loc.get("latitude"),
                "lon": loc.get("longitude"),
                "elevation": loc.get("elevation"),
                "daily_start": inv.get("start"),
                "daily_end": inv.get("end"),
            }
        )
    meta = pd.DataFrame(meta_rows)
    meta.to_csv(out / "stations_IT_meta.csv", index=False)

    # Prefer stations with daily inventory overlapping 2015+
    meta_ok = meta.copy()
    if "daily_end" in meta_ok.columns:
        meta_ok = meta_ok[meta_ok["daily_end"].notna()].copy()
        meta_ok = meta_ok[meta_ok["daily_end"].astype(str) >= "2015-01-01"].copy()
    log(f"  stations with daily inventory since 2015: {len(meta_ok)}/{len(meta)}")

    frames = []
    ok = 0
    miss = 0
    for _, row in meta_ok.iterrows():
        sid = str(row["id"])
        dest = out / "daily" / f"{sid}.csv"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists() and dest.stat().st_size > 800:
            try:
                df = pd.read_csv(dest)
                if list(df.columns)[:1] != ["date"] and "tavg" not in df.columns:
                    cols = [
                        "date",
                        "tavg",
                        "tmin",
                        "tmax",
                        "prcp",
                        "snow",
                        "wdir",
                        "wspd",
                        "wpgt",
                        "pres",
                        "tsun",
                    ]
                    df = pd.read_csv(dest, header=None, names=cols)
                if "date" in df.columns:
                    df = df[(df["date"] >= "2015-01-01") & (df["date"] <= END_ISO)].copy()
                for c in ("tavg", "tmin", "tmax", "prcp", "snow", "wdir", "wspd", "wpgt", "pres", "tsun"):
                    if c in df.columns:
                        df[c] = pd.to_numeric(df[c], errors="coerce")
                df.insert(0, "station_id", sid)
                df.insert(1, "station_name", row["name"])
                df.insert(2, "lat", row["lat"])
                df.insert(3, "lon", row["lon"])
                frames.append(df)
                ok += 1
                continue
            except Exception:
                pass
        url = f"https://bulk.meteostat.net/v2/daily/{sid}.csv.gz"
        try:
            raw = get_bytes(url, timeout=60, retries=2)
            text = gzip.decompress(raw).decode("utf-8", "replace")
            cols = [
                "date",
                "tavg",
                "tmin",
                "tmax",
                "prcp",
                "snow",
                "wdir",
                "wspd",
                "wpgt",
                "pres",
                "tsun",
            ]
            first = text.splitlines()[0] if text else ""
            if first.startswith("date,"):
                df = pd.read_csv(io.StringIO(text))
            else:
                df = pd.read_csv(io.StringIO(text), header=None, names=cols)
            if "date" in df.columns:
                df = df[(df["date"] >= "2015-01-01") & (df["date"] <= END_ISO)].copy()
            for c in ("tavg", "tmin", "tmax", "prcp", "snow", "wdir", "wspd", "wpgt", "pres", "tsun"):
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce")
            df.to_csv(dest, index=False)
            df2 = df.copy()
            df2.insert(0, "station_id", sid)
            df2.insert(1, "station_name", row["name"])
            df2.insert(2, "lat", row["lat"])
            df2.insert(3, "lon", row["lon"])
            frames.append(df2)
            ok += 1
            if (ok % 25) == 0:
                log(f"  stations ok={ok} miss={miss}/{len(meta_ok)}")
            time.sleep(0.25)
        except urllib.error.HTTPError as e:
            miss += 1
            if e.code not in (404, 410):
                log(f"  FAIL station {sid}: {e}")
            time.sleep(0.15)
        except Exception as e:
            miss += 1
            log(f"  FAIL station {sid}: {e}")
            time.sleep(0.5)
    log(f"  stations done ok={ok} miss={miss}")

    if frames:
        all_df = pd.concat(frames, ignore_index=True)
        all_path = out / "italy_stations_daily_2015_present.csv"
        all_df.to_csv(all_path, index=False)
        log(f"  wrote {all_path.name} rows={len(all_df)} stations={ok}")
    (out / "README.txt").write_text(
        "Meteostat bulk daily observations for Italy stations.\n"
        "prcp=mm precipitation, snow=mm snow depth equiv, tavg/tmin/tmax °C, wspd km/h.\n"
        "https://dev.meteostat.net/\n",
        encoding="utf-8",
    )


def update_readme() -> None:
    readme = ROOT / "README.md"
    extra = (
        "\n## Alternative sources (no Open-Meteo)\n\n"
        "When Open-Meteo returns 429, use NASA POWER + Meteostat:\n\n"
        "```powershell\n"
        "python db/meteo-italia/scripts/harvest_meteo_alt.py\n"
        "```\n\n"
        "| Path | Cosa |\n"
        "|------|------|\n"
        "| `sources/nasa_power_grid/` | Griglia nazionale daily (~1°) precip/temp/vento/solare |\n"
        "| `sources/nasa_power_cities/` | 12 città daily |\n"
        "| `sources/nasa_power_zones/` | 7 zone ENTSO daily |\n"
        "| `sources/meteostat_stations/` | Stazioni osservative IT daily |\n"
    )
    if readme.exists():
        t = readme.read_text(encoding="utf-8")
        if "nasa_power_grid" not in t:
            readme.write_text(t + extra, encoding="utf-8")


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-power", action="store_true")
    ap.add_argument("--skip-meteostat", action="store_true")
    args = ap.parse_args()
    if not args.skip_power:
        harvest_nasa_power()
    if not args.skip_meteostat:
        harvest_meteostat()
    update_readme()
    log("DONE meteo alt (NASA POWER + Meteostat)")


if __name__ == "__main__":
    main()
