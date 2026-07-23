# Socio-Italia

Popolazione, densità, PIL, lavoro — driver di domanda elettrica.

## Refresh

```powershell
python db/scripts/harvest_socio_italia.py
```

## Sorgenti

- `sources/eurostat/` — demo_pjan, densità NUTS, GDP, employment
- `sources/worldbank/` — SP.POP.*, GDP, unemployment, land area
- `sources/istat/` — comuni + SDMX popolazione (se API risponde)
- `sources/owid/` — population Italy

## Extra (PIL/suolo/mobilità/povertà)

```powershell
python db/scripts/harvest_territorio_mobilita.py
python db/scripts/harvest_ispra_mit_mobility.py
```

- `sources/eurostat_gva/` — VA/PIL NACE a10/a64, GDP/GVA NUTS2–3, reddito famiglie
- `sources/land_use/` — Eurostat land cover, WB land %, confini ISTAT (zip), OpenPolis geojson
- `sources/mobility/` — Eurostat road/rail/air, ISPRA flotta (tabelle), MIT porti/aereo (+ patenti regionali), OSM motorway count
- `sources/poverty/` — OWID PIP Italy + World Bank Gini/poverty/GNI
- Griglia meteo: `../meteo-italia/sources/open_meteo_grid/` (ritentare se Open-Meteo 429)
- Corine CLC pieno: download manuale CLMS (non in automatico)
