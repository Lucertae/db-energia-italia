# gridstatus

- **Fonti dati:** [US/Canada ISO + EIA](https://www.gridstatus.io/) · [elenco completo](../data-sources/20-gridstatus.md)
- **Web UI:** https://www.gridstatus.io
- **Docs:** https://opensource.gridstatus.io
- **Stack:** Python
- **Licenza:** LGPL-3.0

## Screenshot UI

*Libreria dati; visualizzazione su [gridstatus.io](https://www.gridstatus.io).*

## Dati free / open (ingestion)

**Elenco completo fonti dati (uno per uno):** [data-sources/20-gridstatus.md](../data-sources/20-gridstatus.md)

API Python uniforme per **ISO nordamericani** — complemento a ENTSO-E per desk multi-mercato.

| ISO | Dati tipici |
|-----|-------------|
| **CAISO, ERCOT, PJM, MISO, SPP** | LMP, load, renewables, outages |
| **ISONE, NYISO, IESO, AESO** | Prezzi, fuel mix, interface flows |
| **EIA** | Generation fuel mix US aggregate |

Molti endpoint pubblici senza key; alcuni richiedono credenziali (vedi `.env.template` nel repo).

**Cosa rubare per STRAN:** adapter pattern unico per multi-ISO; health check per buchi dati TP/ISO.
