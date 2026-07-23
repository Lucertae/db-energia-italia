"""Load config/data_sources.json and config/reference_projects.json registries."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from bridge.spine_io import ROOT


def load_data_sources(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    path = base / "config" / "data_sources.json"
    if not path.is_file():
        return {"sources": []}
    return json.loads(path.read_text(encoding="utf-8"))


def load_reference_projects(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    path = base / "config" / "reference_projects.json"
    if not path.is_file():
        return {"projects": []}
    return json.loads(path.read_text(encoding="utf-8"))


def reference_by_id(root: Path | None = None) -> dict[str, dict[str, Any]]:
    cfg = load_reference_projects(root)
    return {p["id"]: p for p in cfg.get("projects", []) if p.get("id")}


def sources_by_sector(root: Path | None = None) -> dict[str, list[dict[str, Any]]]:
    cfg = load_data_sources(root)
    out: dict[str, list[dict[str, Any]]] = {}
    for src in cfg.get("sources", []):
        sector = src.get("sector", "other")
        out.setdefault(sector, []).append(src)
    return out
