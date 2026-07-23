# pysystemtrade

- **Fonti dati:** [IB live + Quandl/CSV futures](https://www.interactivebrokers.com/en/trading/ib-api.php) · [elenco completo](../data-sources/29-pysystemtrade.md)
- **Autore:** Rob Carver / pst-group
- **Stack:** Python, ib_async
- **Licenza:** GPL-3.0

## Screenshot UI

*Backend systematic trading — nessuna UI grafica. Export dati per desk esterni.*

## Dati free / open (ingestion)

**Elenco completo fonti dati (uno per uno):** [data-sources/29-pysystemtrade.md](../data-sources/29-pysystemtrade.md)

Framework **futures sistematici** — già nello stack STRAN (`cache/exports/pysystemtrade/`).

| Fonte | Dati |
|-------|------|
| **Interactive Brokers** | Live futures FX/commodity/index (account) |
| **Quandl / Nasdaq Data Link** | Storico futures (API key) |
| **CSV / Parquet** | File locali |
| **Instrument config** | Metadata futures bundled |

Backtest + produzione con regole Carver (forecast weights, position sizing, risk overlay).

**Cosa rubare per STRAN:** bridge export → spine modules; promozione segnali research solo dopo backtest pass.
