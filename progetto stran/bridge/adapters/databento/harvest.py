"""Optional CME FX futures via Databento."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.deps import pip_install_hint, try_import
from bridge.spine_io import ROOT, load_fx_manifest


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    out_path = base / "cache" / "spine" / "modules" / "databento_harvest.json"
    key = os.environ.get("DATABENTO_API_KEY", "").strip()
    db = try_import("databento")

    manifest = load_fx_manifest(base)
    symbols = [p.get("cme_future") for p in manifest.get("pairs", []) if p.get("cme_future")]

    if db is None or not key:
        payload = {
            "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "status": "not_configured",
            "hint": pip_install_hint("databento") if db is None else "set DATABENTO_API_KEY",
            "target_symbols": symbols,
            "export_dir": "cache/exports/databento",
            "nautilus_note": "Databento DBN feeds NautilusTrader natively",
        }
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return {
            "ok": True,
            "module": "databento_harvest",
            "skipped": True,
            "message": "databento not configured",
            "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
        }

    export_dir = base / "cache" / "exports" / "databento"
    export_dir.mkdir(parents=True, exist_ok=True)
    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "ready",
        "symbols": symbols,
        "export_dir": str(export_dir.relative_to(base)).replace("\\", "/"),
        "note": "Implement dataset query in harvest.py when API key present",
    }
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return {
        "ok": True,
        "module": "databento_harvest",
        "message": f"databento ready symbols={len(symbols)}",
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
