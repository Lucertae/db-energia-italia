# Reference projects — UI e dati open source

*Catalogo: **30 progetti** con scheda UI + fonti dati estratte dal codice sorgente.*

Ogni scheda include screenshot UI e fonti dati **free / open** usate in ingestion.  
I link puntano ai **portali/API dati** — non ai repo GitHub (vedi [`../reference-projects.md`](../reference-projects.md)).

## Indice

| # | Progetto | Categoria | Scheda |
|---|----------|-----------|--------|
| 1 | World Monitor | Ops / geo | [projects/01-world-monitor.md](projects/01-world-monitor.md) |
| 2 | GlobeOps | Ops / geo | [projects/02-globeops.md](projects/02-globeops.md) |
| 3 | Energy Monitor | Ops / energia | [projects/03-energy-monitor.md](projects/03-energy-monitor.md) |
| 4 | Oriza | Commodity desk | [projects/04-oriza.md](projects/04-oriza.md) |
| 5 | Fincept Terminal | Desktop Bloomberg | [projects/05-fincept-terminal.md](projects/05-fincept-terminal.md) |
| 6 | TyphooN Terminal | Desktop trading | [projects/06-typhoon-terminal.md](projects/06-typhoon-terminal.md) |
| 7 | OpenBook | Order flow | [projects/07-openbook.md](projects/07-openbook.md) |
| 8 | rs_trader | Workflow trading | [projects/08-rs-trader.md](projects/08-rs-trader.md) |
| 9 | Blackdesk | TUI research | [projects/09-blackdesk.md](projects/09-blackdesk.md) |
| 10 | mkt | TUI markets | [projects/10-mkt.md](projects/10-mkt.md) |
| 11 | wickra-terminal | TUI + Web trading | [projects/11-wickra-terminal.md](projects/11-wickra-terminal.md) |
| 12 | stocksTUI | TUI Python | [projects/12-stockstui.md](projects/12-stockstui.md) |
| 13 | pftui | TUI + Web portfolio | [projects/13-pftui.md](projects/13-pftui.md) |
| 14 | OpenTerminalUI | Web full-stack | [projects/14-openterminalui.md](projects/14-openterminalui.md) |
| 15 | triphopp Bloomberg | Web self-hosted | [projects/15-triphopp-bloomberg.md](projects/15-triphopp-bloomberg.md) |
| 16 | feremabraz Bloomberg | Web clone UI | [projects/16-feremabraz-bloomberg.md](projects/16-feremabraz-bloomberg.md) |
| 17 | OpenBB | Piattaforma dati | [projects/17-openbb.md](projects/17-openbb.md) |
| 18 | egui-charts | Libreria chart | [projects/18-egui-charts.md](projects/18-egui-charts.md) |
| 19 | OBSYD | Energia EU desk | [projects/19-obsyd.md](projects/19-obsyd.md) |
| 20 | gridstatus | Energia US ISO | [projects/20-gridstatus.md](projects/20-gridstatus.md) |
| 21 | Electricity Maps | Carbon / power globale | [projects/21-electricitymaps.md](projects/21-electricitymaps.md) |
| 22 | Herbie | Meteo NWP | [projects/22-herbie.md](projects/22-herbie.md) |
| 23 | Global Fishing Watch | Maritime AIS | [projects/23-global-fishing-watch.md](projects/23-global-fishing-watch.md) |
| 24 | tar1090 | Aviazione ADS-B | [projects/24-tar1090.md](projects/24-tar1090.md) |
| 25 | OpenSanctions | Sanzioni / PEP | [projects/25-opensanctions.md](projects/25-opensanctions.md) |
| 26 | SpiderFoot | OSINT automation | [projects/26-spiderfoot.md](projects/26-spiderfoot.md) |
| 27 | IntelOwl | Threat intel | [projects/27-intelowl.md](projects/27-intelowl.md) |
| 28 | Rotki | Portfolio on-chain | [projects/28-rotki.md](projects/28-rotki.md) |
| 29 | pysystemtrade | FX futures systematic | [projects/29-pysystemtrade.md](projects/29-pysystemtrade.md) |
| 30 | Hummingbot | Crypto execution | [projects/30-hummingbot.md](projects/30-hummingbot.md) |

## Copertura dati (gap colmati 19–30)

| Dominio | Prima (1–18) | Aggiunto (19–30) |
|---------|--------------|------------------|
| Energia EU (ENTSO-E) | Parziale (WM, Energy Monitor) | **OBSYD**, Electricity Maps parser ENTSOE |
| Energia US (ISO) | Assente | **gridstatus** |
| Carbon / mix globale | Parziale | **Electricity Maps** (379 zone) |
| Meteo NWP → energia | Assente | **Herbie** |
| Maritime dedicato | AIS generico WM | **Global Fishing Watch** |
| ADS-B aviazione UI | Layer WM | **tar1090** |
| Sanzioni / compliance | Assente | **OpenSanctions** |
| OSINT / cyber | Feodo in WM | **SpiderFoot**, **IntelOwl** |
| On-chain / DeFi portfolio | Crypto quotes | **Rotki** |
| FX futures systematic | Assente | **pysystemtrade** |
| Crypto market making | Order book only | **Hummingbot** |

## Fonti dati (elenco completo)

→ **[data-sources/README.md](data-sources/README.md)** — ogni progetto, ogni feed/fonte elencato uno per uno dal codice sorgente.

→ **[ops-matrix.md](ops-matrix.md)** — live/batch, mappa sì/no, frequenza aggiornamento (30 progetti).

## Struttura cartella

```
reference-projects/
├── README.md          ← questo file
├── images/            ← screenshot locali
└── projects/          ← scheda per progetto
```

*Aggiornato: luglio 2026*
