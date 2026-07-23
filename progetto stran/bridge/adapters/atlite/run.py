"""Optional ERA5 → wind/solar capacity factors via atlite."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.deps import pip_install_hint, try_import
from bridge.spine_io import ROOT


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    out_path = base / "cache" / "spine" / "modules" / "atlite_profiles.json"
    atlite = try_import("atlite")

    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ready" if atlite else "not_installed",
        "hint": None if atlite else pip_install_hint("atlite"),
        "export_dir": "cache/weather/cf",
        "companions": ["pvlib", "windpowerlib"],
        "repo": "https://github.com/PyPSA/atlite",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "module": "atlite_profiles",
        "skipped": atlite is None,
        "message": payload["status"],
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
