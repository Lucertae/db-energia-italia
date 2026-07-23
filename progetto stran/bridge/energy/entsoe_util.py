"""Shared ENTSO-E client helpers."""
from __future__ import annotations

import os
from pathlib import Path

from bridge.deps import try_import
from bridge.spine_io import ROOT, load_json


def load_token(cache: Path | None = None) -> str:
    base = cache or (ROOT / "cache")
    for env in ("ENTSOE_API_TOKEN", "HEDGE_ENTSOE_TOKEN"):
        v = os.environ.get(env, "").strip()
        if v:
            return v
    key_file = base / "entsoe.key"
    if key_file.is_file():
        return key_file.read_text(encoding="utf-8").strip()
    return ""


def pandas_client():
    if try_import("entsoe") is None:
        return None
    token = load_token()
    if not token:
        return None
    entsoe = __import__("entsoe")
    return entsoe.EntsoePandasClient(api_key=token)


def load_power_wind_config(root: Path | None = None) -> dict:
    base = root or ROOT
    path = base / "config" / "power_wind.json"
    if not path.is_file():
        return {"desks": {}, "backtest": {}}
    return load_json(path)
