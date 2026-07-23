"""Harvest installed wind capacity (MW) by country/year from ENTSO-E TP."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from bridge.energy.entsoe_util import load_power_wind_config, pandas_client
from bridge.spine_io import ROOT


def _wind_mw_from_frame(df: pd.DataFrame) -> float:
    cols = [c for c in df.columns if "Wind" in str(c)]
    if not cols:
        return 0.0
    return float(df[cols].sum(axis=1).iloc[0])


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    cfg = load_power_wind_config(base)
    client = pandas_client()
    out_dir = base / "cache" / "weather" / "entsoe_capacity"
    out_dir.mkdir(parents=True, exist_ok=True)
    log: list[str] = []
    ok = 0

    if client is None:
        payload = {"ok": False, "log": ["no entsoe client"]}
        out_path = base / "cache" / "spine" / "modules" / "entsoe_capacity_harvest.json"
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {"ok": False, "module": "entsoe_capacity_harvest", "message": "no client", "outputs": []}

    countries = {d["country"]: desk for desk, d in cfg.get("desks", {}).items()}

    for country, desk_id in countries.items():
        yearly: dict[str, float] = {}
        for year in range(2021, datetime.now(timezone.utc).year + 1):
            try:
                start = pd.Timestamp(f"{year}-01-02", tz="UTC")
                end = pd.Timestamp(f"{year}-01-03", tz="UTC")
                df = client.query_installed_generation_capacity(country, start=start, end=end)
                if df is not None and len(df) > 0:
                    yearly[str(year)] = round(_wind_mw_from_frame(df), 1)
            except Exception as exc:
                log.append(f"{country}/{year}:{exc}")

        if yearly:
            path = out_dir / f"{country}.json"
            path.write_text(
                json.dumps({
                    "country": country,
                    "desk_id": desk_id,
                    "source": "entsoe query_installed_generation_capacity",
                    "wind_mw_by_year": yearly,
                    "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                }, indent=2),
                encoding="utf-8",
            )
            ok += 1
            log.append(f"{country}: {len(yearly)} years last={list(yearly.values())[-1]:.0f}MW")

    out_path = base / "cache" / "spine" / "modules" / "entsoe_capacity_harvest.json"
    payload = {"built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "countries_ok": ok, "log": log}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "ok": ok > 0,
        "module": "entsoe_capacity_harvest",
        "message": f"capacity {ok} countries",
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
