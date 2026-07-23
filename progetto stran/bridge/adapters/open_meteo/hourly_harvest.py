"""Cache Open-Meteo hourly wind for multi-grid power desks (PWR-01 v2)."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bridge.energy.entsoe_util import load_power_wind_config
from bridge.spine_io import ROOT
from bridge.weather.io import open_meteo_hourly_archive


START = date(2021, 1, 1)
CHUNK_DAYS = 30
MAX_CHUNKS_PER_RUN = 12


def _missing_months(zone_dir: Path, end: date) -> list[tuple[date, date, str]]:
    existing = {p.stem for p in zone_dir.glob("*.json")} if zone_dir.is_dir() else set()
    out: list[tuple[date, date, str]] = []
    cursor = START
    while cursor < end:
        mk = cursor.strftime("%Y-%m")
        chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), end)
        if mk not in existing:
            out.append((cursor, chunk_end, mk))
        cursor = chunk_end + timedelta(days=1)
    return out


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    pcfg = load_power_wind_config(base)
    end = date.today()
    log: list[str] = []
    chunks = 0
    points_ok = 0

    for desk_id, desk in pcfg.get("desks", {}).items():
        for pt in desk.get("grid_points", []):
            pid = str(pt["id"])
            lat, lon = float(pt["lat"]), float(pt["lon"])
            zone_dir = base / "cache" / "weather" / "open_meteo_hourly" / desk_id / pid
            todo = _missing_months(zone_dir, end)[:MAX_CHUNKS_PER_RUN]
            got = False
            for start, chunk_end, mk in todo:
                try:
                    raw = open_meteo_hourly_archive(lat, lon, start, chunk_end)
                    hourly = raw.get("hourly", {})
                    payload = {
                        "desk_id": desk_id,
                        "point_id": pid,
                        "lat": lat,
                        "lon": lon,
                        "weight": pt.get("weight"),
                        "month": mk,
                        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "time": hourly.get("time", []),
                        "windspeed_10m": hourly.get("windspeed_10m", []),
                    }
                    zone_dir.mkdir(parents=True, exist_ok=True)
                    (zone_dir / f"{mk}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
                    chunks += 1
                    got = True
                    log.append(f"{desk_id}/{pid}/{mk}:{len(payload['time'])}h")
                except Exception as exc:
                    log.append(f"{desk_id}/{pid}/{mk}:ERR {exc}")
            if got or zone_dir.is_dir() and any(zone_dir.glob("*.json")):
                points_ok += 1

    out_path = base / "cache" / "spine" / "modules" / "om_hourly_harvest.json"
    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "grid_points_ok": points_ok,
        "chunks_this_run": chunks,
        "log": log[-15:],
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "ok": points_ok > 0,
        "module": "om_hourly_harvest",
        "message": f"om grid {points_ok} points +{chunks} months",
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
