"""Harvest ENTSO-E published wind+solar generation forecast (MW) by zone."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.deps import try_import
from bridge.spine_io import ROOT


# desk_id → ENTSO-E country / area code for query_wind_and_solar_forecast
WIND_ZONES: dict[str, str] = {
    "PDE": "DE",
    "PFR": "FR",
    "PIT": "IT",
    "PNL": "NL",
    "PPL": "PL",
}


def _load_token(cache: Path) -> str:
    for env in ("ENTSOE_API_TOKEN", "HEDGE_ENTSOE_TOKEN"):
        v = os.environ.get(env, "").strip()
        if v:
            return v
    key_file = cache / "entsoe.key"
    if key_file.is_file():
        return key_file.read_text(encoding="utf-8").strip()
    return ""


def _save_daily_csv(path: Path, desk_id: str, daily: dict[str, float]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows: dict[str, float] = {}
    if path.is_file():
        for line in path.read_text(encoding="utf-8").splitlines()[1:]:
            if "," not in line:
                continue
            d, v = line.split(",", 1)
            try:
                rows[d.strip()] = float(v)
            except ValueError:
                continue
    rows.update(daily)
    days = sorted(rows.keys())[-800:]
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write(f"DATE,{desk_id}_WIND_MW\n")
        for d in days:
            f.write(f"{d},{rows[d]:.4f}\n")
    return len(days)


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    cache = base / "cache"
    token = _load_token(cache)
    out_dir = cache / "weather" / "entsoe_wind"
    log: list[str] = []
    ok = 0

    if not token or try_import("entsoe") is None:
        payload = {
            "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ok": False,
            "zones_ok": 0,
            "log": ["no token or entsoe-py missing"],
        }
        out_path = base / "cache" / "spine" / "modules" / "entsoe_wind_forecast.json"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {
            "ok": False,
            "module": "entsoe_wind_forecast",
            "message": payload["log"][0],
            "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
        }

    import pandas as pd

    client = __import__("entsoe").EntsoePandasClient(api_key=token)
    end = pd.Timestamp.now(tz="UTC")
    start = end - pd.Timedelta(days=14)

    for desk_id, area in WIND_ZONES.items():
        try:
            # Published day-ahead wind+solar forecast (MW); sum wind PSR types
            series = client.query_wind_and_solar_forecast(area, start=start, end=end)
            if series is None or len(series) == 0:
                log.append(f"{desk_id}: empty")
                continue
            if isinstance(series, pd.DataFrame):
                # columns may be Solar/Wind Onshore/Wind Offshore
                wind_cols = [c for c in series.columns if "Wind" in str(c)]
                if wind_cols:
                    s = series[wind_cols].sum(axis=1)
                else:
                    s = series.sum(axis=1)
            else:
                s = series
            daily = s.resample("D").mean().dropna()
            daily_map = {idx.strftime("%Y-%m-%d"): float(v) for idx, v in daily.items()}
            n = _save_daily_csv(out_dir / f"{desk_id}.csv", desk_id, daily_map)
            ok += 1
            log.append(f"{desk_id}: {len(daily_map)}d ({n} total)")
        except Exception as exc:
            log.append(f"{desk_id}: {exc}")

    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "zones_ok": ok,
        "log": log,
        "out_dir": "cache/weather/entsoe_wind",
    }
    out_path = base / "cache" / "spine" / "modules" / "entsoe_wind_forecast.json"
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "ok": ok > 0,
        "module": "entsoe_wind_forecast",
        "message": f"wind fc {ok}/{len(WIND_ZONES)} zones",
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
