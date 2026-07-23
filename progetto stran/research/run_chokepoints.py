#!/usr/bin/env python3
"""
Chokepoint corridor analysis from AIS positions (desk ships cache).

Counts vessels in each corridor bbox defined in chokepoints_catalog.json.
Requires AIS live data (cache/ais.key) or a snapshot JSON export.

Usage:
  python research/run_chokepoints.py
  python research/run_chokepoints.py --snapshot path/to/ships.json
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from paths import ensure_output, RESEARCH_DIR


def in_bbox(lat: float, lon: float, bbox: list[float]) -> bool:
    lat_min, lat_max, lon_min, lon_max = bbox
    return lat_min <= lat <= lat_max and lon_min <= lon <= lon_max


def load_catalog() -> dict:
    p = RESEARCH_DIR / "chokepoints_catalog.json"
    return json.loads(p.read_text(encoding="utf-8"))


def count_in_zones(vessels: list[dict], catalog: dict) -> dict[str, int]:
    counts = {cp["id"]: 0 for cp in catalog["chokepoints"]}
    for v in vessels:
        lat, lon = v.get("lat"), v.get("lon")
        if lat is None or lon is None:
            continue
        for cp in catalog["chokepoints"]:
            if in_bbox(lat, lon, cp["bbox"]):
                counts[cp["id"]] += 1
    return counts


def demo_report(catalog: dict) -> str:
    """Generate report template when no AIS snapshot available."""
    lines = [
        "# Chokepoint monitoring report",
        "",
        "_No AIS snapshot — showing catalog baseline and monitoring plan._",
        "",
        "## Baseline flows (EIA 1H25, mb/d)",
        "",
    ]
    for k, v in catalog.get("baseline_flows_1h25_mbpd", {}).items():
        lines.append(f"- **{k}**: {v} mb/d")
    lines.extend(["", "## Corridors to monitor (AIS bbox)", ""])
    for cp in catalog["chokepoints"]:
        lines.append(
            f"- **{cp['id']}** {cp['name']}: bbox {cp['bbox']} — {cp.get('notes', '')}"
        )
    lines.extend([
        "",
        "## Pipeline bypass capacity",
        "",
    ])
    for pl in catalog.get("pipeline_bypasses", []):
        cap = pl.get("capacity_mbpd") or pl.get("capacity_kbpd", 0) / 1000
        lines.append(f"- **{pl['id']}**: {cap:.2f} mb/d equiv — avoids {pl.get('avoids', [])}")
    lines.extend([
        "",
        "## Next steps",
        "",
        "1. Export AIS positions from desk page N to `research/output/ais_snapshot.json`",
        "2. Integrate IMF PortWatch transit counts",
        "3. Compare Malacca/Hormuz ratio vs EIA baseline",
        "4. Track Fujairah vs Hormuz tanker origin split",
        "",
        "Full analysis: `docs/research/CHOKEPOINTS_ROUTES.md`",
    ])
    return "\n".join(lines) + "\n"


def main() -> int:
    out_dir = ensure_output()
    catalog = load_catalog()

    snapshot_path = None
    if "--snapshot" in sys.argv:
        i = sys.argv.index("--snapshot")
        if i + 1 < len(sys.argv):
            snapshot_path = Path(sys.argv[i + 1])

    if snapshot_path and snapshot_path.is_file():
        vessels = json.loads(snapshot_path.read_text(encoding="utf-8"))
        counts = count_in_zones(vessels, catalog)
        (out_dir / "chokepoint_counts.json").write_text(
            json.dumps(counts, indent=2), encoding="utf-8"
        )
        print(json.dumps(counts, indent=2))
    else:
        report = demo_report(catalog)
        path = out_dir / "chokepoints_report.md"
        path.write_text(report, encoding="utf-8")
        print(f"Catalog report -> {path}")
        print("TIP: add cache/ais.key and export AIS snapshot for live counts")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
