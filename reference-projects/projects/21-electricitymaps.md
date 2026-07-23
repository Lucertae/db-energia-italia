# Electricity Maps

- **Fonti dati:** [379 zones · TSO parsers](https://app.electricitymaps.com/map/live) · [elenco completo](../data-sources/21-electricitymaps.md)
- **App:** https://app.electricitymaps.com
- **Stack:** Python parsers, community contrib
- **Licenza:** AGPL-3.0

## Screenshot UI

![Electricity Maps app](https://raw.githubusercontent.com/electricitymaps/electricitymaps-contrib/master/.github/images/electricity-maps-banner.png)

## Dati free / open (ingestion)

**Elenco completo fonti dati (uno per uno):** [data-sources/21-electricitymaps.md](../data-sources/21-electricitymaps.md)

**379 zone** configurate, **147 parser** open source. Dati da TSO e governi ufficiali.

| Tipo | Contenuto |
|------|-----------|
| **production** | Mix generazione per zona |
| **exchange** | Flussi cross-border |
| **price** | Spot / day-ahead dove disponibile |
| **carbon intensity** | gCO₂eq/kWh (flow-tracing su app) |

Parser rilevanti per STRAN: **ENTSOE**, **EIA**, **EMBER**, **IRENA**, **OPENELECTRICITY**.

**Cosa rubare per STRAN:** schema zone uniforme, parser contrib per colmare buchi ENTSO-E, carbon overlay su mappe energia.
