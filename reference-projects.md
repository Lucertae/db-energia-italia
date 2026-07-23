# Progetti di riferimento — terminal / Bloomberg / ops desk

> **Catalogo completo:** [`reference-projects/`](reference-projects/README.md) · **[Fonti dati uno per uno](reference-projects/data-sources/README.md)** · **[Matrice ops](reference-projects/ops-matrix.md)**

Raccolta di terminal Bloomberg / ops desk — **rimandi alle fonti dati**, non ai repo GitHub.

**Integrazione desk:** [`progetto stran/config/reference_projects.json`](progetto%20stran/config/reference_projects.json) — vedi [`progetto stran/docs/REFERENCE_PROJECTS.md`](progetto%20stran/docs/REFERENCE_PROJECTS.md).

---

## Ops / geo / energia

| Progetto | Portale dati | Catalogo | Note |
|----------|--------------|----------|------|
| **World Monitor** | [WM data catalog](https://www.worldmonitor.app/docs/data-sources) | [elenco](reference-projects/data-sources/01-world-monitor.md) | RSS 626+ feed, 56 map layers, AIS, GDELT, live APIs — import via import_wm_feeds.py |
| **GlobeOps** | [GlobeOps live desk](https://globeops.cloud/) | [elenco](reference-projects/data-sources/02-globeops.md) | 97 RSS + 7 API live, CRT terminal UI — feed-sources.ts in intel harvest |
| **Energy Monitor** | [Energy Monitor](https://energy.worldmonitor.app/) | [elenco](reference-projects/data-sources/03-energy-monitor.md) | Fork WM energy variant — pipeline, AIS, chokepoint, commodity |
| **Oriza** | [EIA Open Data + commodity RSS](https://www.eia.gov/opendata/) | [elenco](reference-projects/data-sources/04-oriza.md) | Commodity desk gas/crude/metals — RSS EIA, scrape patterns |

## Bloomberg / trading desktop

| Progetto | Portale dati | Catalogo | Note |
|----------|--------------|----------|------|
| **Fincept Terminal** | [Fincept connectors & data API](https://fincept.co/) | [elenco](reference-projects/data-sources/05-fincept-terminal.md) | Qt6 desktop Bloomberg-like — 100+ connector pattern |
| **TyphooN Terminal** | [Alpaca + Kraken market APIs](https://docs.alpaca.markets/) | [elenco](reference-projects/data-sources/06-typhoon-terminal.md) | Rust egui GPU charting, Alpaca + Kraken |
| **OpenBook** | [Binance Futures WebSocket depth](https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams) | [elenco](reference-projects/data-sources/07-openbook.md) | Binance Futures order book heatmap — microstructure UI |
| **rs_trader** | [Yahoo Finance + CSV/Parquet replay](https://finance.yahoo.com/) | [elenco](reference-projects/data-sources/08-rs-trader.md) | Rust Iced modular panels, Binance + CSV/Parquet |

## Keyboard-first / TUI

| Progetto | Portale dati | Catalogo | Note |
|----------|--------------|----------|------|
| **Blackdesk** | [Yahoo Finance poll](https://finance.yahoo.com/) | [elenco](reference-projects/data-sources/09-blackdesk.md) | Go Bubble Tea keyboard-first research terminal |
| **mkt** | [Coinbase WS + Yahoo + FRED + DeFiLlama](https://docs.cloud.coinbase.com/advanced-trade-api/docs/welcome) | [elenco](reference-projects/data-sources/10-mkt.md) | TUI no-key: Coinbase, Yahoo, FRED, DeFiLlama, Binance funding/OI |
| **wickra-terminal** | [Exchange REST/WS (514 indicators)](https://api.binance.com/) | [elenco](reference-projects/data-sources/11-wickra-terminal.md) | TUI or web renderer, 514 indicators streaming |
| **stocksTUI** | [yfinance + FRED API](https://fred.stlouisfed.org/docs/api/fred/) | [elenco](reference-projects/data-sources/12-stockstui.md) | Python Textual — Yahoo, FRED, options |
| **pftui** | [19 providers (Yahoo, CoinGecko, CFTC…)](https://pftui.com/) | [elenco](reference-projects/data-sources/13-pftui.md) | 19+ data sources — COT, Fear&Greed, Polymarket |

## Self-hosted full-stack

| Progetto | Portale dati | Catalogo | Note |
|----------|--------------|----------|------|
| **OpenTerminalUI** | [Multi-provider market data shell](https://finance.yahoo.com/) | [elenco](reference-projects/data-sources/14-openterminalui.md) | Bloomberg/Refinitiv shell — multi-chart, OMS, AI agent |
| **triphopp Bloomberg** | [FastAPI routers · macro/FRED/yfinance](https://fred.stlouisfed.org/) | [elenco](reference-projects/data-sources/15-triphopp-bloomberg.md) | Next.js + FastAPI keyboard desk — macro, portfolio, options routers |
| **feremabraz Bloomberg** | [Simulated demo · Yahoo-style quotes](https://finance.yahoo.com/) | [elenco](reference-projects/data-sources/16-feremabraz-bloomberg.md) | UI clone — simulated data only |
| **OpenBB** | [OpenBB Platform providers](https://docs.openbb.co/) | [elenco](reference-projects/data-sources/17-openbb.md) | ODP providers — yfinance, SEC, FRED, EIA, IMF, MCP |

## Librerie chart / UI

| Progetto | Portale dati | Catalogo | Note |
|----------|--------------|----------|------|
| **egui-charts** | [Host app defines feeds](https://userfrm.github.io/egui-charts/) | [elenco](reference-projects/data-sources/18-egui-charts.md) | Rust chart library — future stack beyond GDI |

## Energia / meteo / power grid

| Progetto | Portale dati | Catalogo | Note |
|----------|--------------|----------|------|
| **OBSYD** | [ENTSO-E · Fraunhofer · GIE gas API](https://obsyd.dev/api/docs) | [elenco](reference-projects/data-sources/19-obsyd.md) | EU power desk ENTSO-E + Fraunhofer + GIE gas — anomaly radar |
| **gridstatus** | [US/Canada ISO + EIA](https://www.gridstatus.io/) | [elenco](reference-projects/data-sources/20-gridstatus.md) | US ISO LMP/load — adapter gridstatus_harvest (off) |
| **Electricity Maps** | [379 zones · TSO parsers](https://app.electricitymaps.com/map/live) | [elenco](reference-projects/data-sources/21-electricitymaps.md) | 379 zone parsers, carbon intensity, ENTSOE parser |
| **Herbie** | [NOAA NOMADS/NODD GRIB](https://nomads.ncep.noaa.gov/) | [elenco](reference-projects/data-sources/22-herbie.md) | NWP GRIB HRRR/GFS/ECMWF — adapter herbie_harvest (off) |

## Maritime / aviazione

| Progetto | Portale dati | Catalogo | Note |
|----------|--------------|----------|------|
| **Global Fishing Watch** | [GFW 4Wings AIS API](https://globalfishingwatch.org/our-apis/) | [elenco](reference-projects/data-sources/23-global-fishing-watch.md) | AIS fishing effort, encounters, SAR — complements PortWatch |
| **tar1090** | [ADS-B readsb · adsb.lol aggregate](https://adsb.lol/) | [elenco](reference-projects/data-sources/24-tar1090.md) | ADS-B web UI — complements OpenSky live stream |

## Compliance / OSINT / cyber

| Progetto | Portale dati | Catalogo | Note |
|----------|--------------|----------|------|
| **OpenSanctions** | [OFAC/EU/UN sanctions · yente API](https://www.opensanctions.org/docs/api/) | [elenco](reference-projects/data-sources/25-opensanctions.md) | OFAC/EU/UN sanctions + PEP — yente API |
| **SpiderFoot** | [200+ OSINT modules](https://www.spiderfoot.net/documentation/) | [elenco](reference-projects/data-sources/26-spiderfoot.md) | 200+ OSINT modules — entity recon automation |
| **IntelOwl** | [500+ threat intel analyzers](https://intelowlproject.github.io/docs/) | [elenco](reference-projects/data-sources/27-intelowl.md) | 500+ analyzers — IOC enrichment parallel API |

## Trading / execution / portfolio

| Progetto | Portale dati | Catalogo | Note |
|----------|--------------|----------|------|
| **Rotki** | [Exchange + on-chain sync](https://docs.rotki.com/) | [elenco](reference-projects/data-sources/28-rotki.md) | Self-hosted on-chain + exchange portfolio accounting |
| **pysystemtrade** | [IB live + Quandl/CSV futures](https://www.interactivebrokers.com/en/trading/ib-api.php) | [elenco](reference-projects/data-sources/29-pysystemtrade.md) | Carver systematic futures — export module ON |
| **Hummingbot** | [47 CEX/DEX connectors](https://hummingbot.org/exchanges/) | [elenco](reference-projects/data-sources/30-hummingbot.md) | 47 exchange connectors — market making pattern |

---

## Riepilogo per STRAN

STRAN (`progetto stran/world_clocks.exe`) — demo Win32 GDI, desk ops. Sulla pagina **ING → REF** ogni voce punta al **portale dati** e al catalogo feed/API.

*Aggiornato da `scripts/desk_harvest/gen_reference_summary.py`*
