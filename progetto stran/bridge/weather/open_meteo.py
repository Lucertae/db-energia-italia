"""Fetch Open-Meteo archive + forecast for manifest zones (stdlib HTTP)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.weather.io import (
    date_range_days,
    load_weather_manifest,
    open_meteo_archive,
    open_meteo_forecast,
)
from bridge.spine_io import ROOT


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    manifest = load_weather_manifest(base)
    out_dir = base / "cache" / "weather" / "open_meteo"
    out_dir.mkdir(parents=True, exist_ok=True)

    start, end = date_range_days(30)
    zones_ok = 0
    errors: list[str] = []

    for zone in manifest.get("zones", []):
        zid = zone.get("id", "?")
        lat, lon = zone.get("lat"), zone.get("lon")
        if lat is None or lon is None:
            continue
        try:
            archive = {}
            try:
                archive = open_meteo_archive(float(lat), float(lon), start, end)
                archive = archive.get("daily", {})
            except Exception:
                archive = {}
            forecast = open_meteo_forecast(float(lat), float(lon), 7)
            payload = {
                "zone_id": zid,
                "name": zone.get("name"),
                "lat": lat,
                "lon": lon,
                "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "archive": archive,
                "forecast": forecast.get("daily", {}),
            }
            (out_dir / f"{zid}.json").write_text(
                json.dumps(payload, indent=2), encoding="utf-8"
            )
            zones_ok += 1
        except Exception as exc:
            errors.append(f"{zid}:{exc}")

    summary = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "zones_ok": zones_ok,
        "zones_total": len(manifest.get("zones", [])),
        "errors": errors[:8],
        "out_dir": "cache/weather/open_meteo",
    }
    summary_path = base / "cache" / "spine" / "modules" / "weather_open_meteo.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

    return {
        "ok": zones_ok > 0,
        "module": "weather_open_meteo",
        "message": f"open-meteo {zones_ok}/{len(manifest.get('zones', []))} zones",
        "outputs": [str(summary_path.relative_to(base)).replace("\\", "/")],
    }
