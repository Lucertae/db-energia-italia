"""Optional ERA5 reanalysis via cdsapi (Copernicus CDS)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.deps import pip_install_hint, try_import
from bridge.spine_io import ROOT


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    out_path = base / "cache" / "spine" / "modules" / "era5_harvest.json"
    cds = try_import("cdsapi")
    key = os.environ.get("CDSAPI_URL") or os.path.exists(os.path.expanduser("~/.cdsapirc"))

    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ready" if cds and key else "not_configured",
        "hint": pip_install_hint("cdsapi") if not cds else "register at cds.climate.copernicus.eu → ~/.cdsapirc",
        "dataset": "reanalysis-era5-single-levels",
        "export_dir": "cache/weather/era5",
        "training_use": "atlite / epftoolbox feature history",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "module": "era5_harvest",
        "skipped": not (cds and key),
        "message": payload["status"],
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
