# OPS DESK — strategia salto di qualità

**Stato:** 2026-07-07  
**Verdetto onesto:** il desk è un prototipo funzionante con API reali, non un giocattolo vuoto — ma **non è ancora un ops desk** perché manca la spina dorsale che lega dati, ricerca e UI.

---

## Cosa significa "non è un giocattolo"

| Già reale | Manca per essere serio |
|-----------|------------------------|
| FRED/ECB/ENTSO-E live | Un solo catalogo serie (oggi 5 copie divergenti) |
| 15 pagine analytics | Health ingest visibile + lag per fonte |
| Research layer Python | Output ricerca → runtime (segnali promossi) |
| PortWatch + AIS + RSS | Pipeline schedulata affidabile, non spawn ad hoc |
| 172 file in cache | Provenance, PIT, validazione prima del display |
| lac/math documentati | Spine integrato con `lac\hedge` e `math\data` |

---

## Architettura target

```
                    ┌─────────────────────────────────────┐
                    │  config/desk_spine.json              │
                    │  config/fx_manifest.json             │
                    │  config/modules.json                 │
                    └──────────────┬──────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
  desk_harvest/*            scripts/spine_build.py      bridge/*
  (fetch remoto)            spine_codegen.py            (moduli plugin)
         │                         │                         │
         └──────────── cache/ ─────┴──── config/signals.json ┘
                                   │
                    cache/spine/modules/*.json
                    cache/exports/pysystemtrade/
                                   ▼
                         world_clocks.exe (C)
                    OPS console | FX bridge panel | alerts
```

**Regola:** niente nuova serie nel C senza passare dal manifest.  
**Moduli:** aggiungere plugin in `config/modules.json` + `bridge/` — output in `cache/spine/modules/`.

---

## Fasi

### Fase 1 — Spine (completata)
- [x] `config/desk_spine.json` — manifest unificato
- [x] `scripts/spine_build.py` — health scan → `cache/spine/status.json`
- [x] `config/signals.json` — segnali promossi da ricerca
- [x] `src/spine.c` — loader + OPS console (PAGE_OPS)
- [x] Harvest intel non-bloccante (spawn async, reload da cache)
- [x] `config/fx_manifest.json` — schema FX canonico (base/quote)
- [x] `config/modules.json` — registry moduli plugin
- [x] `bridge/` — graph/carry + adapter pysystemtrade
- [x] `scripts/spine_codegen.py` — catalog + series_fred generated
- [x] `src/modules.c` — UI bridge panel su pagina FX
- [ ] Generare `sources.c` da manifest (elimina drift)
- [ ] Test harness + CI su spine_build

### Fase 2 — Dati veri
- [x] NGS/CRU via EIA public scrape (`eia_public_inventories.py`) — no API key
- [x] Bridge meteo→economia (open-meteo, HDD/CDD, ENSO, weather_signals)
- [x] Backtest PWR-02/PWR-01 su CSV power + Open-Meteo archive (`backtest_pwr_signals`)
- [ ] Promuovere segnali in `config/signals.json` solo se backtest passa
- [ ] Herbie/ERA5/atlite pipeline (NWP → capacity factors)
- [ ] EIA key opzionale per dati extra country-level
- [ ] Import `math\data\unified\prices_unified.csv` come spine job
- [ ] lac `status.json` + `spine_entsoe.yaml` nel health panel
- [ ] Point-in-time per macro (vintage DB)

### Fase 3 — Segnali
- [ ] `research/run_*.py` scrive `cache/spine/signals_candidate.json`
- [ ] Promozione manuale → `config/signals.json`
- [x] Metriche live GAS-01/02, MAR-02 in `spine_build.py` → OPS alerts

### Fase 4 — Ops UX
- [ ] Watchlist utente
- [ ] Staleness rosso su chart se serie > max_age
- [ ] Log errori ingest strutturato (`cache/spine/errors.log`)

---

## Metriche di successo

| Metrica | Oggi | Target |
|---------|------|--------|
| Cataloghi duplicati | 5 | 1 |
| Serie con health noto | 0% | 100% tier-1 |
| Segnali research in UI | 0 | ≥3 promossi |
| Tempo blocco UI su fetch | ~~fino 300s~~ → 0s harvest async | 0s (async) |
| Coverage DATI checklist | ~15% | 50% entro 6 mesi |

---

## Cosa NON fare

- Aggiungere pagine senza spine
- LLM dentro il terminale
- Correlare serie senza QA
- Duplicare catalogo in un altro file

Il salto di qualità è **governance dei dati + promozione segnali**, non più grafici.
