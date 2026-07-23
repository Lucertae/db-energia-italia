# Hummingbot

- **Fonti dati:** [47 CEX/DEX connectors](https://hummingbot.org/exchanges/) · [elenco completo](../data-sources/30-hummingbot.md)
- **Docs:** https://hummingbot.org
- **Stack:** Python, Cython, Docker
- **Licenza:** Apache 2.0

## Screenshot UI

![Hummingbot](https://github.com/user-attachments/assets/3213d7f8-414b-4df8-8c1b-a0cd142a82d8)

## Dati free / open (ingestion)

**Elenco completo fonti dati (uno per uno):** [data-sources/30-hummingbot.md](../data-sources/30-hummingbot.md)

Framework **market making / arb crypto** — 140+ venue via connector standardizzati.

| Protocollo | Dati pubblici (no auth) |
|------------|-------------------------|
| **REST** | Order book snapshot, exchange info, ticker |
| **WebSocket** | Trades, order book diffs, funding (futures) |

| Tipo venue | Esempi |
|------------|--------|
| **CEX** | Binance, Coinbase, Kraken, OKX, Bybit… |
| **DEX (Gateway)** | Uniswap, PancakeSwap, Curve, Trader Joe… |

CLI + Docker; ecosystem Condor (Telegram), Hummingbot API, MCP bot.

**Cosa rubare per STRAN:** connector pattern REST/WS uniforme; funding rate / OI come segnale (come mkt).
