"""Hourly ENTSO-E harvest: published wind fc, DA prices, imbalance (for PWR-01 v2)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from bridge.energy.entsoe_util import load_power_wind_config, pandas_client
from bridge.spine_io import ROOT


START_BACKFILL = pd.Timestamp("2021-01-01", tz="UTC")
CHUNK_DAYS = 28
MAX_CHUNKS_PER_RUN = 8


def _month_key(ts: pd.Timestamp) -> str:
    return ts.strftime("%Y-%m")


def _cache_dir(base: Path, kind: str) -> Path:
    d = base / "cache" / "weather" / "entsoe_hourly" / kind
    d.mkdir(parents=True, exist_ok=True)
    return d


def _existing_months(desk_dir: Path) -> set[str]:
    if not desk_dir.is_dir():
        return set()
    return {p.stem for p in desk_dir.glob("*.json") if p.stem != "manifest"}


def _save_month(desk_dir: Path, month: str, payload: dict[str, Any]) -> None:
    (desk_dir / f"{month}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _wind_monthly(client, country: str, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, list]:
    try:
        series = client.query_wind_and_solar_forecast(country, start=start, end=end)
    except Exception:
        return {"timestamps": [], "wind_mw": []}
    if series is None or len(series) == 0:
        return {"timestamps": [], "wind_mw": []}
    if isinstance(series, pd.DataFrame):
        wind_cols = [c for c in series.columns if "Wind" in str(c)]
        s = series[wind_cols].sum(axis=1) if wind_cols else series.sum(axis=1)
    else:
        s = series
    s = s.dropna()
    return {
        "timestamps": [t.isoformat() for t in s.index],
        "wind_mw": [float(v) for v in s.values],
    }


def _da_monthly(client, eic: str, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, list]:
    try:
        series = client.query_day_ahead_prices(eic, start=start, end=end)
    except Exception:
        return {"timestamps": [], "da_eur_mwh": []}
    if series is None or len(series) == 0:
        return {"timestamps": [], "da_eur_mwh": []}
    s = series.dropna()
    return {
        "timestamps": [t.isoformat() for t in s.index],
        "da_eur_mwh": [float(v) for v in s.values],
    }


def _imb_monthly(client, country: str, eic: str, start: pd.Timestamp, end: pd.Timestamp) -> dict[str, list]:
    """Imbalance prices — try ISO country then bidding-zone EIC (IT needs EIC)."""
    for code in (country, eic):
        try:
            series = client.query_imbalance_prices(code, start=start, end=end)
        except Exception:
            continue
        if series is None or len(series) == 0:
            continue
        if isinstance(series, pd.DataFrame):
            long_col = "Long" if "Long" in series.columns else series.columns[0]
            short_col = "Short" if "Short" in series.columns else series.columns[-1]
            s_long = series[long_col].dropna()
            s_short = series[short_col].dropna()
            idx = s_long.index.intersection(s_short.index)
            return {
                "timestamps": [t.isoformat() for t in idx],
                "imb_long": [float(s_long[t]) for t in idx],
                "imb_short": [float(s_short[t]) for t in idx],
                "source_code": code,
            }
        s = series.dropna()
        return {
            "timestamps": [t.isoformat() for t in s.index],
            "imb_long": [float(v) for v in s.values],
            "imb_short": [float(v) for v in s.values],
            "source_code": code,
        }
    return {"timestamps": [], "imb_long": [], "imb_short": []}


def _months_to_fetch(existing: set[str], end: pd.Timestamp) -> list[tuple[pd.Timestamp, pd.Timestamp, str]]:
    out: list[tuple[pd.Timestamp, pd.Timestamp, str]] = []
    cursor = START_BACKFILL
    while cursor < end:
        month_end = (cursor + pd.offsets.MonthEnd(0)).normalize() + pd.Timedelta(days=1)
        if month_end > end:
            month_end = end
        mk = _month_key(cursor)
        if mk not in existing:
            out.append((cursor, month_end, mk))
        cursor = month_end
    return out


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    cfg = load_power_wind_config(base)
    client = pandas_client()
    log: list[str] = []
    chunks_done = 0

    if client is None:
        payload = {
            "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ok": False,
            "log": ["no entsoe token or entsoe-py"],
        }
        out = base / "cache" / "spine" / "modules" / "entsoe_hourly_harvest.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"ok": False, "module": "entsoe_hourly_harvest", "message": payload["log"][0], "outputs": [str(out.relative_to(base)).replace("\\", "/")]}

    end = pd.Timestamp.now(tz="UTC")
    desks_ok = 0

    for desk_id, desk in cfg.get("desks", {}).items():
        country = desk["country"]
        eic = desk["eic"]
        wind_dir = _cache_dir(base, "wind_published") / desk_id
        da_dir = _cache_dir(base, "da") / desk_id
        imb_dir = _cache_dir(base, "imbalance") / desk_id
        wind_dir.mkdir(parents=True, exist_ok=True)
        da_dir.mkdir(parents=True, exist_ok=True)
        imb_dir.mkdir(parents=True, exist_ok=True)

        existing = _existing_months(wind_dir)
        todo = _months_to_fetch(existing, end)[:MAX_CHUNKS_PER_RUN]

        # Imbalance may lag wind/DA — backfill missing imb months independently
        imb_existing = _existing_months(imb_dir)
        imb_todo = _months_to_fetch(imb_existing, end)[:MAX_CHUNKS_PER_RUN]

        seen: set[str] = set()
        for start, chunk_end, mk in todo:
            seen.add(mk)
            try:
                w = _wind_monthly(client, country, start, chunk_end)
                d = _da_monthly(client, eic, start, chunk_end)
                im = _imb_monthly(client, country, eic, start, chunk_end)
                _save_month(wind_dir, mk, {"month": mk, "desk": desk_id, **w})
                _save_month(da_dir, mk, {"month": mk, "desk": desk_id, **d})
                if im["timestamps"]:
                    _save_month(imb_dir, mk, {"month": mk, "desk": desk_id, **im})
                else:
                    _save_month(imb_dir, mk, {
                        "month": mk, "desk": desk_id,
                        "timestamps": [], "imb_long": [], "imb_short": [],
                        "empty": True, "tried": [country, eic],
                    })
                    log.append(f"{desk_id}/{mk}:imb=0 (tried {country}+{eic})")
                chunks_done += 1
                log.append(
                    f"{desk_id}/{mk}: w={len(w['timestamps'])} da={len(d['timestamps'])} "
                    f"imb={len(im['timestamps'])}"
                )
            except Exception as exc:
                log.append(f"{desk_id}/{mk}:ERR {exc}")

        for start, chunk_end, mk in imb_todo:
            if mk in seen:
                continue
            try:
                im = _imb_monthly(client, country, eic, start, chunk_end)
                if im["timestamps"]:
                    _save_month(imb_dir, mk, {"month": mk, "desk": desk_id, **im})
                    chunks_done += 1
                    log.append(f"{desk_id}/{mk}:imb-only={len(im['timestamps'])} via {im.get('source_code')}")
                else:
                    _save_month(imb_dir, mk, {
                        "month": mk, "desk": desk_id,
                        "timestamps": [], "imb_long": [], "imb_short": [],
                        "empty": True, "tried": [country, eic],
                    })
            except Exception as exc:
                log.append(f"{desk_id}/{mk}:imb-ERR {exc}")

        if _existing_months(wind_dir):
            desks_ok += 1

    manifest = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "desks": list(cfg.get("desks", {}).keys()),
        "chunks_this_run": chunks_done,
        "backfill_from": START_BACKFILL.isoformat(),
        "log": log[-12:],
    }
    (base / "cache" / "weather" / "entsoe_hourly" / "manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    out_path = base / "cache" / "spine" / "modules" / "entsoe_hourly_harvest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({**manifest, "zones_ok": desks_ok}, indent=2), encoding="utf-8")

    msg = f"hourly {desks_ok} desks +{chunks_done} months"
    return {
        "ok": desks_ok > 0,
        "module": "entsoe_hourly_harvest",
        "message": msg,
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
