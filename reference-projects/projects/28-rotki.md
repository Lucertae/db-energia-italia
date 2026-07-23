# Rotki

- **Fonti dati:** [Exchange + on-chain sync](https://docs.rotki.com/) · [elenco completo](../data-sources/28-rotki.md)
- **Sito:** https://rotki.com
- **Stack:** Python backend, Electron/Vue frontend
- **Licenza:** AGPL-3.0

## Screenshot UI

*Desktop app — screenshot su [rotki.com](https://rotki.com).*

## Dati free / open (ingestion)

**Elenco completo fonti dati (uno per uno):** [data-sources/28-rotki.md](../data-sources/28-rotki.md)

Portfolio **self-hosted** — on-chain + exchange. Gap: tracking DeFi oltre CoinGecko sparkline.

| Fonte | Dati |
|-------|------|
| **Ethereum + L2** | Balances, DeFi positions via RPC |
| **Bitcoin** | UTXO tracking |
| **Exchange APIs** | Binance, Kraken, Coinbase… (user keys) |
| **DeFi** | Aave, Uniswap, Compound decode |
| **CoinGecko** | Price oracles (free tier) |

Dati encrypted local-first. PnL accounting con regole configurabili.

**Cosa rubare per STRAN:** decode transazioni on-chain, multi-venue balance aggregation, report PnL.
