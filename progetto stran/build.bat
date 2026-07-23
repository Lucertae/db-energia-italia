@echo off
cd /d "%~dp0"
gcc -Os -s -municode -mwindows -Isrc -o world_clocks.exe ^
  src/main.c src/common.c src/astro.c src/time.c src/solar.c src/moon.c ^
  src/sessions.c src/overnight.c src/desk.c src/arena.c src/signal.c ^
  src/ingest.c src/ingest_inet.c src/ingest_curl.c   src/ingest_stooq.c src/ingest_eia.c src/ingest_entsoe.c   src/ingest_crypto.c src/ingest_ais.c src/ingest_sole.c src/ingest_libero.c src/ingest_intel.c src/keys.c ^
  src/sources.c src/fetch_pool.c src/histdb.c src/dcf.c src/fin.c src/glossary.c src/corr.c src/series.c src/chart.c ^
  src/market.c src/energy.c src/companies.c src/production.c src/countries.c src/map_canvas.c src/world_map.c ^
  src/ships.c src/chokepoints.c src/spine.c src/modules.c src/sole.c src/weather.c src/crypto.c src/systemic.c src/risk.c src/catalog.c src/pages.c src/data.c ^
  src/ops.c src/lab.c src/sig.c src/gas.c src/forcing.c src/qa.c src/intel.c src/desk_panels.c src/ingest_view.c src/keys_view.c src/map_layers.c src/map_view.c src/globe_view.c ^
  -lgdi32 -luser32 -lwinhttp -lwininet -lm
if %ERRORLEVEL% EQU 0 (
    echo Build OK: world_clocks.exe
) else (
    echo Build failed.
    exit /b 1
)
