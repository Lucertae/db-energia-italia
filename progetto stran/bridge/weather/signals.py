"""Combine weather features → energy + FX trading signals."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.weather.io import load_weather_manifest
from bridge.spine_io import ROOT, fred_last, desk_csv_path


def _load_module_json(base: Path, name: str) -> dict[str, Any]:
    p = base / "cache" / "spine" / "modules" / name
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    manifest = load_weather_manifest(base)
    hdd = _load_module_json(base, "weather_hdd_cdd.json")
    enso = _load_module_json(base, "weather_enso.json")

    signals: list[dict[str, Any]] = []

    eu = next((r for r in hdd.get("regions", []) if r.get("region") == "EU"), None)
    bt = _load_module_json(base, "backtest_pwr_signals.json")
    pwr01_validated = bool(bt.get("PWR-01", {}).get("any_desk_passed"))

    if eu:
        hdd_anom = float(eu.get("hdd_anom_weighted", 0.0))
        cdd_anom = float(eu.get("cdd_anom_weighted", 0.0))
        alert = abs(hdd_anom) > 2.0 or abs(cdd_anom) > 2.0
        signals.append({
            "id": "PWR-02",
            "sector": "energy",
            "metric": "eu_hdd_cdd_anom",
            "hdd_anom": hdd_anom,
            "cdd_anom": cdd_anom,
            "alert": alert,
            "msg": f"EU HDD anom {hdd_anom:+.1f} CDD {cdd_anom:+.1f} → gas/power demand",
            "horizon": "daily-weekly",
        })

    us = next((r for r in hdd.get("regions", []) if r.get("region") == "US"), None)
    if us:
        hdd_anom = float(us.get("hdd_anom_weighted", 0.0))
        signals.append({
            "id": "PWR-03",
            "sector": "energy",
            "metric": "us_hdd_anom",
            "value": hdd_anom,
            "alert": hdd_anom > 3.0,
            "msg": f"US HDD anom {hdd_anom:+.1f} → HH gas demand proxy",
            "horizon": "daily-weekly",
        })

    for zone in hdd.get("zones", []):
        if not zone.get("power_desk"):
            continue
        wind = zone.get("wind_fc_mean_ms")
        if wind is None:
            continue
        desk = zone["power_desk"]
        wind_thr = float(manifest.get("wind_ramp_threshold_ms", 8.0))
        alert = float(wind) > wind_thr and pwr01_validated
        if float(wind) > wind_thr:
            signals.append({
                "id": "PWR-01",
                "sector": "energy",
                "metric": "wind_fc_ramp",
                "zone": zone.get("zone_id"),
                "power_desk": desk,
                "wind_fc_ms": wind,
                "alert": alert,
                "msg": f"{desk} wind fc {wind:.1f} m/s → renewable ramp / DA price",
                "horizon": "intraday-daily",
                "validated": pwr01_validated,
                "note": "backtest FAIL — monitor only; use PWR-01b delta" if not pwr01_validated else None,
            })

    wd_path = base / "cache" / "spine" / "modules" / "weather_wind_delta.json"
    bt_v2 = _load_module_json(base, "backtest_pwr_v2.json")
    pwr_v2_validated = bool(bt_v2.get("any_desk_passed"))

    if wd_path.is_file():
        wd = json.loads(wd_path.read_text(encoding="utf-8"))
        for row in wd.get("deltas", []):
            d_norm = float(row.get("delta_norm", row.get("delta_z", 0.0)))
            sid = row.get("signal_id", "PWR-01b")
            signals.append({
                "id": sid,
                "sector": "energy",
                "metric": "wind_fc_delta_norm",
                "power_desk": row.get("desk"),
                "zone": row.get("zone"),
                "delta_norm": d_norm,
                "alert": bool(row.get("alert")) and pwr_v2_validated,
                "msg": (
                    f"{row.get('desk')} delta_norm {d_norm:+.3f} "
                    f"(OM cubic MW − published) → imb−DA"
                ),
                "horizon": "gate D-1",
                "validated": pwr_v2_validated,
                "note": None if pwr_v2_validated else "backtest v2 pending / FAIL",
            })

    latest = enso.get("latest")
    if latest:
        phase = latest.get("phase", "neutral")
        oni = latest.get("oni", 0.0)
        affected = enso.get("affected_fx_desk_ids", [])
        signals.append({
            "id": "FX-ENSO",
            "sector": "fx",
            "metric": "oni_phase",
            "oni": oni,
            "phase": phase,
            "pairs": affected,
            "alert": abs(oni) >= 0.8,
            "msg": f"ENSO {phase} ONI={oni:+.2f} → {','.join(affected)} terms of trade",
            "horizon": "monthly",
        })

    ttf = fred_last(desk_csv_path(base, "TTF"))
    hub = fred_last(desk_csv_path(base, "HUB"))
    if ttf and hub and hub > 0:
        ratio = ttf / hub
        signals.append({
            "id": "GAS-X",
            "sector": "energy",
            "metric": "ttf_hub_ratio",
            "value": round(ratio, 3),
            "alert": ratio > 2.5 or ratio < 0.4,
            "msg": f"TTF/HUB={ratio:.2f} (weather-linked arb context)",
            "horizon": "weekly",
        })

    alerts = [s for s in signals if s.get("alert")]

    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "signals": signals,
        "alerts": len(alerts),
        "brief": " | ".join(s["id"] for s in alerts) if alerts else "no weather alerts",
    }

    out_path = base / "cache" / "spine" / "modules" / "weather_signals.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "ok": len(signals) > 0,
        "module": "weather_signals",
        "message": f"{len(signals)} signals {len(alerts)} alerts",
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
