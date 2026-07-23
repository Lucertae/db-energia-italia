#!/usr/bin/env python3
from pathlib import Path
from collections import Counter
import json
import pandas as pd

SRC = Path(r"c:\Users\jecho\Desktop\terminal\db\imprese-energia-italia\sources")
OUT = Path(r"c:\Users\jecho\Desktop\terminal\db\imprese-energia-italia\derived")
OUT.mkdir(parents=True, exist_ok=True)

op = next(SRC.rglob("operatori-export*.xlsx"))
df = pd.read_excel(op)
soc = [c for c in df.columns if str(c).lower().startswith("societ")][0]
sett = [c for c in df.columns if "settori" in str(c).lower() or "attivit" in str(c).lower()][0]
piva = [c for c in df.columns if "iva" in str(c).lower()][0]
sede = [c for c in df.columns if "sede legale" in str(c).lower()][0]
s = df[sett].fillna("").astype(str)

patterns = {
    "a_produzione_ee": r"a\)\s*produzione",
    "b_trasmissione_ee": r"b\)\s*trasmissione",
    "c_dispacciamento": r"c\)\s*dispacci",
    "d_distribuzione_ee": r"d\)\s*distribuzione dell.energia elettrica",
    "e_misura_ee": r"e\)\s*misura dell.energia elettrica",
    "f_ingrosso_ee": r"f\)\s*acquisto e vendita all.ingrosso dell.energia elettrica",
    "h_tutela_ee": r"h\)\s*vendita.*maggior tutela",
    "i_libero_ee": r"i\)\s*vendita ai clienti liberi",
    "p_distribuzione_gas": r"p\)\s*distribuzione del gas",
    "q_misura_gas": r"q\)\s*misura del gas",
    "r_ingrosso_gas": r"r\)\s*acquisto e vendita all.ingrosso del gas",
    "s_tutela_gas": r"s\)\s*vendita di gas naturale ai clienti finali nel servizio di tutela",
    "t_libero_gas": r"t\)\s*vendita di gas naturale ai clienti finali a condizioni di libero",
    "termica_produzione": r"Produzione di energia termica",
    "termica_distribuzione": r"Distribuzione di energia termica",
}
counts = {k: int(s.str.contains(p, case=False, regex=True).sum()) for k, p in patterns.items()}

prod = df[s.str.contains(r"a\)\s*produzione", case=False, regex=True)][[soc, piva, sede, sett]]
prod.to_csv(OUT / "arera_produzione_energia_elettrica.csv", index=False, encoding="utf-8-sig")
dist_ee = df[s.str.contains(r"d\)\s*distribuzione dell.energia elettrica", case=False, regex=True)][[soc, piva, sede, sett]]
dist_ee.to_csv(OUT / "arera_distribuzione_ee.csv", index=False, encoding="utf-8-sig")
dist_gas = df[s.str.contains(r"p\)\s*distribuzione del gas", case=False, regex=True)][[soc, piva, sede, sett]]
dist_gas.to_csv(OUT / "arera_distribuzione_gas.csv", index=False, encoding="utf-8-sig")

(OUT / "arera_activity_counts.json").write_text(json.dumps(counts, indent=2, ensure_ascii=False), encoding="utf-8")
print(json.dumps(counts, indent=2, ensure_ascii=False))
print("exported producers", len(prod), "dso_ee", len(dist_ee), "dso_gas", len(dist_gas))
