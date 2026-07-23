"""Optional Dukascopy spot FX tick download."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.deps import pip_install_hint, try_import
from bridge.spine_io import ROOT


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    out_path = base / "cache" / "spine" / "modules" / "dukascopy_harvest.json"
    mod = try_import("dukascopy_python") or try_import("dukascopy")

    if mod is None:
        payload = {
            "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "not_installed",
            "hint": pip_install_hint("dukascopy-python"),
            "export_dir": "cache/exports/dukascopy",
            "note": "Free historical spot tick — intraday FX research",
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {
            "ok": True,
            "module": "dukascopy_harvest",
            "skipped": True,
            "message": "dukascopy not installed",
            "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
        }

    payload = {"built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"), "status": "ready"}
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "module": "dukascopy_harvest",
        "message": "dukascopy available",
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
