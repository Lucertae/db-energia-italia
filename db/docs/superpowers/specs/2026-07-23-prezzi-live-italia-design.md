# Design: Prezzi live / economici Italia (approccio A)

Date: 2026-07-23  
Status: draft — awaiting user review  
Scope: tutto ciò che manca ancora sulla parte economica/prezzi, **solo fonti scaricabili in automatico**.

## Goal

Avere sotto `db/mercati-italia/sources/prezzi_live/` un pacchetto **aggiornabile** di prezzi economici IT (near-real-time / daily), con uno script unico di refresh, senza scrape UI GME per MI/MSD.

## Non-goals (restano gap / manuali)

- GME MI / MSD / MB yearly ZIP o Download UI
- GME MGP Anno2007
- GSE Atlaimpianti
- EUA futures tick-by-tick a pagamento
- PSV “exchange live” se non esposto da fonte pubblica gratuita stabile

## Architecture

```
db/mercati-italia/sources/prezzi_live/
  README.txt
  manifest.json                 # last run status per feed
  electricity/
    entsoe_day_ahead_it_zones_latest.csv   # YTD / rolling window
    ember_italy_wholesale_daily.csv        # extract IT from Ember daily
  gas_indices/
    arera_indici_latest.csv                # refresh Portale Offerte indices
  fuels/
    sisen_weekly_prices_latest.csv
    sisen_monthly_prices_latest.csv
  carbon/
    eex_eua_auction_latest.xlsx            # newest year file + pointer
  snapshot.json                            # compact “now” board for all feeds

db/scripts/harvest_prezzi_live.py          # single entrypoint
```

Reuse existing harvesters where possible (call into or copy proven URL patterns from `harvest_priority_gaps.py`, `harvest_sisen_opendata.py`, `fill_eua_mase.py`, ENTSO-E client).

## Feeds (in scope)

| Feed | Source | Granularity | Output |
|------|--------|-------------|--------|
| Day-ahead EE IT zones | ENTSO-E Transparency (`entsoe.key`) | hourly, zones IT | `electricity/entsoe_day_ahead_*.csv` |
| Wholesale EE IT | Ember daily CSV (public) | daily | `electricity/ember_italy_wholesale_daily.csv` |
| Indici PUN/PSV/PE/… | ARERA Portale Offerte public CSV | as published | `gas_indices/arera_indici_latest.csv` |
| Carburanti | SISEN open-data API | weekly / monthly | `fuels/sisen_*.csv` |
| EUA auction | EEX public auction-report | annual file, refresh current year | `carbon/eex_eua_auction_*.xls(x)` |

## Refresh behaviour

```powershell
python db/scripts/harvest_prezzi_live.py
python db/scripts/harvest_prezzi_live.py --electricity-only
```

- Idempotent: skip unchanged files when size/schema OK unless `--force`
- Write `manifest.json` with timestamp, status, row counts
- Write `snapshot.json` with latest date and latest value(s) per feed for quick “live board”
- Fail soft per feed (one failure must not abort others)
- Rate-limit: ENTSO-E polite sleeps; no hammering

## ENTSO-E day-ahead specifics

- Use existing `entsoe-italia/entsoe.key` and domain mapping already used in `harvest_all_italia.py`
- Pull a **rolling window** (e.g. last 90 days → today+1 for published DA) into `prezzi_live`, not a full re-harvest of all history (history already under `entsoe-italia/data/`)
- Columns: datetime (Europe/Rome), zone/EIC, price EUR/MWh

## Docs updates

- `db/GAPS.md`: mark prezzi_live feeds as covered; keep MI/MSD/2007 blocked
- `db/mercati-italia/METADATI.txt`: section `sources/prezzi_live/`
- Short `prezzi_live/README.txt`

## Success criteria

1. One command refreshes all automatic price feeds without interactive UI
2. `snapshot.json` shows a non-empty latest stamp for EE, ARERA indices, SISEN fuels, EUA
3. No secrets committed; ENTSO key stays gitignored
4. GAPS.md distinguishes automatic vs still-manual price gaps

## Out of this design (later)

- Scheduler/cron or Cursor loop for continuous live
- Dashboard UI
- GME session download for MI
