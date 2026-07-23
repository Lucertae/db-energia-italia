#!/usr/bin/env python3
"""Generate reference-projects/ops-matrix.md from desk config."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "config" / "reference_projects.json"
OUT = ROOT.parent / "reference-projects" / "ops-matrix.md"


def fmt_refresh(ops: dict) -> str:
    label = ops.get("refresh_label") or ""
    sec = ops.get("refresh_sec")
    if label:
        return label
    if sec is None:
        return "on-demand"
    if sec < 60:
        return f"{sec}s"
    if sec < 3600:
        return f"{sec // 60}min"
    return f"{sec // 3600}h"


def main() -> int:
    data = json.loads(CFG.read_text(encoding="utf-8"))
    lines = [
        "# Reference projects — matrice operativa",
        "",
        "Live vs batch, mappa, frequenza aggiornamento. Sorgente: `progetto stran/config/reference_projects.json`.",
        "",
        "| # | Progetto | Mode | Mappa | Tipo mappa | Refresh |",
        "|---|----------|------|-------|------------|---------|",
    ]
    for p in sorted(data.get("projects", []), key=lambda x: x.get("num", 0)):
        ops = p.get("ops") or {}
        map_yes = "sì" if ops.get("needs_map") else "no"
        lines.append(
            f"| {p.get('num', '')} | **{p.get('name', '')}** "
            f"| {ops.get('data_mode', '?')} "
            f"| {map_yes} "
            f"| {ops.get('map_kind', '—')} "
            f"| {fmt_refresh(ops)} |"
        )
    lines += [
        "",
        "## Legenda `data_mode`",
        "",
        "| Mode | Significato |",
        "|------|-------------|",
        "| **live** | Feed streaming o poll continuo |",
        "| **mixed** | Live API + RSS/batch insieme |",
        "| **batch** | Download periodico o dataset statico |",
        "| **static** | Dati simulati / demo |",
        "| **on_demand** | Run su richiesta (scan, analisi) |",
        "| **library** | Nessun feed bundled — dipende dall'host |",
        "",
        "*Aggiornato automaticamente da `scripts/desk_harvest/apply_reference_ops.py`*",
        "",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
