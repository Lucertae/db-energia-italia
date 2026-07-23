"""Optional FX ingestion via findatapy (Cuemacro)."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.deps import pip_install_hint, try_import
from bridge.spine_io import ROOT


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    mod = try_import("findatapy")
    out_path = base / "cache" / "spine" / "modules" / "findatapy_harvest.json"

    if mod is None:
        payload = {
            "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "not_installed",
            "hint": pip_install_hint("findatapy"),
            "repo": "https://github.com/cuemacro/findatapy",
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {
            "ok": True,
            "module": "findatapy_harvest",
            "skipped": True,
            "message": "findatapy not installed",
            "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
        }

    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ready",
        "note": "Configure findatapy market_data_register in bridge/adapters/findatapy/config.yaml",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "module": "findatapy_harvest",
        "message": "findatapy available — add config to enable downloads",
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
