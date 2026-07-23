# OPS DESK — struttura progetto

```
terminal/
  build.bat          # compila → world_clocks.exe
  run.bat            # avvia il desk
  world_clocks.exe   # binario (generato)
  cache/             # storico CSV FRED + eia.key
  src/               # sorgenti C (Win32/GDI)
  docs/              # documentazione
    DATA_STORICO.md  # catalogo dati storici da avere
    screenshots/     # catture UI (dev)
  scripts/           # snap.ps1, click.ps1 (test UI)
  test/              # ingest_test.c
  bin/               # eseguibili di test secondari
```

## Moduli in `src/`

| Area | File |
|------|------|
| App | `main.c` |
| UI core | `common`, `desk`, `pages`, `market`, `chart`, `energy`, `moon`, `solar`, `sessions`, `overnight`, `time`, `astro` |
| Dati | `data`, `series`, `sources`, `histdb`, `fetch_pool`, `signal`, `arena` |
| Ingest | `ingest`, `ingest_inet`, `ingest_curl`, `ingest_stooq`, `ingest_eia` |
| Dominio | `companies`, `production`, `dcf` |

## Build

```bat
build.bat
run.bat
```

L’app si aspetta `cache/` nella root (path relativi alla cwd).
