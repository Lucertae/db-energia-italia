# Global Fishing Watch

- **Fonti dati:** [GFW 4Wings AIS API](https://globalfishingwatch.org/our-apis/) · [elenco completo](../data-sources/23-global-fishing-watch.md)
- **Map:** https://globalfishingwatch.org/map/
- **API docs:** https://globalfishingwatch.org/our-apis/documentation
- **Stack:** Python client, map web (4Wings)
- **Licenza:** Apache 2.0 (client)

## Screenshot UI

*Mappa pubblica su [globalfishingwatch.org/map](https://globalfishingwatch.org/map/).*

## Dati free / open (ingestion)

**Elenco completo fonti dati (uno per uno):** [data-sources/23-global-fishing-watch.md](../data-sources/23-global-fishing-watch.md)

Copertura **marittima** dedicata — complementa AIS generico di World Monitor.

| API | Dati |
|-----|------|
| **4Wings** | Fishing effort gridded, vessel presence, SAR |
| **Vessels** | Identity, registry, AIS metadata |
| **Events** | Fishing, encounters, port visits, loitering, AIS gaps |
| **Insights** | Storico attività per MMSI |

Token API gratuito con registrazione. Dati AIS globali + registri pubblici + rilevamenti SAR.

**Cosa rubare per STRAN:** eventi encounter/transshipment, gap detection AIS, layer pesca vs cargo vs tanker.
