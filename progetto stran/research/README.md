# OPS DESK — research layer

Pipeline separato dal terminale C per QA, pulizia, feature engineering e pre-analisi.

## Setup

```bat
pip install -r research\requirements.txt
```

## Desk C integration (automatic)

The terminal refreshes without AI:

| Component | Refresh | Source |
|-----------|---------|--------|
| `ingest_intel.c` | every 30 min | spawns harvest if cache stale |
| PortWatch CSV | 6 h | IMF ArcGIS (hormuz-tracker pattern) |
| RSS headlines | 6 h | **642 feeds** → `harvest_intel.py` + `desk_index.json` |
| Intel page | — | **N** — 8 categorie + eventi live USGS/GDACS/NOAA |
| AIS bbox counts | live | `ships_count_in_bbox` on page **N** |
| Rule brief | live | delta vs 30d baseline |

Build: included in `build.bat` (`chokepoints.c`, `ingest_intel.c`).

View: page **N** (SHIPS) — panel CHOKEPOINTS + HEADLINES.

## Run

```bat
python research\run_gas.py
python research\run_oil.py
```

Output in `research/output/`:
- `gas_report.md`, `gas_features_monthly.csv`, `gas_qa.json`
- `oil_report.md`, `oil_features_monthly.csv`

## Docs

- `docs/research/LITERATURA.md` — sintesi accademica + regole operative
- `SEGNALI_DA_STUDIARE.md` — ipotesi e stato validazione

## Inventari US (no API key)

```bat
python scripts\desk_harvest\eia_public_inventories.py
```

Scarica CRU + NGS da pagine pubbliche EIA (LeafHandler / hist HTML).  
API key opzionale solo per dati country-level avanzati.
