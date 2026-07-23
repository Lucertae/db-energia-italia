#!/usr/bin/env python3
"""Primary data portals for 30 reference projects — no GitHub repo links."""
from __future__ import annotations

# data_portal: main API / dataset / docs URL for ingestion (not source code)
REFERENCE_PORTALS: dict[str, dict[str, str]] = {
    "world_monitor": {
        "data_portal": "https://www.worldmonitor.app/docs/data-sources",
        "data_portal_label": "WM data catalog",
    },
    "globeops": {
        "data_portal": "https://globeops.cloud/",
        "data_portal_label": "GlobeOps live desk",
    },
    "energy_monitor": {
        "data_portal": "https://energy.worldmonitor.app/",
        "data_portal_label": "Energy Monitor",
    },
    "oriza": {
        "data_portal": "https://www.eia.gov/opendata/",
        "data_portal_label": "EIA Open Data + commodity RSS",
    },
    "fincept_terminal": {
        "data_portal": "https://fincept.co/",
        "data_portal_label": "Fincept connectors & data API",
    },
    "typhoon_terminal": {
        "data_portal": "https://docs.alpaca.markets/",
        "data_portal_label": "Alpaca + Kraken market APIs",
    },
    "openbook": {
        "data_portal": "https://developers.binance.com/docs/derivatives/usds-margined-futures/websocket-market-streams",
        "data_portal_label": "Binance Futures WebSocket depth",
    },
    "rs_trader": {
        "data_portal": "https://finance.yahoo.com/",
        "data_portal_label": "Yahoo Finance + CSV/Parquet replay",
    },
    "blackdesk": {
        "data_portal": "https://finance.yahoo.com/",
        "data_portal_label": "Yahoo Finance poll",
    },
    "mkt": {
        "data_portal": "https://docs.cloud.coinbase.com/advanced-trade-api/docs/welcome",
        "data_portal_label": "Coinbase WS + Yahoo + FRED + DeFiLlama",
    },
    "wickra_terminal": {
        "data_portal": "https://api.binance.com/",
        "data_portal_label": "Exchange REST/WS (514 indicators)",
    },
    "stockstui": {
        "data_portal": "https://fred.stlouisfed.org/docs/api/fred/",
        "data_portal_label": "yfinance + FRED API",
    },
    "pftui": {
        "data_portal": "https://pftui.com/",
        "data_portal_label": "19 providers (Yahoo, CoinGecko, CFTC…)",
    },
    "openterminalui": {
        "data_portal": "https://finance.yahoo.com/",
        "data_portal_label": "Multi-provider market data shell",
    },
    "triphopp_bloomberg": {
        "data_portal": "https://fred.stlouisfed.org/",
        "data_portal_label": "FastAPI routers · macro/FRED/yfinance",
    },
    "feremabraz_bloomberg": {
        "data_portal": "https://finance.yahoo.com/",
        "data_portal_label": "Simulated demo · Yahoo-style quotes",
    },
    "openbb": {
        "data_portal": "https://docs.openbb.co/",
        "data_portal_label": "OpenBB Platform providers",
    },
    "egui_charts": {
        "data_portal": "https://userfrm.github.io/egui-charts/",
        "data_portal_label": "Host app defines feeds",
    },
    "obsyd": {
        "data_portal": "https://obsyd.dev/api/docs",
        "data_portal_label": "ENTSO-E · Fraunhofer · GIE gas API",
    },
    "gridstatus": {
        "data_portal": "https://www.gridstatus.io/",
        "data_portal_label": "US/Canada ISO + EIA",
    },
    "electricitymaps": {
        "data_portal": "https://app.electricitymaps.com/map/live",
        "data_portal_label": "379 zones · TSO parsers",
    },
    "herbie": {
        "data_portal": "https://nomads.ncep.noaa.gov/",
        "data_portal_label": "NOAA NOMADS/NODD GRIB",
    },
    "global_fishing_watch": {
        "data_portal": "https://globalfishingwatch.org/our-apis/",
        "data_portal_label": "GFW 4Wings AIS API",
    },
    "tar1090": {
        "data_portal": "https://adsb.lol/",
        "data_portal_label": "ADS-B readsb · adsb.lol aggregate",
    },
    "opensanctions": {
        "data_portal": "https://www.opensanctions.org/docs/api/",
        "data_portal_label": "OFAC/EU/UN sanctions · yente API",
    },
    "spiderfoot": {
        "data_portal": "https://www.spiderfoot.net/documentation/",
        "data_portal_label": "200+ OSINT modules",
    },
    "intelowl": {
        "data_portal": "https://intelowlproject.github.io/docs/",
        "data_portal_label": "500+ threat intel analyzers",
    },
    "rotki": {
        "data_portal": "https://docs.rotki.com/",
        "data_portal_label": "Exchange + on-chain sync",
    },
    "pysystemtrade": {
        "data_portal": "https://www.interactivebrokers.com/en/trading/ib-api.php",
        "data_portal_label": "IB live + Quandl/CSV futures",
    },
    "hummingbot": {
        "data_portal": "https://hummingbot.org/exchanges/",
        "data_portal_label": "47 CEX/DEX connectors",
    },
}
