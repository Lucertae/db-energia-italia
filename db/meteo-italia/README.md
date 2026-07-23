# Meteo Italia

DB #6 — Open-Meteo Historical Weather per **12 città** e **7 zone ENTSO-E**, orario + giornaliero, con **pioggia / neve / precipitazioni**.

## Refresh

```powershell
python db/meteo-italia/scripts/harvest_open_meteo.py
python db/meteo-italia/scripts/harvest_open_meteo.py --force
# se rate-limit 429:
python db/meteo-italia/scripts/cooldown_harvest_meteo.py 1800
```

Scheda: [`METADATI.txt`](METADATI.txt)

## Contenuto

| Path | Cosa |
|------|------|
| `sources/meteo/<Citta>_<anno>.csv` | Orario città (schema ricco) |
| `sources/meteo/italy_cities_hourly_2015_2026.csv` | Merge orario completo |
| `sources/meteo/italy_cities_hourly_PARTIAL_rich.csv` | Merge parziale già scaricato |
| `sources/meteo_daily/` | Giornaliero: `rain_sum`, `snowfall_sum`, `precipitation_sum` |
| `sources/open_meteo_zones/` | Orario zone mercato |
| `sources/open_meteo_zones_daily/` | Giornaliero zone |

## Precipitazioni (unità)

| Campo | Significato |
|-------|-------------|
| `precipitation` | Totale (rain+showers+neve water-eq), mm |
| `rain` | Pioggia liquida, mm |
| `showers` | Rovescio, mm |
| `snowfall` | Neve, **cm** |
| `snow_depth` | Altezza manto, **m** |
| `*_sum` (daily) | Quantità giornaliere |

Più: weather_code WMO, umidità, dewpoint, pressione, nubi low/mid/high, vento+raffiche, SW/direct/diffuse/DNI, sunshine, ET0, suolo.

Periodo target: **2015 → oggi**.

## Alternative sources (no Open-Meteo)

When Open-Meteo returns 429, use NASA POWER + Meteostat:

```powershell
python db/meteo-italia/scripts/harvest_meteo_alt.py
```

| Path | Cosa |
|------|------|
| `sources/nasa_power_grid/` | Griglia nazionale daily (~1°) precip/temp/vento/solare |
| `sources/nasa_power_cities/` | 12 città daily |
| `sources/nasa_power_zones/` | 7 zone ENTSO daily |
| `sources/meteostat_stations/` | Stazioni osservative IT daily |
