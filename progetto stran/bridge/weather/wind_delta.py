"""Wind forecast delta: multi-grid OM fleet MW vs ENTSO-E published (PWR-01 v2 live)."""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bridge.energy.capacity import capacity_mw_for_hour
from bridge.energy.entsoe_util import load_power_wind_config
from bridge.energy.gate import gate_hour_key
from bridge.energy.power_curve import delta_norm, wind_to_mw
from bridge.energy.wind_grid import load_grid_wind_hourly
from bridge.spine_io import ROOT, read_fred_csv


def _gate_wind_from_forecast(base: Path, grid_points: list[dict[str, Any]], gate_hk: str) -> float | None:
    """Weighted hourly forecast wind (m/s) at gate bucket from per-point JSON."""
    if not grid_points:
        return None
    w_sum = sum(float(p.get("weight", 1)) for p in grid_points)
    if w_sum <= 0:
        return None
    vals: list[tuple[float, float]] = []
    for pt in grid_points:
        pid = str(pt["id"])
        w = float(pt.get("weight", 1)) / w_sum
        p = base / "cache" / "weather" / "open_meteo" / f"{pid}.json"
        if not p.is_file():
            continue
        data = json.loads(p.read_text(encoding="utf-8"))
        fc = data.get("forecast", {})
        times = fc.get("time", [])
        winds = fc.get("windspeed_10m", [])
        if not times:
            continue
        for ts, ws in zip(times, winds):
            if ws is None:
                continue
            hk = str(ts)[:13].replace(" ", "T")
            if hk == gate_hk:
                vals.append((w, float(ws)))
                break
    if vals:
        return sum(w * v for w, v in vals)
    return None


def _forecast_wind_ms(
    base: Path,
    desk_id: str,
    grid_points: list[dict[str, Any]],
    *,
    legacy_zone: str | None = None,
    gate_hk: str | None = None,
) -> float | None:
    if gate_hk and grid_points:
        gw = _gate_wind_from_forecast(base, grid_points, gate_hk)
        if gw is not None:
            return gw
    hourly = load_grid_wind_hourly(base, desk_id, grid_points, legacy_zone=legacy_zone)
    if hourly:
        key = gate_hk if gate_hk and gate_hk in hourly else sorted(hourly.keys())[-1]
        return hourly[key]
    return None


def _published_wind_mw(base: Path, desk_id: str) -> float | None:
    rows = read_fred_csv(base / "cache" / "weather" / "entsoe_wind" / f"{desk_id}.csv")
    return rows[-1][1] if rows else None


def _published_wind_mw_hourly(base: Path, desk_id: str, gate_hk: str) -> float | None:
    d = base / "cache" / "weather" / "entsoe_hourly" / "wind_published" / desk_id
    if not d.is_dir():
        return _published_wind_mw(base, desk_id)
    for path in sorted(d.glob("*.json"), reverse=True):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for ts, v in zip(data.get("timestamps", []), data.get("wind_mw", [])):
            if v is None:
                continue
            hk = str(ts)[:13].replace(" ", "T")
            if hk == gate_hk:
                return float(v)
    return _published_wind_mw(base, desk_id)


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    pcfg = load_power_wind_config(base)
    bt = pcfg.get("backtest", {})
    fleet_cfg = bt.get("fleet_curve", {})
    gate_cfg = bt.get("gate", {"enabled": True, "hour_utc": 10, "minute_utc": 30})
    gate_hour = int(gate_cfg.get("hour_utc", 10))
    gate_minute = int(gate_cfg.get("minute_utc", 30))
    deltas: list[dict[str, Any]] = []

    now = datetime.now(timezone.utc)
    next_delivery = (now + timedelta(days=1)).strftime("%Y-%m-%dT%H")
    gate_hk = gate_hour_key(next_delivery, gate_hour_utc=gate_hour, gate_minute_utc=gate_minute)

    for desk_id, desk_cfg in pcfg.get("desks", {}).items():
        grid = desk_cfg.get("grid_points", [])
        legacy = desk_cfg.get("om_legacy_zone")
        om_ms = _forecast_wind_ms(
            base, desk_id, grid, legacy_zone=legacy, gate_hk=gate_hk,
        )
        pub_mw = _published_wind_mw_hourly(base, desk_id, gate_hk)
        if om_ms is None or pub_mw is None:
            continue
        country = str(desk_cfg.get("country", ""))
        cap_fb = float(desk_cfg.get("capacity_mw_fallback", 65000))
        cap = capacity_mw_for_hour(base, country, gate_hk, cap_fb)
        om_mw = wind_to_mw(
            om_ms, cap,
            cut_in_ms=float(fleet_cfg.get("cut_in_ms", 3)),
            rated_ms=float(fleet_cfg.get("rated_ms", 12)),
            cut_out_ms=float(fleet_cfg.get("cut_out_ms", 25)),
            fleet=True,
            smooth_sigma_ms=float(fleet_cfg.get("smooth_sigma_ms", 2)),
        )
        d_norm = delta_norm(om_mw, pub_mw, cap)
        deltas.append({
            "desk": desk_id,
            "zone": f"{len(grid)}-grid",
            "gate_hour_utc": gate_hk,
            "delivery_hour_utc": next_delivery,
            "delta_norm": round(d_norm, 5),
            "om_wind_ms": round(om_ms, 2),
            "om_mw_proxy": round(om_mw, 1),
            "pub_wind_mw": round(pub_mw, 1),
            "capacity_mw": round(cap, 0),
            "alert": abs(d_norm) > 0.02,
            "hypothesis": "delta_norm>0 → intraday/imb−DA ↓ at delivery (gate D-1)",
            "signal_id": "PWR-01-v2",
        })

    payload = {
        "built_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "method": f"multi-grid OM + fleet CF − published / capacity @ gate {gate_hk}",
        "deltas": deltas,
    }
    out_path = base / "cache" / "spine" / "modules" / "weather_wind_delta.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    alerts = sum(1 for d in deltas if d.get("alert"))
    return {
        "ok": len(deltas) > 0,
        "module": "weather_wind_delta",
        "message": f"{len(deltas)} desks {alerts} v2 alerts gate={gate_hk}",
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
