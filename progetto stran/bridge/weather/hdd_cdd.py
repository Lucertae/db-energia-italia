"""HDD/CDD weighted aggregates from Open-Meteo cache → energy demand proxy."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.weather.io import load_weather_manifest
from bridge.spine_io import ROOT


def _hdd_cdd(daily_mean_c: float, hdd_base: float, cdd_base: float) -> tuple[float, float]:
    hdd = max(0.0, hdd_base - daily_mean_c)
    cdd = max(0.0, daily_mean_c - cdd_base)
    return hdd, cdd


def _zone_metrics(path: Path, hdd_base: float, cdd_base: float) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    daily = data.get("archive", {})
    temps = daily.get("temperature_2m_mean") or []
    times = daily.get("time") or []
    fc = data.get("forecast", {})
    fc_temps = fc.get("temperature_2m_mean") or []
    fc_winds = fc.get("windspeed_10m_max") or fc.get("wind_speed_10m_max") or []

    hdds: list[float] = []
    cdds: list[float] = []
    winds: list[float] = []
    rads: list[float] = []

    if len(temps) < 3 and fc_temps:
        for t in fc_temps:
            if t is None:
                continue
            h, c = _hdd_cdd(float(t), hdd_base, cdd_base)
            hdds.append(h)
            cdds.append(c)
        times = fc.get("time") or []
    else:
        for i, t in enumerate(temps):
            if t is None:
                continue
            h, c = _hdd_cdd(float(t), hdd_base, cdd_base)
            hdds.append(h)
            cdds.append(c)
            wlist = daily.get("windspeed_10m_max") or daily.get("wind_speed_10m_max") or []
            if i < len(wlist) and wlist[i] is not None:
                winds.append(float(wlist[i]))
            rlist = daily.get("shortwave_radiation_sum") or []
            if i < len(rlist) and rlist[i] is not None:
                rads.append(float(rlist[i]))

    if len(hdds) < 3:
        return None

    recent_hdd = sum(hdds[-7:]) / min(7, len(hdds))
    recent_cdd = sum(cdds[-7:]) / min(7, len(cdds))
    hist_hdd = sum(hdds[:-7]) / max(1, len(hdds) - 7) if len(hdds) > 7 else recent_hdd
    hist_cdd = sum(cdds[:-7]) / max(1, len(cdds) - 7) if len(cdds) > 7 else recent_cdd

    wind_fc_mean = sum(float(x) for x in fc_winds if x is not None) / max(1, len(fc_winds))
    temp_fc_mean = sum(float(x) for x in fc_temps if x is not None) / max(1, len(fc_temps))

    return {
        "zone_id": data.get("zone_id"),
        "last_date": times[-1] if times else None,
        "hdd_7d": round(recent_hdd, 2),
        "cdd_7d": round(recent_cdd, 2),
        "hdd_anom": round(recent_hdd - hist_hdd, 2),
        "cdd_anom": round(recent_cdd - hist_cdd, 2),
        "wind_fc_mean_ms": round(wind_fc_mean, 2),
        "temp_fc_mean_c": round(temp_fc_mean, 1),
        "solar_proxy_wh_m2": round(sum(rads[-7:]) / max(1, len(rads[-7:])), 0) if rads else None,
    }


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    manifest = load_weather_manifest(base)
    hdd_base = float(manifest.get("hdd_base_c", 18.0))
    cdd_base = float(manifest.get("cdd_base_c", 22.0))
    om_dir = base / "cache" / "weather" / "open_meteo"

    regions: dict[str, dict[str, float]] = {}
    zones: list[dict[str, Any]] = []

    for zone in manifest.get("zones", []):
        zid = zone.get("id", "?")
        m = _zone_metrics(om_dir / f"{zid}.json", hdd_base, cdd_base)
        if not m:
            continue
        m["power_desk"] = zone.get("power_desk")
        m["fx_pairs"] = zone.get("fx_pairs", [])
        m["weight_hdd"] = zone.get("weight_hdd", 0.0)
        m["weight_cdd"] = zone.get("weight_cdd", 0.0)
        zones.append(m)

        region = zone.get("region", "OTHER")
        reg = regions.setdefault(region, {"hdd_w": 0.0, "cdd_w": 0.0, "hdd_w_sum": 0.0, "cdd_w_sum": 0.0})
        wh = float(zone.get("weight_hdd", 0.0))
        wc = float(zone.get("weight_cdd", 0.0))
        reg["hdd_w"] += m["hdd_anom"] * wh
        reg["cdd_w"] += m["cdd_anom"] * wc
        reg["hdd_w_sum"] += wh
        reg["cdd_w_sum"] += wc

    region_summary = []
    for rid, r in regions.items():
        hws = r["hdd_w_sum"] or 1.0
        cws = r["cdd_w_sum"] or 1.0
        region_summary.append({
            "region": rid,
            "hdd_anom_weighted": round(r["hdd_w"] / hws, 2),
            "cdd_anom_weighted": round(r["cdd_w"] / cws, 2),
        })

    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hdd_base_c": hdd_base,
        "cdd_base_c": cdd_base,
        "zones": zones,
        "regions": region_summary,
    }

    out_path = base / "cache" / "spine" / "modules" / "weather_hdd_cdd.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    eu = next((r for r in region_summary if r["region"] == "EU"), None)
    msg = f"{len(zones)} zones"
    if eu:
        msg += f" EU hdd_anom={eu['hdd_anom_weighted']:+.1f}"

    return {
        "ok": len(zones) > 0,
        "module": "weather_hdd_cdd",
        "message": msg,
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
