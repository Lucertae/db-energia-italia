"""Load weather_manifest.json and shared helpers."""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from bridge.spine_io import ROOT


def load_weather_manifest(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    path = base / "config" / "weather_manifest.json"
    if not path.is_file():
        return {"zones": []}
    return json.loads(path.read_text(encoding="utf-8"))


def http_get_json(url: str, timeout: int = 60) -> dict[str, Any]:
    req = urllib.request.Request(url, headers={"User-Agent": "ops-desk-weather/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def open_meteo_archive(
    lat: float, lon: float, start: date, end: date
) -> dict[str, Any]:
    params = urllib.parse.urlencode({
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "daily": "temperature_2m_mean,windspeed_10m_max,shortwave_radiation_sum,precipitation_sum",
        "timezone": "UTC",
    })
    url = f"https://archive-api.open-meteo.com/v1/archive?{params}"
    return http_get_json(url)


def open_meteo_hourly_archive(
    lat: float, lon: float, start: date, end: date
) -> dict[str, Any]:
    """Hourly wind for power-curve MW proxy (PWR-01 v2 backtest)."""
    params = urllib.parse.urlencode({
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "hourly": "windspeed_10m",
        "timezone": "UTC",
    })
    url = f"https://archive-api.open-meteo.com/v1/archive?{params}"
    return http_get_json(url)


def open_meteo_forecast(lat: float, lon: float, days: int = 7) -> dict[str, Any]:
    params = urllib.parse.urlencode({
        "latitude": f"{lat:.4f}",
        "longitude": f"{lon:.4f}",
        "daily": "temperature_2m_mean,windspeed_10m_max,shortwave_radiation_sum,precipitation_sum",
        "forecast_days": str(days),
        "timezone": "UTC",
    })
    url = f"https://api.open-meteo.com/v1/forecast?{params}"
    return http_get_json(url)


def date_range_days(n: int, lag_days: int = 5) -> tuple[date, date]:
    end = date.today() - timedelta(days=lag_days)
    start = end - timedelta(days=n)
    return start, end
