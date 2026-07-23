# Terna Italia

Database dedicato ai dati **Terna**.

Oggi: carico, IMCEI, settori, capacità (symlink/copia da `consumi-italia/sources/terna/`).

**Ancora da mettere:** tutti i **PDF** e i **dati semantici** su:
- incidenti di rete
- stato della rete
- avanzamento / sviluppo della rete (piani, cantieri, opere)

Vedi `METADATI.txt` (sezioni 1 e 6) e voci `catalog.csv` con `status=planned`.

## Credenziali

Metti `client_id` / `client_secret` in `terna.credentials` (non commit — già in `.gitignore`).

## Refresh

```powershell
python db/terna-italia/scripts/harvest_terna_api.py
python db/terna-italia/scripts/terna_total_load_backfill.py   # 2021-22 se rate-limit ok
```

## Contenuto tipico (già presente)

- `sources/total_load/` — carico orario
- `sources/imcei/` — indice consumi industriali
- `sources/industry_sector/`, `services_sector/`
- `sources/electrical_energy_*`, `renewable_source_capacity/`
- `sources/bilanci/` — bilanci ISPRA/Terna se presenti

## Contenuto previsto (vuoto / planned)

- `sources/pdf/` — documenti PDF Terna
- `sources/incidenti/` — eventi/incidenti di rete
- `sources/stato_rete/` — stato rete
- `sources/avanzamento_rete/` — avanzamento opere / piani di sviluppo
