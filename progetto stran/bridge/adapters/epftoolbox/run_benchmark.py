"""epftoolbox readiness check — DA price forecasting benchmark."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.deps import pip_install_hint, try_import
from bridge.spine_io import ROOT


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    out_path = base / "cache" / "spine" / "modules" / "epftoolbox_status.json"
    mod = try_import("epftoolbox")

    entsoe_csv = base / "cache" / "PDE.csv"
    has_power = entsoe_csv.is_file()

    if mod is None:
        payload = {
            "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "not_installed",
            "hint": pip_install_hint("epftoolbox"),
            "has_entsoe_cache": has_power,
            "repo": "https://github.com/javieralbacete/epftoolbox",
        }
    else:
        payload = {
            "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "ready",
            "has_entsoe_cache": has_power,
            "note": "Run LEAR/DNN benchmark on PDE hourly export (future module)",
        }

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "module": "epftoolbox_status",
        "message": payload["status"],
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
