# mkt

- **Fonti dati:** [Coinbase WS + Yahoo + FRED + DeFiLlama](https://docs.cloud.coinbase.com/advanced-trade-api/docs/welcome) · [elenco completo](../data-sources/10-mkt.md)
- **Stack:** Go, Bubbletea, Lipgloss
- **Licenza:** MIT

## Screenshot UI

*Nessuno screenshot nel repository GitHub. TUI 9 tab con 7 temi colore.*

## Dati free / open (ingestion)

**Elenco completo fonti dati (uno per uno):** [data-sources/10-mkt.md](../data-sources/10-mkt.md)


**Nessuna API key richiesta.**

| Fonte | Protocollo | Dati |
|-------|------------|------|
| **Coinbase Advanced Trade** | WebSocket | Crypto real-time, L2 book |
| **Coinbase Exchange** | REST | Candles, order book |
| **Yahoo Finance** | REST | Stocks, macro, options, earnings |
| **FRED** | REST CSV | Serie economiche (`FRED:` prefix) |
| **DeFiLlama** | REST | TVL per chain |
| **Binance Futures** | REST | Funding rate, open interest |
| **Yahoo / MarketWatch / CNBC** | RSS | News |
| **SEC EDGAR** | Atom RSS | Filing per ticker (8-K, 10-Q, 10-K) |

### Extra

- `ntfy.sh` / **Pushover** per alert (opzionale, free)
- `--listen` HTTP API read-only
- `mkt mcp` — MCP server per agenti
- `MKT_RECORD` — replay NDJSON per backtest alert
