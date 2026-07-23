# Herbie

- **Fonti dati:** [NOAA NOMADS/NODD GRIB](https://nomads.ncep.noaa.gov/) · [elenco completo](../data-sources/22-herbie.md)
- **Docs:** https://blaylockbk.github.io/Herbie/
- **Stack:** Python, xarray
- **Licenza:** MIT

## Screenshot UI

*Libreria ingestion NWP — nessuna UI bundled. Usata in pipeline meteo → energia (STRAN Fase 2).*

## Dati free / open (ingestion)

**Elenco completo fonti dati (uno per uno):** [data-sources/22-herbie.md](../data-sources/22-herbie.md)

Download modelli numerici **senza costo** da mirror pubblici.

| Modello | Uso desk |
|---------|----------|
| **HRRR, RAP, GFS, NAM** | Forecast US high-res |
| **ECMWF IFS** | Open data tier globale |
| **ICON, GEM, NBM, RRFS** | Europa / Canada / blend |

| Host | Note |
|------|------|
| **NOMADS, NODD (AWS/GCP/Azure)** | NOAA open data |
| **ECMWF open portal** | Tier gratuito |
| **Pando Archive (Utah)** | Archive storico |

**Cosa rubare per STRAN:** pipeline Herbie → atlite → capacity factors; sostituisce fetch meteo ad hoc in harvest.
