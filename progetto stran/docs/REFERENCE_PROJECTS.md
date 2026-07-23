# Reference projects — integrazione STRAN

**Registro machine-readable:** `config/reference_projects.json`  
**Catalogo UI + fonti dati:** [`../../reference-projects/README.md`](../../reference-projects/README.md)

Tutti i **30** progetti Bloomberg / ops desk del catalogo sono registrati nel desk.

## Stato integrazione

| Stato | Significato | Progetti |
|-------|-------------|----------|
| **integrated** | Modulo bridge attivo | pysystemtrade, entsoe-py (via harvest) |
| **partial** | Feed/API importati in harvest | World Monitor, GlobeOps, mkt, pftui, triphopp, OpenBB, OBSYD, OpenSanctions |
| **adapter_off** | Adapter registrato, modulo disabilitato | gridstatus, herbie, findatapy, epftoolbox |
| **reference** | Catalogo + pattern UI/dati, no adapter in-process | resto |

## Metadati operativi (`ops`)

Ogni progetto ha un blocco `ops` in `reference_projects.json`:

| Campo | Valori | Significato |
|-------|--------|-------------|
| `data_portal` | URL | Portale/API dati principale (no GitHub) |
| `data_sources` | path | Catalogo feed/fonti estratto dal codice |
| `data_mode` | live · mixed · batch · static · on_demand · library | Tipo di ingest |
| `needs_map` | true/false | UI richiede canvas geo/spaziale |
| `map_kind` | globe · maritime · adsb · energy · chart · orderbook · workspace · graph · tui · none | Tipo mappa |
| `refresh_sec` | secondi o null | Intervallo poll tipico |
| `refresh_label` | testo | Descrizione refresh (più precisa del solo numero) |

Matrice completa: [`../../reference-projects/ops-matrix.md`](../../reference-projects/ops-matrix.md)

Sulla pagina **X ING → tab REF** le colonne sono: **MODE · MAP · REFRESH**.

## Dove compare nel desk

| Componente | Ruolo |
|------------|--------|
| `config/reference_projects.json` | Master list 30 progetti + link schede |
| `config/modules.json` → `external_adapters` | Tutti i 30 + stack legacy (findatapy, nautilus…) |
| `config/data_sources.json` | Fonti ingestibili (19–30 gap fillers + stack esistente) |
| `scripts/desk_harvest/live_streams.json` | Stream live con campo `ref` → progetto sorgente |
| `scripts/desk_harvest/import_wm_feeds.py` | RSS World Monitor + GlobeOps |
| `scripts/desk_harvest/ref_free_feeds.json` | RSS free tier (mkt, OpenBB, pftui…) |
| `cache/ingest/manifest.json` | Sezione **REF** (30 voci) via `build_ingest_manifest.py` |
| Pagina **X ING** (`world_clocks.exe`) | Tab REF + pannello **FILTER:** (digita per cercare, Esc cancella) |

## Rigenerare manifest

```powershell
cd "progetto stran"
python scripts\desk_harvest\apply_reference_portals.py
python scripts\desk_harvest\build_ingest_manifest.py
```

## Abilitare adapter (es. gridstatus, herbie)

1. `pip install gridstatus` o `pip install herbie-data`
2. In `config/modules.json` imposta `"enabled": true` su `gridstatus_harvest` / `herbie_harvest`
3. `python scripts\spine_build.py`

Vedi anche `docs/STACK_OPEN_SOURCE.md` e `docs/MODULES.md`.
