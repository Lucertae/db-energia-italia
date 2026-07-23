"""EPEX continuous intraday index (ID1/ID3) harvest for PWR-01 v2 DE target.

Sources (in order):
1. Local CSV cache: cache/weather/epex_id/{desk}/Continuous_Index-*.csv (EPEX SFTP export)
2. Parsed monthly JSON already on disk

Without EPEX subscription, run with empty cache — pwr_v2 falls back to imb−DA.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.energy.entsoe_util import load_power_wind_config
from bridge.spine_io import ROOT


def _hour_key_from_iso(ts: str) -> str:
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


def _parse_continuous_index_csv(path: Path, *, index_name: str = "ID1") -> dict[str, float]:
    """Parse EPEX Continuous_Index-MA-*.csv → delivery hour → EUR/MWh."""
    out: dict[str, float] = {}
    text = path.read_text(encoding="utf-8", errors="replace")
    lines = [ln for ln in text.splitlines() if ln and not ln.startswith("#")]
    if len(lines) < 2:
        return out
    reader = csv.DictReader(lines)
    for row in reader:
        name = (row.get("IndexName") or row.get("indexname") or "").strip().upper()
        if name and index_name.upper() not in name:
            continue
        start = row.get("DeliveryStart") or row.get("deliverystart") or ""
        price = row.get("IndexPrice") or row.get("indexprice") or row.get("Price")
        if not start or price in (None, ""):
            continue
        try:
            hk = _hour_key_from_iso(start.replace("Z", "+00:00"))
            out[hk] = float(price)
        except (TypeError, ValueError):
            continue
    return out


def _load_desk_id_index(base: Path, desk_id: str, index_name: str) -> dict[str, float]:
    merged: dict[str, float] = {}
    d = base / "cache" / "weather" / "epex_id" / desk_id
    if d.is_dir():
        for path in sorted(d.glob("Continuous_Index*.csv")) + sorted(d.glob("*.csv")):
            merged.update(_parse_continuous_index_csv(path, index_name=index_name))
    cache = base / "cache" / "weather" / "entsoe_hourly" / "id_index" / desk_id
    if cache.is_dir():
        for path in sorted(cache.glob("*.json")):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                continue
            for ts, v in zip(data.get("timestamps", []), data.get("id_eur_mwh", [])):
                if v is None:
                    continue
                merged[_hour_key_from_iso(str(ts))] = float(v)
    return merged


def _save_monthly(base: Path, desk_id: str, hourly: dict[str, float]) -> int:
    if not hourly:
        return 0
    out_dir = base / "cache" / "weather" / "entsoe_hourly" / "id_index" / desk_id
    out_dir.mkdir(parents=True, exist_ok=True)
    by_month: dict[str, list[tuple[str, float]]] = {}
    for hk, v in sorted(hourly.items()):
        mk = hk[:7]
        by_month.setdefault(mk, []).append((hk, v))
    for mk, pairs in by_month.items():
        payload = {
            "month": mk,
            "desk": desk_id,
            "source": "epex_continuous_index",
            "timestamps": [f"{hk}:00:00+00:00" for hk, _ in pairs],
            "id_eur_mwh": [v for _, v in pairs],
        }
        (out_dir / f"{mk}.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return len(by_month)


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    cfg = load_power_wind_config(base)
    log: list[str] = []
    desks_ok = 0

    for desk_id, desk in cfg.get("desks", {}).items():
        target = str(desk.get("target", "imb_minus_da"))
        if target != "id_minus_da":
            continue
        index_name = str(desk.get("id_index", "ID1"))
        hourly = _load_desk_id_index(base, desk_id, index_name)
        n_months = _save_monthly(base, desk_id, hourly)
        if hourly:
            desks_ok += 1
            log.append(f"{desk_id}: {len(hourly)}h ID ({index_name}) → {n_months} months")
        else:
            csv_dir = base / "cache" / "weather" / "epex_id" / desk_id
            log.append(
                f"{desk_id}: no ID data — drop EPEX Continuous_Index-*.csv in "
                f"{csv_dir.relative_to(base).as_posix()}/ (requires EPEX SFTP license)"
            )

    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "desks_ok": desks_ok,
        "log": log,
        "note": "ID1/ID3 from EPEX Continuous_Index CSV; fallback imb−DA when empty",
    }
    out_path = base / "cache" / "spine" / "modules" / "epex_id_harvest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "module": "epex_id_harvest",
        "message": f"epex_id {desks_ok} desks with ID cache",
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
