#!/usr/bin/env python3
"""Harvest + summarize Italian energy enterprise lists (ARERA + ATECO map)."""
from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd
import urllib.request

ROOT = Path(r"c:\Users\jecho\Desktop\terminal\db\imprese-energia-italia")
SRC = ROOT / "sources"
OUT = ROOT / "derived"
OUT.mkdir(parents=True, exist_ok=True)

# --- ARERA operators ---
op_xlsx = next(SRC.rglob("operatori-export*.xlsx"))
df = pd.read_excel(op_xlsx)
# normalize columns
df.columns = [str(c).strip() for c in df.columns]
col_soc = [c for c in df.columns if c.lower().startswith("societ")][0]
col_settori = [c for c in df.columns if "settori" in c.lower() or "attivit" in c.lower()][0]
col_piva = [c for c in df.columns if "partita" in c.lower() or "iva" in c.lower()][0]
col_sede = [c for c in df.columns if "sede legale" in c.lower()][0]

df[col_settori] = df[col_settori].fillna("").astype(str)
# explode settori (often semicolon/comma separated)
all_tags = []
energy_mask = []
ENERGY_KEYS = [
    "elettric", "gas", "teleriscald", "energia", "distribuz", "trasmiss",
    "dispacci", "produzione", "vendita", "misura", "stoccaggio", "rigassif",
    "biometan", "idrogen",
]
for s in df[col_settori]:
    tags = re.split(r"[;|,/\n]+", s)
    tags = [t.strip() for t in tags if t.strip()]
    all_tags.extend(tags)
    low = s.lower()
    energy_mask.append(any(k in low for k in ENERGY_KEYS))

df["energy_related"] = energy_mask
energy = df[df["energy_related"]].copy()

# region from sede legale if present
def guess_region(sede: str) -> str:
    s = str(sede).upper()
    regions = [
        "VALLE D'AOSTA", "PIEMONTE", "LOMBARDIA", "TRENTINO", "ALTO ADIGE", "BOLZANO",
        "VENETO", "FRIULI", "LIGURIA", "EMILIA", "TOSCANA", "UMBRIA", "MARCHE",
        "LAZIO", "ABRUZZO", "MOLISE", "CAMPANIA", "PUGLIA", "BASILICATA", "CALABRIA",
        "SICILIA", "SARDEGNA",
    ]
    for r in regions:
        if r in s:
            return r
    # CAP-based rough? skip
    return "ND"

energy["regione_guess"] = energy[col_sede].map(guess_region)

# venditori
vend_ee = pd.read_excel(next(SRC.rglob("export-mercato-vend*.xlsx")))
vend_gas = pd.read_excel(next(SRC.rglob("export-gas-vend*.xlsx")))

tag_counts = Counter(all_tags).most_common(80)

# export
energy_out = energy[[col_soc, col_piva, col_settori, col_sede, "regione_guess"]].drop_duplicates()
energy_out.to_csv(OUT / "arera_operatori_energy_related.csv", index=False, encoding="utf-8-sig")
df[[col_soc, col_piva, col_settori, col_sede]].drop_duplicates().to_csv(
    OUT / "arera_operatori_ALL.csv", index=False, encoding="utf-8-sig"
)
vend_ee.to_csv(OUT / "arera_venditori_elettrico.csv", index=False, encoding="utf-8-sig")
vend_gas.to_csv(OUT / "arera_venditori_gas.csv", index=False, encoding="utf-8-sig")

summary = {
    "arera_operatori_total_rows": int(len(df)),
    "arera_operatori_unique_piva": int(df[col_piva].nunique()),
    "arera_energy_related_rows": int(len(energy)),
    "arera_energy_related_unique_piva": int(energy[col_piva].nunique()),
    "arera_venditori_elettrico_rows": int(len(vend_ee)),
    "arera_venditori_gas_rows": int(len(vend_gas)),
    "top_settori_tags": tag_counts[:50],
    "energy_by_regione_guess": energy["regione_guess"].value_counts().to_dict(),
    "sources": {
        "arera_operatori": str(op_xlsx.name),
        "note": "ARERA anagrafiche = operatori regolati energia/ambiente/acqua; non e Registro Imprese ATECO completo",
    },
}
(OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
print(json.dumps(summary, ensure_ascii=False, indent=2))

# --- Infocamere catalog: find ATECO D dataset pages ---
rdf_path = SRC / "catalog.rdf"
if not rdf_path.exists():
    urllib.request.urlretrieve(
        "https://opendata.marche.camcom.it/data/dcat-opendata-catalog.rdf", rdf_path
    )
text = rdf_path.read_text(encoding="utf-8", errors="ignore")
# titles containing Settore Ateco D
titles = re.findall(r"<dct:title[^>]*>([^<]*Ateco D[^<]*)</dct:title>", text)
print("ATECO D titles:", len(titles))
for t in titles[:15]:
    print(" -", t)
