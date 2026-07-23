# Mercati Italia

DB #5 — mercati elettrici **GME**, gas **ENTSOG/SNAM**, incentivi **GSE**, **Ember** (**~1.0 GB**).

## Refresh

```powershell
python db/mercati-italia/scripts/harvest_all.py
```

I file GSE sono anche scaricabili da URL dirette `opendata.gse.it/Lists/DataSetGSEPubblica/…` (non solo postback).  
Scheda completa: [`METADATI.txt`](METADATI.txt)

## Contenuto

| Sorgente | Path | Cosa |
|----------|------|------|
| GME MGP | `sources/gme/mgp_storici/` | Zip/xlsx 2004–2006 + 2008–2026 (~597 MB). **Manca 2007** (server) |
| ENTSOG/SNAM | `sources/entsog_snam/` | Flussi 2022–2026 + mensile 2021-02…12 + punti |
| GSE open data | `sources/gse/` | ~280 MB: Conto Energia, FER, TEE, biometano, isole, CB/CV… |
| Ember | `sources/ember/` | `italy_yearly.csv` + `italy_monthly.csv` (+ full long) |
| AGSI | `sources/agsi/` | Bloccato senza API key GIE |

Catalogo harvest: `catalog.csv`. Scheda completa: `METADATI.txt`.
