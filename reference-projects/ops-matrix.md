# Reference projects — matrice operativa

Live vs batch, mappa, frequenza aggiornamento. Sorgente: `progetto stran/config/reference_projects.json`.

| # | Progetto | Mode | Mappa | Tipo mappa | Refresh |
|---|----------|------|-------|------------|---------|
| 1 | **World Monitor** | mixed | sì | globe | API 30s–15min · RSS 15–60min · 56 layer map |
| 2 | **GlobeOps** | mixed | sì | globe | 7 API live 30s–15min · 97 RSS · ASCII map |
| 3 | **Energy Monitor** | mixed | sì | globe | WM energy variant · AIS/commodity 1–15min |
| 4 | **Oriza** | mixed | sì | workspace | RSS 15min · scrape batch · weather demo |
| 5 | **Fincept Terminal** | live | sì | workspace | Streaming per connector (API keys) |
| 6 | **TyphooN Terminal** | live | no | chart | WebSocket tick · GPU charts |
| 7 | **OpenBook** | live | sì | orderbook | Binance Futures WS @100ms depth |
| 8 | **rs_trader** | mixed | no | workspace | Live tick or CSV/Parquet replay |
| 9 | **Blackdesk** | live | no | tui | Yahoo poll · keyboard TUI |
| 10 | **mkt** | live | no | tui | Coinbase WS · REST 1–5min · no API key |
| 11 | **wickra-terminal** | live | no | chart | 514 indicators stream · TUI or web |
| 12 | **stocksTUI** | live | no | tui | yfinance + FRED poll |
| 13 | **pftui** | live | no | workspace | 19 sources · poll 5–60min · web dashboard |
| 14 | **OpenTerminalUI** | live | no | workspace | Multi-chart shell · provider poll |
| 15 | **triphopp Bloomberg** | live | no | workspace | FastAPI routers · macro/portfolio poll |
| 16 | **feremabraz Bloomberg** | static | no | chart | Simulated data only · no live feed |
| 17 | **OpenBB** | mixed | no | workspace | Provider-dependent · EOD to intraday |
| 18 | **egui-charts** | library | no | library | Host app defines data + refresh |
| 19 | **OBSYD** | live | sì | energy | ENTSO-E hourly DA · GIE gas daily · flows |
| 20 | **gridstatus** | live | no | energy | US ISO LMP/load · publish 5–60min |
| 21 | **Electricity Maps** | live | sì | globe | TSO parsers · carbon map 5–15min |
| 22 | **Herbie** | batch | no | none | NWP model cycles 1–6h · GRIB download |
| 23 | **Global Fishing Watch** | batch | sì | maritime | AIS grid · ~5 day lag · 4Wings API |
| 24 | **tar1090** | live | sì | adsb | readsb/dump1090 push · 1–2s tracks |
| 25 | **OpenSanctions** | batch | no | none | Daily crawler · yente API on query |
| 26 | **SpiderFoot** | on_demand | sì | graph | OSINT scan per target · 200+ modules |
| 27 | **IntelOwl** | on_demand | no | workspace | Analyzer run per IOC submit |
| 28 | **Rotki** | live | no | workspace | Exchange/on-chain sync · ~5min |
| 29 | **pysystemtrade** | mixed | no | chart | Daily futures bars · IB live optional |
| 30 | **Hummingbot** | live | no | none | 47 CEX/DEX connectors · WS order book |

## Legenda `data_mode`

| Mode | Significato |
|------|-------------|
| **live** | Feed streaming o poll continuo |
| **mixed** | Live API + RSS/batch insieme |
| **batch** | Download periodico o dataset statico |
| **static** | Dati simulati / demo |
| **on_demand** | Run su richiesta (scan, analisi) |
| **library** | Nessun feed bundled — dipende dall'host |

*Aggiornato automaticamente da `scripts/desk_harvest/apply_reference_ops.py`*
