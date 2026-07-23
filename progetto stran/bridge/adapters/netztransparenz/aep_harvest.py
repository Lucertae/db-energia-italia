"""Netztransparenz.de ID-AEP / AEP harvest for PDE target (id_minus_da)."""
from __future__ import annotations

import json
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bridge.energy.entsoe_util import load_power_wind_config
from bridge.spine_io import ROOT

BASE_URL = "https://ds.netztransparenz.de/api/v1/data/IdAep"
CHUNK_DAYS = 14
MAX_CHUNKS = 6


def _parse_id_aep_csv(text: str) -> dict[str, float]:
    """Parse Format 13 → hourly UTC mean €/MWh."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.startswith("#")]
    if len(lines) < 2:
        return {}
    # skip header row(s)
    start = 0
    if "ID AEP" in lines[0] or "Datum" in lines[0]:
        start = 1
    buckets: dict[str, list[float]] = {}
    for ln in lines[start:]:
        parts = [p.strip() for p in ln.replace(";", ",").split(",")]
        if len(parts) < 6:
            continue
        try:
            d = parts[0]
            t_from = parts[1] if ":" in parts[1] else parts[2]
            price_s = parts[-1].replace(",", ".")
            price = float(price_s)
            hk = f"{d}T{int(t_from.split(':')[0]):02d}"
            buckets.setdefault(hk, []).append(price)
        except (ValueError, IndexError):
            continue
    return {hk: sum(v) / len(v) for hk, v in buckets.items() if v}


def _fetch_range(start: date, end: date) -> dict[str, float]:
    url = f"{BASE_URL}/dateFrom={start.isoformat()}/dateTo={end.isoformat()}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "ops-desk/1.0", "Accept": "text/csv,*/*"},
    )
    try:
        body = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
        return _parse_id_aep_csv(body)
    except Exception:
        return {}


def _load_local_csv(base: Path) -> dict[str, float]:
    merged: dict[str, float] = {}
    d = base / "cache" / "weather" / "netztransparenz" / "IdAep"
    if not d.is_dir():
        return merged
    for path in sorted(d.glob("*.csv")):
        try:
            merged.update(_parse_id_aep_csv(path.read_text(encoding="utf-8", errors="replace")))
        except OSError:
            continue
    return merged


def _save_monthly(base: Path, desk_id: str, hourly: dict[str, float]) -> int:
    out_dir = base / "cache" / "weather" / "entsoe_hourly" / "id_index" / desk_id
    out_dir.mkdir(parents=True, exist_ok=True)
    by_month: dict[str, list[tuple[str, float]]] = {}
    for hk, v in sorted(hourly.items()):
        by_month.setdefault(hk[:7], []).append((hk, v))
    for mk, pairs in by_month.items():
        payload = {
            "month": mk,
            "desk": desk_id,
            "source": "netztransparenz_IdAep",
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
        if str(desk.get("target", "")) != "id_minus_da":
            continue
        hourly = _load_local_csv(base)
        end = date.today()
        start = date(2022, 7, 1)
        cursor = start
        chunks = 0
        while cursor < end and chunks < MAX_CHUNKS:
            chunk_end = min(cursor + timedelta(days=CHUNK_DAYS), end)
            got = _fetch_range(cursor, chunk_end)
            if got:
                hourly.update(got)
                log.append(f"api {cursor}→{chunk_end}: {len(got)}h")
            cursor = chunk_end + timedelta(days=1)
            chunks += 1

        n_months = _save_monthly(base, desk_id, hourly) if hourly else 0
        if hourly:
            desks_ok += 1
            log.append(f"{desk_id}: {len(hourly)}h ID-AEP → {n_months} months")
        else:
            log.append(
                f"{desk_id}: no ID-AEP — API 401 or empty; drop CSV in "
                "cache/weather/netztransparenz/IdAep/ or check ds.netztransparenz.de access"
            )

    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "desks_ok": desks_ok,
        "log": log,
        "api": BASE_URL,
    }
    out_path = base / "cache" / "spine" / "modules" / "netztransparenz_aep_harvest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "module": "netztransparenz_aep_harvest",
        "message": f"netztransparenz ID-AEP {desks_ok} desks",
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
