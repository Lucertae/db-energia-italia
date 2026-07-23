#!/usr/bin/env python3
"""Merge reference_ops into config/reference_projects.json."""
from __future__ import annotations

import json
from pathlib import Path

from reference_ops import REFERENCE_OPS

ROOT = Path(__file__).resolve().parents[2]
CFG = ROOT / "config" / "reference_projects.json"


def main() -> int:
    data = json.loads(CFG.read_text(encoding="utf-8"))
    projects = data.get("projects") or []
    missing = []
    for p in projects:
        pid = p.get("id", "")
        ops = REFERENCE_OPS.get(pid)
        if not ops:
            missing.append(pid)
            continue
        p["ops"] = ops
    if missing:
        print("WARN missing ops for:", ", ".join(missing))
    data["ops_schema"] = {
        "data_mode": "live | mixed | batch | static | on_demand | library",
        "needs_map": "true if primary UI requires geo/spatial map canvas",
        "map_kind": "globe | maritime | adsb | energy | chart | orderbook | workspace | graph | tui | none | library",
        "refresh_sec": "typical poll interval seconds; null = on-demand or N/A",
        "refresh_label": "human-readable refresh summary",
    }
    data["version"] = 2
    CFG.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Updated {CFG}  projects={len(projects)}  ops={len(projects) - len(missing)}")
    # regenerate markdown matrix
    try:
        from gen_ops_matrix import main as gen_md
        gen_md()
    except Exception as e:
        print(f"WARN gen_ops_matrix: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
