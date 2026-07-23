#!/usr/bin/env python3
"""Replace GitHub repo links with data portals in config + catalog markdown."""
from __future__ import annotations

import json
import re
from pathlib import Path

from reference_portals import REFERENCE_PORTALS

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "config" / "reference_projects.json"
CATALOG = ROOT.parent / "reference-projects"


def merge_json() -> tuple[int, int]:
    data = json.loads(CFG.read_text(encoding="utf-8"))
    projects = data.get("projects") or []
    missing: list[str] = []
    for p in projects:
        pid = p.get("id", "")
        portal = REFERENCE_PORTALS.get(pid)
        if not portal:
            missing.append(pid)
            continue
        p["data_portal"] = portal["data_portal"]
        p["data_portal_label"] = portal.get("data_portal_label", "")
        p.pop("repo", None)
    if missing:
        print("WARN missing portals for:", ", ".join(missing))
    data["version"] = 3
    data["link_policy"] = "data_portal + data_sources catalog — no GitHub repo links in desk/catalog"
    CFG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return len(projects), len(projects) - len(missing)


def _strip_repo_lines(text: str) -> str:
    lines = text.splitlines(keepends=True)
    out: list[str] = []
    skip_prefixes = (
        "- **Repo:**",
        "- **Repo client:**",
        "- **Fork attivo:**",
        "- **Download:**",
    )
    for line in lines:
        if any(line.startswith(p) for p in skip_prefixes):
            continue
        if "Repo GitHub non accessibile" in line:
            continue
        if "github.com" in line and line.strip().startswith("Documentazione:"):
            continue
        out.append(line)
    return "".join(out)


def _ensure_fonti_line(text: str, ds_rel: str, portal: str, label: str) -> str:
    fonti = f"- **Fonti dati:** [{label}]({portal}) · [elenco completo]({ds_rel})\n"
    if "- **Fonti dati:**" in text:
        text = re.sub(r"- \*\*Fonti dati:\*\*.*\n", fonti, text, count=1)
        return text
    # insert after first heading block (after title line)
    m = re.search(r"(^# .+\n\n)", text, re.MULTILINE)
    if m:
        pos = m.end()
        return text[:pos] + fonti + text[pos:]
    return fonti + text


def _patch_data_sources_header(text: str, portal: str, label: str) -> str:
    text = _strip_repo_lines(text)
    text = re.sub(
        r"Estratto dal codice sorgente GitHub",
        "Estratto dal codice sorgente",
        text,
    )
    portal_line = f"- **Portale dati:** [{label}]({portal})\n\n"
    if "- **Portale dati:**" in text:
        text = re.sub(r"- \*\*Portale dati:\*\*.*\n", portal_line, text, count=1)
        return text
    m = re.search(r"(^# .+\n\n)", text, re.MULTILINE)
    if m:
        pos = m.end()
        return text[:pos] + portal_line + text[pos:]
    return portal_line + text


def patch_markdown(projects: list[dict]) -> tuple[int, int]:
    cards = ds = 0
    for p in projects:
        pid = p.get("id", "")
        portal = REFERENCE_PORTALS.get(pid)
        if not portal:
            continue
        num = int(p.get("num", 0))
        ds_name = Path(p.get("data_sources", "")).name
        if not ds_name:
            ds_name = f"{num:02d}-{pid.replace('_', '-')}.md"
        ds_rel = f"../data-sources/{ds_name}"
        label = portal.get("data_portal_label") or p.get("name", pid)
        url = portal["data_portal"]

        card_path = CATALOG / "projects" / Path(p.get("project_card", "")).name
        if card_path.is_file():
            raw = card_path.read_text(encoding="utf-8")
            patched = _ensure_fonti_line(_strip_repo_lines(raw), ds_rel, url, label)
            if patched != raw:
                card_path.write_text(patched, encoding="utf-8")
                cards += 1

        ds_path = CATALOG / "data-sources" / ds_name
        if ds_path.is_file():
            raw = ds_path.read_text(encoding="utf-8")
            patched = _patch_data_sources_header(raw, url, label)
            if patched != raw:
                ds_path.write_text(patched, encoding="utf-8")
                ds += 1
    return cards, ds


def main() -> int:
    n, ok = merge_json()
    data = json.loads(CFG.read_text(encoding="utf-8"))
    cards, ds_files = patch_markdown(data.get("projects") or [])
    print(f"Updated {CFG}  projects={n}  portals={ok}")
    print(f"Patched project cards={cards}  data-sources headers={ds_files}")
    try:
        from gen_reference_summary import main as gen_summary
        gen_summary()
    except Exception as e:
        print(f"WARN gen_reference_summary: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
