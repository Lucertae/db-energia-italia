"""Optional NWP download via Herbie — GEFS 10m wind subset for DE grid."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.deps import pip_install_hint, try_import
from bridge.energy.entsoe_util import load_power_wind_config
from bridge.spine_io import ROOT


def _gefs_wind_sample(base: Path) -> dict[str, Any]:
    """Download one recent GEFS cycle 10m wind at DE grid centroid if herbie installed."""
    herbie_mod = try_import("herbie")
    if herbie_mod is None:
        return {"ok": False, "reason": "herbie not installed"}

    try:
        from herbie import Herbie
    except ImportError:
        return {"ok": False, "reason": "herbie import failed"}

    pcfg = load_power_wind_config(base)
    desk = pcfg.get("desks", {}).get("PDE", {})
    grid = desk.get("grid_points", [])
    if not grid:
        return {"ok": False, "reason": "no PDE grid in power_wind.json"}

    lat = sum(float(p["lat"]) * float(p.get("weight", 1)) for p in grid) / sum(
        float(p.get("weight", 1)) for p in grid
    )
    lon = sum(float(p["lon"]) * float(p.get("weight", 1)) for p in grid) / sum(
        float(p.get("weight", 1)) for p in grid
    )

    out_dir = base / "cache" / "weather" / "grib" / "gefs"
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        H = Herbie("now", model="gefs", product="pgrb2b", fxx=6)
        ds = H.xarray("UGRD:10 m above ground")
        sample = {
            "model": "gefs",
            "fxx": 6,
            "lat_centroid": round(lat, 3),
            "lon_centroid": round(lon, 3),
            "variables": list(ds.data_vars)[:4] if hasattr(ds, "data_vars") else [],
            "grib_path": str(getattr(H, "local_file", "")),
        }
        meta_path = out_dir / "latest_sample.json"
        meta_path.write_text(json.dumps(sample, indent=2), encoding="utf-8")
        return {"ok": True, "sample": sample, "meta": str(meta_path)}
    except Exception as exc:
        return {"ok": False, "reason": str(exc)[:200]}


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    out_path = base / "cache" / "spine" / "modules" / "herbie_harvest.json"
    herbie = try_import("herbie")
    gefs = _gefs_wind_sample(base) if herbie else {"ok": False, "skipped": True}

    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ready" if herbie else "not_installed",
        "hint": None if herbie else pip_install_hint("herbie"),
        "models": ["HRRR", "GFS", "GEFS", "ECMWF", "NBM", "AIFS"],
        "gefs_sample": gefs,
        "export_dir": "cache/weather/grib",
        "next": "GEFS ensemble spread → delta uncertainty gate (after v2 methodology fixed)",
        "repo": "https://github.com/blaylockbk/Herbie",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    msg = "herbie+gefs sample ok" if gefs.get("ok") else ("herbie ready" if herbie else "herbie not installed")
    return {
        "ok": True,
        "module": "herbie_harvest",
        "skipped": herbie is None,
        "message": msg,
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
