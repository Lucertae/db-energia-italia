#!/usr/bin/env python3
"""Load legend catalog (10 categories + 75 items) into PostGIS."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

try:
    import psycopg2
except ImportError:
    import subprocess

    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary", "-q"])
    import psycopg2

ROOT = Path(__file__).resolve().parents[1]
FILTRI = ROOT / "filtri-legenda-completa.json"

DSN = os.environ.get(
    "OIM_DSN",
    "host=127.0.0.1 port=5433 dbname=oim_italia user=oim password=oim",
)


def main() -> None:
    data = json.loads(FILTRI.read_text(encoding="utf-8"))
    conn = psycopg2.connect(DSN)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute("TRUNCATE legend_voce, legend_category CASCADE")
    for cat in data["categorie"]:
        cur.execute(
            "INSERT INTO legend_category(id, label_it, label_en, layer_oim) VALUES (%s,%s,%s,%s)",
            (cat["id"], cat["label_it"], cat.get("label_en"), cat.get("layer_oim") or ""),
        )
        for i, voce in enumerate(cat["voci"]):
            cur.execute(
                "INSERT INTO legend_voce(id, category_id, label_it, sort_order) VALUES (%s,%s,%s,%s)",
                (voce["id"], cat["id"], voce["label_it"], i),
            )
    cur.execute("SELECT count(*) FROM legend_category")
    n_cat = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM legend_voce")
    n_voce = cur.fetchone()[0]
    print(f"legend loaded: {n_cat} categories, {n_voce} voci")
    assert n_cat == 10 and n_voce == 75, (n_cat, n_voce)
    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
