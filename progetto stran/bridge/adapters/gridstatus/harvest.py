"""Optional US ISO power via gridstatus."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.deps import pip_install_hint, try_import
from bridge.spine_io import ROOT


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    out_path = base / "cache" / "spine" / "modules" / "gridstatus_harvest.json"
    gs = try_import("gridstatus")

    if gs is None:
        payload = {
            "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "not_installed",
            "hint": pip_install_hint("gridstatus"),
            "isos": ["CAISO", "ERCOT", "PJM", "MISO", "NYISO", "SPP"],
            "export_dir": "cache/exports/gridstatus",
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {
            "ok": True,
            "module": "gridstatus_harvest",
            "skipped": True,
            "message": "gridstatus not installed",
            "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
        }

    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ready",
        "note": "Fetch LMP/load via gridstatus.get_iso() in future harvest step",
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "module": "gridstatus_harvest",
        "message": "gridstatus available",
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
