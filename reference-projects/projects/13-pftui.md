# pftui

- **Fonti dati:** [19 providers (Yahoo, CoinGecko, CFTC…)](https://pftui.com/) · [elenco completo](../data-sources/13-pftui.md)
- **Crate:** https://crates.io/crates/pftui
- **Sito:** https://pftui.com *(404 al momento)*
- **Stack:** Rust, Ratatui, Actix-web, TradingView widget

## Screenshot UI

*Nessuno screenshot scaricabile — repo non accessibile.*

Documentazione pubblica (crates.io): TUI 7 viste + web dashboard responsive.

## Dati free / open (ingestion)

**Elenco completo fonti dati (uno per uno):** [data-sources/13-pftui.md](../data-sources/13-pftui.md)


Da documentazione `DATA-AGGREGATION.md` (pubblicata):

| Fonte | Dati | Auth |
|-------|------|------|
| **Yahoo Finance** | Equity, ETF, FX, commodity | Nessuna key |
| **CoinGecko** | Crypto | Nessuna key |
| **Polymarket** | Prediction markets | Pubblico |
| **CFTC/Socrata** | COT positioning | Pubblico |
| **Alternative.me** | Fear & Greed | Pubblico |
| **BLS** | Serie economiche US | Pubblico |
| **World Bank** | Macro globale | Pubblico |
| **CME/COMEX** | Warehouse inventory | Pubblico |
| **RSS** | Headlines mercato | Pubblico |

19+ data source aggregate. CLI 100+ comandi con output JSON per agenti AI.
