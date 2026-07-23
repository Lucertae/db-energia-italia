#!/usr/bin/env python3
"""Generate SQL to load legend catalog into PostGIS."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILTRI = ROOT / "filtri-legenda-completa.json"
OUT = ROOT / "sql" / "02_legend.sql"


def esc(s: str) -> str:
    return s.replace("'", "''")


def main() -> None:
    data = json.loads(FILTRI.read_text(encoding="utf-8"))
    lines = [
        "TRUNCATE legend_voce, legend_category CASCADE;",
    ]
    n_voce = 0
    for cat in data["categorie"]:
        lines.append(
            "INSERT INTO legend_category(id, label_it, label_en, layer_oim) VALUES ("
            f"'{esc(cat['id'])}', '{esc(cat['label_it'])}', "
            f"'{esc(cat.get('label_en') or '')}', '{esc(cat.get('layer_oim') or '')}');"
        )
        for i, voce in enumerate(cat["voci"]):
            n_voce += 1
            lines.append(
                "INSERT INTO legend_voce(id, category_id, label_it, sort_order) VALUES ("
                f"'{esc(voce['id'])}', '{esc(cat['id'])}', '{esc(voce['label_it'])}', {i});"
            )
    lines.append(
        f"DO $$ BEGIN "
        f"ASSERT (SELECT count(*) FROM legend_category) = 10, 'expected 10 categories'; "
        f"ASSERT (SELECT count(*) FROM legend_voce) = 75, 'expected 75 voci'; "
        f"END $$;"
    )
    lines.append(
        "SELECT 'legend ok' AS status, "
        "(SELECT count(*) FROM legend_category) AS categories, "
        "(SELECT count(*) FROM legend_voce) AS voci;"
    )
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(data['categorie'])} cat, {n_voce} voci)")


if __name__ == "__main__":
    main()
