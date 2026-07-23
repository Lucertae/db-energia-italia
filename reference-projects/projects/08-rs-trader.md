# rs_trader

- **Fonti dati:** [Yahoo Finance + CSV/Parquet replay](https://finance.yahoo.com/) · [elenco completo](../data-sources/08-rs-trader.md)
- **Stack:** Rust 2024, Iced, wgpu, Polars, Tokio
- **Licenza:** —

## Screenshot UI

*Nessuno screenshot nel README. Architettura a plugin/pannelli Iced.*

## Dati free / open (ingestion)

**Elenco completo fonti dati (uno per uno):** [data-sources/08-rs-trader.md](../data-sources/08-rs-trader.md)


| Fonte | Dati | Note |
|-------|------|------|
| **CSV / Parquet** | OHLCV locale | Loader file |
| **Binance** | Market data | Connector menzionato |
| **Simulatori** | Paper trading | Locale |

Architettura workflow-centric: i **workflow nodes** accedono ai broker; le **UI panes** consumano solo il message bus. Estensibile a Rithmic, Hyperliquid, DXFeed via trait generici.

*Nessun catalogo connector documentato nel README — progetto in evoluzione.*
