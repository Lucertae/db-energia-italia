# TyphooN Terminal

- **Fonti dati:** [Alpaca + Kraken market APIs](https://docs.alpaca.markets/) · [elenco completo](../data-sources/06-typhoon-terminal.md)
- **Stack:** Rust, egui, wgpu (GPU charting)
- **Licenza:** Free personal use

## Screenshot UI

*Nessuno screenshot nel README GitHub. Build locale richiesta.*


## Dati free / open (ingestion)

**Elenco completo fonti dati (uno per uno):** [data-sources/06-typhoon-terminal.md](../data-sources/06-typhoon-terminal.md)


Da `docs/API_KEYS.md`:

### Senza API key

| Fonte | Dati |
|-------|------|
| **Kraken** (public) | Spot, xStocks, Futures OHLCV, depth, candles |
| **Yahoo Finance** | Extended hours watchlist |
| **SEC EDGAR** | Form 4 insider, filings |
| **ECB** | FX rates |
| **ForexFactory** | Calendario economico |
| **StockTwits** | Sentiment |
| **FINRA Reg SHO** | Short volume dark pool |
| **House Stock Watcher** | Congress trades (free) |
| **ntfy.sh** | Push notifications (no account) |
| **Matrix** | Community chat |

### Free tier con registrazione

| Fonte | Dati | Limite |
|-------|------|--------|
| **FRED** | Macro, yield curve | 120 req/min |
| **Alpaca** | IEX data + paper trading | 200 req/min |
| **Finnhub** | Ratings, earnings, news | 60/min |
| **FMP** | Fundamentals | 250/giorno |
| **Alpha Vantage** | Earnings | 25/giorno |
| **CryptoPanic** | Crypto news | Free tier |
| **QuiverQuant** | Congress trades | Free tier |

### Broker (trading, non solo dati)

Kraken, Alpaca — chiavi per ordini e account.
