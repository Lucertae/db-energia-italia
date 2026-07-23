#!/usr/bin/env python3
"""
Harvest ENTSO-E Transparency Platform — all available series for Italy.

Saves CSV under data/<dataset>/<zone>/<year>.csv
Logs status to logs/harvest_manifest.jsonl
"""
from __future__ import annotations

import json
import time
import traceback
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests
from entsoe import EntsoePandasClient
from entsoe.exceptions import NoMatchingDataError, InvalidBusinessParameterError

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
LOGS = ROOT / "logs"
KEY_FILE = ROOT / "entsoe.key"

# Italy country + bidding zones (EIC)
ZONES = {
    "IT": "10YIT-GRTN-----B",
    "IT-North": "10Y1001A1001A73I",
    "IT-Centre-North": "10Y1001A1001A70O",
    "IT-Centre-South": "10Y1001A1001A71M",
    "IT-South": "10Y1001A1001A788",
    "IT-Sicily": "10Y1001A1001A74G",
    "IT-Sardinia": "10Y1001A1001A75E",
    "IT-Calabria": "10Y1001C--00096J",
}

# Neighbours for cross-border / NTC / scheduled exchanges
NEIGHBOURS = {
    "FR": "10YFR-RTE------C",
    "CH": "10YCH-SWISSGRIDZ",
    "AT": "10YAT-APG------L",
    "SI": "10YSI-ELES-----O",
    "GR": "10YGR-HTSO-----Y",
    "MT": "10Y1001A1001A93C",
    "ME": "10YCS-CG-TSO---S",
}

START_YEAR = 2015
TZ = "Europe/Rome"

# Balancing — ENTSO-E document variants (see entsoe.mappings)
ACTIVATED_ENERGY_BUSINESS_TYPES = ("A95", "A96", "A97", "A98")  # FCR, aFRR, mFRR, RR
PROCURED_PROCESS_TYPES = ("A51", "A52", "A47")  # aFRR, FCR, mFRR
CONTRACTED_PROCESS_TYPES = ("A51", "A52", "A47", "A46", "A60", "A61", "A67", "A68")
MARKET_AGREEMENT_TYPES = ("A01", "A02", "A03", "A04", "A06", "A13")  # A05/A07 often 400 on A15
ACTIVATED_PRICES_PROCESS_TYPES = ("A16", "A60", "A61", "A67", "A68")  # A51/A52/A47 → 400 on A84


def load_key() -> str:
    return KEY_FILE.read_text(encoding="utf-8").strip()


def year_windows(start_year: int = START_YEAR):
    now = pd.Timestamp.now(tz=TZ)
    for y in range(start_year, now.year + 1):
        s = pd.Timestamp(f"{y}-01-01", tz=TZ)
        e = pd.Timestamp(f"{y+1}-01-01", tz=TZ)
        if e > now:
            e = now.floor("h") + pd.Timedelta(hours=1)
        if s >= e:
            continue
        yield y, s, e


def save_df(df: pd.DataFrame | pd.Series, path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(df, pd.Series):
        out = df.to_frame(name=df.name or "value")
    else:
        out = df
    if out is None or out.empty:
        return 0
    out.to_csv(path)
    return int(len(out))


def log_event(fp, **kw):
    kw["ts"] = datetime.utcnow().isoformat() + "Z"
    fp.write(json.dumps(kw, ensure_ascii=False) + "\n")
    fp.flush()
    print(f"{kw.get('status','?'):7} {kw.get('dataset','')} {kw.get('zone','')} {kw.get('year','')} {kw.get('rows', kw.get('error',''))}", flush=True)


def call(
    client,
    name: str,
    fn,
    out_path: Path,
    logfp,
    zone: str,
    year: int,
    sleep_s: float = 1.0,
    retry_empty: bool = False,
):
    if out_path.exists():
        sz = out_path.stat().st_size
        if sz > 50:
            log_event(logfp, status="skip", dataset=name, zone=zone, year=year, path=str(out_path))
            return "skip"
        if sz == 0 and not retry_empty:
            log_event(logfp, status="skip_empty", dataset=name, zone=zone, year=year, path=str(out_path))
            return "skip_empty"
    try:
        df = fn()
        n = save_df(df, out_path)
        log_event(logfp, status="ok", dataset=name, zone=zone, year=year, rows=n, path=str(out_path))
        time.sleep(sleep_s)
        return "ok"
    except NoMatchingDataError:
        log_event(logfp, status="empty", dataset=name, zone=zone, year=year)
        # touch empty marker so we don't retry forever
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("", encoding="utf-8")
        time.sleep(0.3)
        return "empty"
    except InvalidBusinessParameterError as e:
        log_event(logfp, status="invalid", dataset=name, zone=zone, year=year, error=str(e)[:300])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("", encoding="utf-8")
        time.sleep(0.3)
        return "invalid"
    except requests.HTTPError as e:
        log_event(logfp, status="invalid", dataset=name, zone=zone, year=year, error=str(e)[:300])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text("", encoding="utf-8")
        time.sleep(0.3)
        return "invalid"
    except Exception as e:
        log_event(
            logfp,
            status="error",
            dataset=name,
            zone=zone,
            year=year,
            error=str(e)[:500],
            trace=traceback.format_exc()[-800:],
        )
        time.sleep(1.5)
        return "error"


def harvest_balancing(client, logfp, retry_empty: bool = False, sleep_s: float = 1.0):
    """Harvest all IT balancing series with required ENTSO-E parameter variants."""
    z = ZONES["IT"]
    base = DATA / "IT" / "balancing"

    for year, start, end in year_windows():
        for bt in ACTIVATED_ENERGY_BUSINESS_TYPES:
            ds = f"activated_balancing_energy/{bt}"
            call(
                client,
                ds,
                lambda s=start, e=end, bt=bt: client.query_activated_balancing_energy(
                    z, start=s, end=e, business_type=bt
                ),
                base / "activated_balancing_energy" / bt / f"{year}.csv",
                logfp,
                "IT",
                year,
                sleep_s=sleep_s,
                retry_empty=retry_empty,
            )

        for pt in ACTIVATED_PRICES_PROCESS_TYPES:
            if pt == "A16":
                out = base / "activated_balancing_energy_prices" / f"{year}.csv"
            else:
                out = base / "activated_balancing_energy_prices" / pt / f"{year}.csv"
            ds = f"activated_balancing_energy_prices/{pt}"
            call(
                client,
                ds,
                lambda s=start, e=end, pt=pt: client.query_activated_balancing_energy_prices(
                    z, start=s, end=e, process_type=pt
                ),
                out,
                logfp,
                "IT",
                year,
                sleep_s=sleep_s,
                retry_empty=retry_empty,
            )

        for pt in PROCURED_PROCESS_TYPES:
            ds = f"procured_balancing_capacity/{pt}/all"
            call(
                client,
                ds,
                lambda s=start, e=end, pt=pt: client.query_procured_balancing_capacity(
                    z, process_type=pt, start=s, end=e
                ),
                base / "procured_balancing_capacity" / pt / "all" / f"{year}.csv",
                logfp,
                "IT",
                year,
                sleep_s=sleep_s,
                retry_empty=retry_empty,
            )
            for mt in MARKET_AGREEMENT_TYPES:
                ds = f"procured_balancing_capacity/{pt}/{mt}"
                call(
                    client,
                    ds,
                    lambda s=start, e=end, pt=pt, mt=mt: client.query_procured_balancing_capacity(
                        z, process_type=pt, start=s, end=e, type_marketagreement_type=mt
                    ),
                    base / "procured_balancing_capacity" / pt / mt / f"{year}.csv",
                    logfp,
                    "IT",
                    year,
                    sleep_s=sleep_s,
                    retry_empty=retry_empty,
                )

        for pt in CONTRACTED_PROCESS_TYPES:
            for mt in MARKET_AGREEMENT_TYPES:
                tag = f"{pt}_{mt}"
                for ds_name, fn in (
                    (
                        "contracted_reserve_amount",
                        lambda s=start, e=end, pt=pt, mt=mt: client.query_contracted_reserve_amount(
                            z, process_type=pt, type_marketagreement_type=mt, start=s, end=e
                        ),
                    ),
                    (
                        "contracted_reserve_prices",
                        lambda s=start, e=end, pt=pt, mt=mt: client.query_contracted_reserve_prices(
                            z, process_type=pt, type_marketagreement_type=mt, start=s, end=e
                        ),
                    ),
                ):
                    ds = f"{ds_name}/{tag}"
                    call(
                        client,
                        ds,
                        fn,
                        base / ds_name / tag / f"{year}.csv",
                        logfp,
                        "IT",
                        year,
                        sleep_s=sleep_s,
                        retry_empty=retry_empty,
                    )


def main():
    DATA.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    key = load_key()
    if not key:
        raise SystemExit("Missing entsoe.key")

    client = EntsoePandasClient(api_key=key)
    log_path = LOGS / f"harvest_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.jsonl"
    print(f"ENTSO-E harvest Italia -> {DATA}")
    print(f"log: {log_path}")

    with log_path.open("a", encoding="utf-8") as logfp:
        # ---- Per-zone time series ----
        for zone_name, eic in ZONES.items():
            for year, start, end in year_windows():
                base = DATA / zone_name

                jobs = [
                    ("load", lambda s=start, e=end, z=eic: client.query_load(z, start=s, end=e)),
                    ("load_forecast", lambda s=start, e=end, z=eic: client.query_load_forecast(z, start=s, end=e)),
                    ("generation", lambda s=start, e=end, z=eic: client.query_generation(z, start=s, end=e)),
                    ("generation_forecast", lambda s=start, e=end, z=eic: client.query_generation_forecast(z, start=s, end=e)),
                    ("wind_solar_forecast", lambda s=start, e=end, z=eic: client.query_wind_and_solar_forecast(z, start=s, end=e)),
                    ("intraday_wind_solar_forecast", lambda s=start, e=end, z=eic: client.query_intraday_wind_and_solar_forecast(z, start=s, end=e)),
                    ("net_position", lambda s=start, e=end, z=eic: client.query_net_position(z, start=s, end=e)),
                    ("imbalance_prices", lambda s=start, e=end, z=eic: client.query_imbalance_prices(z, start=s, end=e)),
                    ("imbalance_volumes", lambda s=start, e=end, z=eic: client.query_imbalance_volumes(z, start=s, end=e)),
                    ("installed_capacity", lambda s=start, e=end, z=eic: client.query_installed_generation_capacity(z, start=s, end=e)),
                    ("installed_capacity_per_unit", lambda s=start, e=end, z=eic: client.query_installed_generation_capacity_per_unit(z, start=s, end=e)),
                    ("hydro_reservoirs", lambda s=start, e=end, z=eic: client.query_aggregate_water_reservoirs_and_hydro_storage(z, start=s, end=e)),
                    ("day_ahead_prices", lambda s=start, e=end, z=eic: client.query_day_ahead_prices(z, start=s, end=e)),
                ]

                # Intraday prices: API requires sequence (1..)
                for seq in (1, 2, 3):
                    jobs.append(
                        (
                            f"intraday_prices_seq{seq}",
                            lambda s=start, e=end, z=eic, seq=seq: client.query_intraday_prices(
                                z, start=s, end=e, sequence=seq
                            ),
                        )
                    )

                # Unavailability only (generation_per_plant skipped: hangs / unstable on yearly chunks)
                if zone_name == "IT":
                    jobs += [
                        ("unavailability_generation_units", lambda s=start, e=end, z=eic: client.query_unavailability_of_generation_units(z, start=s, end=e)),
                        ("unavailability_production_units", lambda s=start, e=end, z=eic: client.query_unavailability_of_production_units(z, start=s, end=e)),
                    ]

                for ds, fn in jobs:
                    call(client, ds, fn, base / ds / f"{year}.csv", logfp, zone_name, year)

        # generation_per_plant: monthly chunks (yearly requests hang)
        for year, y_start, y_end in year_windows():
            cur = y_start
            while cur < y_end:
                nxt = min(cur + pd.DateOffset(months=1), y_end)
                mlabel = f"{cur.year}-{cur.month:02d}"
                call(
                    client,
                    "generation_per_plant",
                    lambda s=cur, e=nxt, z=ZONES["IT"]: client.query_generation_per_plant(z, start=s, end=e),
                    DATA / "IT" / "generation_per_plant" / f"{mlabel}.csv",
                    logfp,
                    "IT",
                    mlabel,
                    sleep_s=1.2,
                )
                cur = nxt

        # ---- Cross-border with neighbours (from/to IT country) ----
        it = ZONES["IT"]
        for nb_name, nb_eic in NEIGHBOURS.items():
            for year, start, end in year_windows():
                pair = f"IT__{nb_name}"
                base = DATA / "crossborder" / pair
                jobs = [
                    (
                        "physical_flows",
                        lambda s=start, e=end, a=it, b=nb_eic: client.query_crossborder_flows(a, b, start=s, end=e),
                    ),
                    (
                        "scheduled_exchanges",
                        lambda s=start, e=end, a=it, b=nb_eic: client.query_scheduled_exchanges(a, b, start=s, end=e),
                    ),
                    (
                        "ntc_dayahead",
                        lambda s=start, e=end, a=it, b=nb_eic: client.query_net_transfer_capacity_dayahead(a, b, start=s, end=e),
                    ),
                    (
                        "ntc_weekahead",
                        lambda s=start, e=end, a=it, b=nb_eic: client.query_net_transfer_capacity_weekahead(a, b, start=s, end=e),
                    ),
                    (
                        "ntc_monthahead",
                        lambda s=start, e=end, a=it, b=nb_eic: client.query_net_transfer_capacity_monthahead(a, b, start=s, end=e),
                    ),
                    (
                        "ntc_yearahead",
                        lambda s=start, e=end, a=it, b=nb_eic: client.query_net_transfer_capacity_yearahead(a, b, start=s, end=e),
                    ),
                    (
                        "unavailability_transmission",
                        lambda s=start, e=end, a=it, b=nb_eic: client.query_unavailability_transmission(a, b, start=s, end=e),
                    ),
                ]
                for ds, fn in jobs:
                    call(client, ds, fn, base / ds / f"{year}.csv", logfp, pair, year)

                # reverse physical flows
                call(
                    client,
                    "physical_flows_rev",
                    lambda s=start, e=end, a=nb_eic, b=it: client.query_crossborder_flows(a, b, start=s, end=e),
                    DATA / "crossborder" / f"{nb_name}__IT" / "physical_flows" / f"{year}.csv",
                    logfp,
                    f"{nb_name}__IT",
                    year,
                )

        harvest_balancing(client, logfp)

        log_event(logfp, status="done", dataset="ALL", zone="IT", year=0)

    # write summary
    summary = {
        "finished_at": datetime.utcnow().isoformat() + "Z",
        "data_root": str(DATA),
        "zones": ZONES,
        "neighbours": NEIGHBOURS,
        "start_year": START_YEAR,
        "csv_files": len(list(DATA.rglob("*.csv"))),
        "bytes": sum(p.stat().st_size for p in DATA.rglob("*") if p.is_file()),
    }
    (ROOT / "harvest_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("DONE", summary)


if __name__ == "__main__":
    main()
