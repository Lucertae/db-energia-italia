"""NOAA ENSO ONI index → commodity FX overlay features."""
from __future__ import annotations

import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.weather.io import load_weather_manifest
from bridge.spine_io import ROOT

ONI_URL = "https://www.cpc.ncep.noaa.gov/data/indices/oni.ascii.txt"
ONI_FALLBACK = "https://psl.noaa.gov/gcos_wgsp/Timeseries/Data/nino34.long.anom.data.txt"


def _parse_oni_cpc(text: str) -> float | None:
    """Parse CPC ONI ascii — one row per season, ANOM column."""
    last_anom: float | None = None
    for line in text.splitlines():
        line = line.strip()
        if not line or "SEAS" in line.upper() or "ANOM" in line.upper():
            continue
        parts = re.split(r"\s+", line)
        if len(parts) < 4:
            continue
        try:
            last_anom = float(parts[-1])
        except ValueError:
            continue
    return last_anom


def _parse_nino34_anom(text: str) -> float | None:
    """Fallback: NOAA PSL nino34 monthly anomalies."""
    vals: list[float] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or not re.match(r"^\d{4}", line):
            continue
        for tok in re.split(r"\s+", line)[1:]:
            try:
                v = float(tok)
                if abs(v) < 90:
                    vals.append(v)
            except ValueError:
                continue
    return vals[-1] if vals else None


def _fetch_oni() -> tuple[float, str]:
    for url, parser in (
        (ONI_URL, _parse_oni_cpc),
        (ONI_FALLBACK, _parse_nino34_anom),
    ):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "ops-desk-weather/1.0"})
            with urllib.request.urlopen(req, timeout=30) as resp:
                text = resp.read().decode("utf-8", errors="replace")
            val = parser(text)
            if val is not None:
                return val, url
        except Exception:
            continue
    raise ValueError("no ONI values from CPC or PSL fallback")


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    manifest = load_weather_manifest(base)
    enso_cfg = manifest.get("enso", {})
    out_path = base / "cache" / "spine" / "modules" / "weather_enso.json"

    try:
        oni, src = _fetch_oni()
        if oni >= 0.5:
            phase = "el_nino"
        elif oni <= -0.5:
            phase = "la_nina"
        else:
            phase = "neutral"
        latest = {"oni": round(oni, 3), "phase": phase, "source": src}
    except Exception as exc:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps({"error": str(exc)}, indent=2), encoding="utf-8")
        return {
            "ok": False,
            "module": "weather_enso",
            "message": str(exc),
            "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
        }

    fx_map = enso_cfg.get("fx_commodity_pairs", {})
    affected = fx_map.get(phase, [])

    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "latest": latest,
        "affected_fx_desk_ids": affected,
        "note": "ENSO overlay for commodity FX — weekly/monthly horizon",
    }

    cache_path = base / "cache" / "weather" / "enso.json"
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "module": "weather_enso",
        "message": f"ONI={oni:+.2f} {phase} fx={','.join(affected)}",
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
