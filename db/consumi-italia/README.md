# Consumi Italia

DB #4 — consumi e bilanci energetici Italia (**~1.75 GB**).

## Refresh

```powershell
python db/consumi-italia/scripts/harvest_all.py
python db/consumi-italia/scripts/harvest_terna_api.py   # terna.credentials
```

Scheda completa: [`METADATI.txt`](METADATI.txt)

## Contenuto

| Sorgente | Path | Cosa |
|----------|------|------|
| ARERA domestici | `sources/arera/domestici/` | Prelievi medi kWh, geo, potenza (~zip multi-anno) |
| ARERA non domestici ATECO | `sources/arera/non_domestici_ateco/` | Clienti BT per ATECO |
| Terna/ISPRA bilanci | `sources/terna/bilanci/` | Elettricità per settore 1990–2024 |
| Terna API | `sources/terna/{imcei,industry_sector,services_sector,…}/` | Mensile industria/servizi/settori |
| Terna total-load | `sources/terna/total_load/` | 2023–2026 (~63 MB); 2021–22 via backfill se quota ok |
| Eurostat | `sources/eurostat/*_italy.csv` | Bilanci, prezzi, trade, stocks, SDG 07, GHG (32 file) |
| World Bank | `sources/worldbank/` | Indicatori energia IT |
| ISTAT | `sources/istat/` | Comuni + geojson limiti |
| OWID CO₂ | `sources/edgar/italy_owid_co2.csv` | Estratto Italy |

## Limiti

- Nessun nominativo azienda / POD.
- Credenziali in `terna.credentials` (non commit). Ruotare se esposte.
