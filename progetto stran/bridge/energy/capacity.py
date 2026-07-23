"""Time-varying wind installed capacity from ENTSO-E cache."""
from __future__ import annotations

import json
from pathlib import Path


def capacity_mw_for_hour(base: Path, country: str, hour_key: str, fallback: float) -> float:
    """Return wind MW for year extracted from hour_key YYYY-MM-DDTHH."""
    path = base / "cache" / "weather" / "entsoe_capacity" / f"{country}.json"
    if not path.is_file():
        return fallback
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        yearly = data.get("wind_mw_by_year", {})
        year = hour_key[:4]
        if year in yearly:
            return float(yearly[year])
        years = sorted(yearly.keys())
        if years:
            # nearest prior year
            prior = [y for y in years if y <= year]
            key = prior[-1] if prior else years[0]
            return float(yearly[key])
    except (json.JSONDecodeError, OSError, ValueError):
        pass
    return fallback
