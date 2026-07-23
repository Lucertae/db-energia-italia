"""Run registered bridge modules from config/modules.json."""
from __future__ import annotations

import importlib
import json
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.spine_io import ROOT, load_json


def _resolve_entry(entry: str):
    mod_name, _, fn_name = entry.partition(":")
    if not fn_name:
        raise ValueError(f"invalid module entry (need module:func): {entry}")
    mod = importlib.import_module(mod_name)
    fn = getattr(mod, fn_name)
    return fn


def run_module(mod_cfg: dict[str, Any], root: Path) -> dict[str, Any]:
    mid = mod_cfg.get("id", "?")
    if not mod_cfg.get("enabled", True):
        return {"ok": True, "module": mid, "skipped": True, "message": "disabled"}

    entry = mod_cfg.get("entry", "")
    try:
        fn = _resolve_entry(entry)
        result = fn(root)
        if not isinstance(result, dict):
            result = {"ok": True, "module": mid, "message": str(result)}
        result.setdefault("module", mid)
        result.setdefault("ok", True)
        return result
    except Exception as exc:
        return {
            "ok": False,
            "module": mid,
            "message": str(exc),
            "trace": traceback.format_exc(limit=8),
        }


def run_all(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    cfg_path = base / "config" / "modules.json"
    if not cfg_path.is_file():
        return {"ok": False, "error": f"missing {cfg_path}", "results": []}

    cfg = load_json(cfg_path)
    results: list[dict[str, Any]] = []
    ok_all = True

    for mod in cfg.get("modules", []):
        res = run_module(mod, base)
        results.append(res)
        if not res.get("ok", False):
            ok_all = False

    index = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ok": ok_all,
        "modules": results,
        "brief": _brief(results),
    }

    out_dir = base / "cache" / "spine"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "modules_index.json").write_text(
        json.dumps(index, indent=2), encoding="utf-8"
    )
    return index


def _brief(results: list[dict[str, Any]]) -> str:
    parts: list[str] = []
    for r in results:
        if r.get("skipped"):
            continue
        tag = r.get("module", "?")
        if r.get("ok"):
            parts.append(f"{tag}:ok")
        else:
            parts.append(f"{tag}:FAIL")
    return " | ".join(parts) if parts else "no modules"


if __name__ == "__main__":
    idx = run_all()
    print(f"modules {'OK' if idx['ok'] else 'FAIL'}  {idx.get('brief', '')}")
