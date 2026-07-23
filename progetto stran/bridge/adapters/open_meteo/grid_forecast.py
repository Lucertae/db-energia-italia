"""Open-Meteo hourly forecast for power_wind.json grid points (live PWR-01 v2)."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.energy.entsoe_util import load_power_wind_config
from bridge.spine_io import ROOT
from bridge.weather.io import http_get_json


def _fetch_hourly_forecast(lat: float, lon: float, days: int = 2) -> dict[str, Any]:
    params = urllib.parse.urlencode({
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "hourly": "windspeed_10m",
        "forecast_days": str(days),
        "timezone": "UTC",
    })
    url = f"https://api.open-meteo.com/v1/forecast?{params}"
    return http_get_json(url)


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    pcfg = load_power_wind_config(base)
    out_dir = base / "cache" / "weather" / "open_meteo"
    out_dir.mkdir(parents=True, exist_ok=True)
    ok = 0
    errors: list[str] = []

    for desk_id, desk in pcfg.get("desks", {}).items():
        for pt in desk.get("grid_points", []):
            pid = str(pt["id"])
            lat, lon = float(pt["lat"]), float(pt["lon"])
            try:
                raw = _fetch_hourly_forecast(lat, lon)
                hourly = raw.get("hourly", {})
                payload = {
                    "zone_id": pid,
                    "desk_id": desk_id,
                    "lat": lat,
                    "lon": lon,
                    "weight": pt.get("weight"),
                    "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "forecast": {
                        "time": hourly.get("time", []),
                        "windspeed_10m": hourly.get("windspeed_10m", []),
                    },
                }
                (out_dir / f"{pid}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
                ok += 1
            except Exception as exc:
                errors.append(f"{pid}:{exc}")

    summary = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "grid_points_ok": ok,
        "errors": errors[:10],
    }
    out_path = base / "cache" / "spine" / "modules" / "om_grid_forecast.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return {
        "ok": ok > 0,
        "module": "om_grid_forecast",
        "message": f"grid forecast {ok} points",
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
