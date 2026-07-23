# Design: Pipeline aziende energia in crisi (Italia)

**Date:** 2026-07-23  
**Package:** `aziende-crisi-energia/` (standalone, zero dipendenza da `db/`)

## Goal

Produrre `output/aziende_energia_crisi.txt` (+ CSV/JSON) con imprese italiane energia/adiacenti in (A) procedura concorsuale o (B) distress pubblico, da fonti multiple con merge/dedup.

## Architecture

- Orchestratore `main.py` (ThreadPoolExecutor max 3).
- Ogni sorgente: sottoclasse di `sources.base.Source` → `fetch() -> list[Company]`.
- HTTP: rate limit ≥2s/dominio, UA identificativo, retry backoff, cache disco `cache/<sha256(url)>`.
- Dedup: P.IVA normalizzata; fallback rapidfuzz denominazione+provincia (>92).
- Enrichment: anagrafica locale opzionale da `../aziende-energetiche-it.txt` (P.IVA/provincia); openapi.it se chiave presente.
- Matching settore: ATECO target; altrimenti keyword su denominazione (`match=keyword` in NOTE).

## Sources

1. PVP giustizia — ricerca vendite / keyword energia  
2. Gazzetta Ufficiale Foglio inserzioni — lookback mesi  
3. MIMIT tavoli crisi attivi (+ monitoraggio)  
4. openapi.it Company API (skip se no key)  
5. AstaLegale / fallback Fallcoaste  
6. Google News RSS  
7. Unioncamere CNC stub (+ fallback GU/news misure protettive)  
8. Anagrafica locale ARERA (enrichment + filtro universo energia) — non inventa crisi

## Output row

`RAGIONE SOCIALE | P.IVA/CF | ATECO | PROVINCIA | STATO | FONTE | NOTE`

## Constraints

Robots/ToS, no hard crash su 0 risultati (ERROR + suggerimento selettori), CLI `--sources`, `--lookback-months`, `--no-cache`, `--ateco-only`.

## Disclaimer

Dati pubblici ≠ visura camerale. Verificare su registroimprese.it. GDPR: imprese ok; persone fisiche con base giuridica.
