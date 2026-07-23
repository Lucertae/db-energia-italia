#!/usr/bin/env python3
"""Regenerate reference-projects.md from reference_projects.json (data portals, no GitHub)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "config" / "reference_projects.json"
OUT = ROOT.parent / "reference-projects.md"

CATEGORY_SECTION: dict[str, str] = {
    "ops_geo": "Ops / geo / energia",
    "ops_energy": "Ops / geo / energia",
    "commodity": "Ops / geo / energia",
    "desktop_bloomberg": "Bloomberg / trading desktop",
    "desktop_trading": "Bloomberg / trading desktop",
    "orderflow": "Bloomberg / trading desktop",
    "workflow_trading": "Bloomberg / trading desktop",
    "tui_research": "Keyboard-first / TUI",
    "tui_markets": "Keyboard-first / TUI",
    "tui_web_trading": "Keyboard-first / TUI",
    "tui_python": "Keyboard-first / TUI",
    "tui_portfolio": "Keyboard-first / TUI",
    "web_fullstack": "Self-hosted full-stack",
    "web_selfhosted": "Self-hosted full-stack",
    "web_clone": "Self-hosted full-stack",
    "data_platform": "Self-hosted full-stack",
    "chart_lib": "Librerie chart / UI",
    "energy_eu": "Energia / meteo / power grid",
    "energy_us": "Energia / meteo / power grid",
    "energy_global": "Energia / meteo / power grid",
    "weather_nwp": "Energia / meteo / power grid",
    "maritime": "Maritime / aviazione",
    "aviation": "Maritime / aviazione",
    "compliance": "Compliance / OSINT / cyber",
    "osint": "Compliance / OSINT / cyber",
    "threat_intel": "Compliance / OSINT / cyber",
    "portfolio": "Trading / execution / portfolio",
    "fx_systematic": "Trading / execution / portfolio",
    "crypto_execution": "Trading / execution / portfolio",
}

SECTION_ORDER = [
    "Ops / geo / energia",
    "Bloomberg / trading desktop",
    "Keyboard-first / TUI",
    "Self-hosted full-stack",
    "Librerie chart / UI",
    "Energia / meteo / power grid",
    "Maritime / aviazione",
    "Compliance / OSINT / cyber",
    "Trading / execution / portfolio",
]


def ds_link(p: dict) -> str:
    ds = Path(p.get("data_sources", "")).name
    return f"[elenco](reference-projects/data-sources/{ds})"


def main() -> int:
    data = json.loads(CFG.read_text(encoding="utf-8"))
    projects = sorted(data.get("projects") or [], key=lambda x: x.get("num", 0))

    by_section: dict[str, list[dict]] = {s: [] for s in SECTION_ORDER}
    for p in projects:
        cat = p.get("category", "other")
        sec = CATEGORY_SECTION.get(cat, "Altri")
        by_section.setdefault(sec, []).append(p)

    lines = [
        "# Progetti di riferimento — terminal / Bloomberg / ops desk\n\n",
        "> **Catalogo completo:** [`reference-projects/`](reference-projects/README.md) · "
        "**[Fonti dati uno per uno](reference-projects/data-sources/README.md)** · "
        "**[Matrice ops](reference-projects/ops-matrix.md)**\n\n",
        "Raccolta di terminal Bloomberg / ops desk — **rimandi alle fonti dati**, non ai repo GitHub.\n\n",
        "**Integrazione desk:** [`progetto stran/config/reference_projects.json`]"
        "(progetto%20stran/config/reference_projects.json) — "
        "vedi [`progetto stran/docs/REFERENCE_PROJECTS.md`](progetto%20stran/docs/REFERENCE_PROJECTS.md).\n\n",
        "---\n",
    ]

    for title in SECTION_ORDER + ["Altri"]:
        group = by_section.get(title) or []
        if not group:
            continue
        lines.append(f"\n## {title}\n\n")
        lines.append("| Progetto | Portale dati | Catalogo | Note |\n")
        lines.append("|----------|--------------|----------|------|\n")
        for p in group:
            name = p.get("name", "")
            portal = p.get("data_portal", "")
            label = p.get("data_portal_label", "portale")
            role = (p.get("desk_role") or "").replace("|", "/")[:120]
            lines.append(
                f"| **{name}** | [{label}]({portal}) | {ds_link(p)} | {role} |\n"
            )

    lines.extend(
        [
            "\n---\n\n",
            "## Riepilogo per STRAN\n\n",
            "STRAN (`progetto stran/world_clocks.exe`) — demo Win32 GDI, desk ops. "
            "Sulla pagina **ING → REF** ogni voce punta al **portale dati** e al catalogo feed/API.\n\n",
            "*Aggiornato da `scripts/desk_harvest/gen_reference_summary.py`*\n",
        ]
    )

    OUT.write_text("".join(lines), encoding="utf-8")
    print(f"Wrote {OUT}  projects={len(projects)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
