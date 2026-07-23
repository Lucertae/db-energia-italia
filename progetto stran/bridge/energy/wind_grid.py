"""Weighted multi-point Open-Meteo wind aggregation for power desks."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def _hour_key(ts: str) -> str:
    try:
        import pandas as pd

        t = pd.Timestamp(ts)
        if t.tzinfo is None:
            t = t.tz_localize("UTC")
        else:
            t = t.tz_convert("UTC")
        return t.strftime("%Y-%m-%dT%H")
    except Exception:
        return str(ts)[:13]


def _load_point_hourly(base: Path, *candidates: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    for d in candidates:
        if not d.is_dir():
            continue
        for path in sorted(d.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            for ts, ws in zip(data.get("time", []), data.get("windspeed_10m", [])):
                if ws is None:
                    continue
                out[_hour_key(str(ts))] = float(ws)
        if out:
            return out
    return out


def load_grid_wind_hourly(
    base: Path,
    desk_id: str,
    grid_points: list[dict[str, Any]],
    *,
    legacy_zone: str | None = None,
) -> dict[str, float]:
    """Weighted mean wind (m/s) per UTC hour across manifest grid points."""
    if not grid_points:
        if legacy_zone:
            return _load_point_hourly(base / "cache" / "weather" / "open_meteo_hourly" / legacy_zone)
        return {}

    w_sum = sum(float(p.get("weight", 1.0)) for p in grid_points)
    if w_sum <= 0:
        return {}

    accum: dict[str, list[tuple[float, float]]] = {}

    for pt in grid_points:
        pid = str(pt.get("id", "pt"))
        w = float(pt.get("weight", 1.0)) / w_sum
        pt_legacy = pt.get("legacy_zone_id") or legacy_zone
        candidates = [
            base / "cache" / "weather" / "open_meteo_hourly" / desk_id / pid,
            base / "cache" / "weather" / "open_meteo_hourly" / pid,
        ]
        if pt_legacy:
            candidates.append(base / "cache" / "weather" / "open_meteo_hourly" / str(pt_legacy))
        hourly = _load_point_hourly(base, *candidates)
        for hk, ws in hourly.items():
            accum.setdefault(hk, []).append((w, ws))

    out: dict[str, float] = {}
    for hk, pairs in accum.items():
        if not pairs:
            continue
        tw = sum(w for w, _ in pairs)
        if tw <= 0:
            continue
        out[hk] = sum(w * v for w, v in pairs) / tw
    return out
