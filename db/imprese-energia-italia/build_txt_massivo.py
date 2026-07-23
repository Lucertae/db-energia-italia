#!/usr/bin/env python3
"""Build aziende-energetiche-it.txt with maximum nominative coverage from ARERA (+ header map)."""
from __future__ import annotations

from pathlib import Path
import pandas as pd
import re

ROOT = Path(r"c:\Users\jecho\Desktop\terminal")
DER = ROOT / "db" / "imprese-energia-italia" / "derived"
SRC = ROOT / "db" / "imprese-energia-italia" / "sources"
OUT = ROOT / "aziende-energetiche-it.txt"

op = next(SRC.rglob("operatori-export*.xlsx"))
df = pd.read_excel(op)
soc = [c for c in df.columns if str(c).lower().startswith("societ")][0]
sett = [c for c in df.columns if "settori" in str(c).lower() or "attivit" in str(c).lower()][0]
piva = [c for c in df.columns if "iva" in str(c).lower()][0]
sede = [c for c in df.columns if "sede legale" in str(c).lower()][0]
df[sett] = df[sett].fillna("").astype(str)
df[soc] = df[soc].fillna("").astype(str).str.strip()
df[piva] = df[piva].fillna("").astype(str).str.strip()
df[sede] = df[sede].fillna("").astype(str).str.strip()

# drop empty names
df = df[df[soc].str.len() > 1].copy()

def mask(pat: str):
    return df[sett].str.contains(pat, case=False, regex=True)

buckets = {
    "PRODUZIONE ENERGIA ELETTRICA (ARERA a)": mask(r"a\)\s*produzione"),
    "TRASMISSIONE ENERGIA ELETTRICA (ARERA b)": mask(r"b\)\s*trasmissione"),
    "DISPACCIAMENTO (ARERA c)": mask(r"c\)\s*dispacci"),
    "DISTRIBUZIONE ENERGIA ELETTRICA (ARERA d)": mask(r"d\)\s*distribuzione dell.energia elettrica"),
    "MISURA ENERGIA ELETTRICA (ARERA e)": mask(r"e\)\s*misura dell.energia elettrica"),
    "INGROSSO ENERGIA ELETTRICA (ARERA f)": mask(r"f\)\s*acquisto e vendita all.ingrosso dell.energia elettrica"),
    "VENDITA EE MAGGIOR TUTELA (ARERA h)": mask(r"h\)\s*vendita.*maggior tutela"),
    "VENDITA EE MERCATO LIBERO (ARERA i)": mask(r"i\)\s*vendita ai clienti liberi"),
    "DISTRIBUZIONE GAS (ARERA p)": mask(r"p\)\s*distribuzione del gas"),
    "MISURA GAS (ARERA q)": mask(r"q\)\s*misura del gas"),
    "INGROSSO GAS (ARERA r)": mask(r"r\)\s*acquisto e vendita all.ingrosso del gas"),
    "VENDITA GAS TUTELA/UI (ARERA s)": mask(r"s\)\s*vendita di gas naturale ai clienti finali nel servizio di tutela"),
    "VENDITA GAS MERCATO LIBERO (ARERA t)": mask(r"t\)\s*vendita di gas naturale ai clienti finali a condizioni di libero"),
    "PRODUZIONE ENERGIA TERMICA / TELERISCALDAMENTO": mask(r"Produzione di energia termica"),
    "DISTRIBUZIONE ENERGIA TERMICA / TELERISCALDAMENTO": mask(r"Distribuzione di energia termica"),
}

# also load dedicated venditori sheets (may have cleaner web/contacts)
vend_ee = pd.read_excel(next(SRC.rglob("export-mercato-vend*.xlsx")))
vend_gas = pd.read_excel(next(SRC.rglob("export-gas-vend*.xlsx")))

lines: list[str] = []
lines.append("aziende energetiche it — anagrafica MASSIVA + mappa ecosistema")
lines.append("Generato: 2026-07-23")
lines.append("Fonte primaria nominativi: ARERA Anagrafiche Operatori / Venditori (export 22/07/2026)")
lines.append("Open data Camere/Movimprese = stock ATECO; qui sotto ragioni sociali regolate.")
lines.append("")
lines.append("TOTALE OPERATORI ARERA UNICI (P.IVA): " + str(df[piva].nunique()))
for title, m in buckets.items():
    lines.append(f"  - {title}: {int(m.sum())}")
lines.append("")
lines.append("Per PMI installatori (ATECO 43.21/43.22) non in ARERA: Registro Imprese —")
lines.append("vedi db/imprese-energia-italia/README.md (mappa ATECO).")
lines.append("")
lines.append("=" * 80)
lines.append("A) MAPPA STRATEGICA (big / sistema) — sintesi")
lines.append("=" * 80)
lines.append("Majors: Eni, Enel, GSE, Edison, Plenitude, Engie, EPH, Sorgenia, Erg, Saras,")
lines.append("  API/IP, Q8, ISAB, Saipem, Maire/Tecnimont")
lines.append("Multiutility: A2A, Hera, Iren, Acea, AGSM AIM, Dolomiti, Alperia, CVA, Estra, Ascopiave")
lines.append("Reti: Terna, Snam, Italgas, 2i Rete Gas, e-distribuzione, Unareti, Areti, Ireti, Inrete,")
lines.append("  Edyna, SET, Deval, Medea, Toscana Energia, Centria, AcegasApsAmga, V-Reti, DEA")
lines.append("O&M/OEM: Ansaldo Energia, Nuovo Pignone/Baker Hughes, Siemens Energy, GE Vernova,")
lines.append("  ABB, Schneider, CESI, Sirti, Webuild, Bonatti, SICIM, Rosetti Marino")
lines.append("Mappa regionale dettagliata storica: sezioni precedenti in git / piani db/docs")
lines.append("  (il volume nominativo ARERA è sotto — migliaia di società).")
lines.append("")

seen_global: set[str] = set()

def emit_block(title: str, frame: pd.DataFrame, name_col: str, piva_col: str | None, sede_col: str | None):
    lines.append("=" * 80)
    lines.append(f"B) {title}")
    lines.append("=" * 80)
    # dedupe by piva if available else name
    rows = []
    local_seen = set()
    for _, r in frame.iterrows():
        name = str(r[name_col]).strip()
        if len(name) < 2:
            continue
        key = str(r[piva_col]).strip() if piva_col and pd.notna(r.get(piva_col)) else name.upper()
        if not key or key in local_seen:
            continue
        local_seen.add(key)
        seen_global.add(key)
        sd = ""
        if sede_col and sede_col in r and pd.notna(r[sede_col]):
            sd = str(r[sede_col]).replace("\n", " ").strip()
            if len(sd) > 90:
                sd = sd[:87] + "..."
        piv = str(r[piva_col]).strip() if piva_col else ""
        if piv and piv.lower() != "nan":
            if sd:
                rows.append(f"{name} | P.IVA {piv} | {sd}")
            else:
                rows.append(f"{name} | P.IVA {piv}")
        else:
            rows.append(name)
    rows.sort(key=lambda x: x.upper())
    lines.append(f"# conteggio: {len(rows)}")
    lines.extend(rows)
    lines.append("")

for title, m in buckets.items():
    sub = df.loc[m, [soc, piva, sede]].drop_duplicates(subset=[piva])
    emit_block(title, sub, soc, piva, sede)

# venditori sheets (ensure all included even if tag parsing missed)
vee_name = [c for c in vend_ee.columns if "RAGIONE" in str(c).upper() or "SOCI" in str(c).upper()][0]
vee_piva = [c for c in vend_ee.columns if "IVA" in str(c).upper()][0]
vee_com = None
for c in vend_ee.columns:
    if "COMUNE" in str(c).upper():
        vee_com = c
        break
emit_block(
    "VENDITORI EE MERCATO LIBERO — export dedicato ARERA (conferma)",
    vend_ee,
    vee_name,
    vee_piva,
    vee_com,
)

vg_name = [c for c in vend_gas.columns if "RAGIONE" in str(c).upper() or "SOCI" in str(c).upper()][0]
vg_piva = [c for c in vend_gas.columns if "IVA" in str(c).upper()][0]
emit_block(
    "VENDITORI GAS — export dedicato ARERA (conferma)",
    vend_gas,
    vg_name,
    vg_piva,
    None,
)

# residual energy-related not already heavily covered? optional: all operators with energia keywords
energy_kw = re.compile(
    r"elettric|gas naturale|teleriscald|energia termica|distribuzione del gas|"
    r"produzione dell.energia|vendita ai clienti|ingrosso dell.energia|ingrosso del gas|"
    r"misura dell.energia|misura del gas|dispacci|trasmissione",
    re.I,
)
resid_mask = df[sett].map(lambda x: bool(energy_kw.search(x)))
# exclude already listed pivas in buckets
already = set()
for m in buckets.values():
    already.update(df.loc[m, piva].astype(str))
resid = df.loc[resid_mask & ~df[piva].astype(str).isin(already), [soc, piva, sede]].drop_duplicates(subset=[piva])
if len(resid):
    emit_block("ALTRI OPERATORI ARERA CON ATTIVITA ENERGY-RELATED", resid, soc, piva, sede)

lines.append("=" * 80)
lines.append("NOTE FINALI")
lines.append("=" * 80)
lines.append(f"Chiavi uniche emesse (P.IVA/nome): {len(seen_global)}")
lines.append("Fonte: ARERA https://www.arera.it/area-operatori/ricerca-operatori")
lines.append("CSV mirror: db/imprese-energia-italia/derived/")
lines.append("ATECO installatori/O&M (43.21/43.22 ecc.) richiedono Registro Imprese — non in ARERA.")
lines.append("")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"Wrote {OUT} lines={len(lines)} bytes={OUT.stat().st_size}")
