"""ENTSO-E harvest via entsoe-py (fallback: desk harvest_entsoe.py)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bridge.deps import run_harvest_script, try_import
from bridge.spine_io import ROOT


ZONES = {
    "PDE": "10Y1001A1001A82H",
    "PFR": "10YFR-RTE------C",
    "PIT": "10Y1001A1001A73I",
    "PNL": "10YNL----------L",
    "PPL": "10YPL-AREA-----S",
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


def _merge_daily_csv(cache: Path, desk_id: str, daily: dict[str, float]) -> int:
    path = cache / f"{desk_id}.csv"
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
    days = sorted(rows.keys())[-1900:]
    with path.open("w", encoding="utf-8", newline="") as f:
        f.write(f"DATE,{desk_id}\n")
        for d in days:
            f.write(f"{d},{rows[d]:.4f}\n")
    return len(days)


def _harvest_entsoe_py(token: str, cache: Path) -> tuple[int, list[str]]:
    entsoe = try_import("entsoe")
    if entsoe is None:
        return 0, ["entsoe-py not installed"]

    import pandas as pd

    client = entsoe.EntsoePandasClient(api_key=token)
    end = pd.Timestamp.now(tz="UTC")
    start = end - pd.Timedelta(days=7)
    ok = 0
    log: list[str] = []

    for desk_id, eic in ZONES.items():
        try:
            series = client.query_day_ahead_prices(eic, start=start, end=end)
            if series is None or len(series) == 0:
                log.append(f"{desk_id}: empty")
                continue
            daily = series.resample("D").mean().dropna()
            daily_map = {idx.strftime("%Y-%m-%d"): float(v) for idx, v in daily.items()}
            n = _merge_daily_csv(cache, desk_id, daily_map)
            ok += 1
            log.append(f"{desk_id}: {len(daily_map)}d merged ({n} total)")
        except Exception as exc:
            log.append(f"{desk_id}: {exc}")

    return ok, log


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    cache = base / "cache"
    cache.mkdir(parents=True, exist_ok=True)

    token = _load_token(cache)
    backend = "none"
    ok_count = 0
    log: list[str] = []

    if token and try_import("entsoe") is not None:
        ok_count, log = _harvest_entsoe_py(token, cache)
        backend = "entsoe-py"
    elif token:
        ok, out = run_harvest_script(base, "scripts/desk_harvest/harvest_entsoe.py")
        backend = "desk_harvest_xml"
        log.append(out or ("ok" if ok else "fail"))
        ok_count = 1 if ok else 0
    else:
        log.append("no ENTSOE token — set ENTSOE_API_TOKEN or cache/entsoe.key")

    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "backend": backend,
        "zones_ok": ok_count,
        "log": log[-10:],
    }
    out_path = base / "cache" / "spine" / "modules" / "entsoe_py_harvest.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "ok": ok_count > 0 or backend == "none",
        "module": "entsoe_py_harvest",
        "message": f"{backend} zones={ok_count}",
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
