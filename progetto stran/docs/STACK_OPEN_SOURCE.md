# Stack open source — mappa operativa OPS DESK

**Registro machine-readable:** `config/data_sources.json`  
**Moduli attivi:** `config/modules.json`  
**Catalogo 30 progetti:** `config/reference_projects.json` · [`docs/REFERENCE_PROJECTS.md`](REFERENCE_PROJECTS.md)

---

## Verdetto strategico

| Settore | Dato pregiato | Cosa dà l'open source | Edge raggiungibile? |
|---------|---------------|------------------------|---------------------|
| **FX** | Tick interdealer (proprietario) | Framework ingest + research | Solo su orizzonti lunghi / futures; daily ref ≠ arb |
| **Energia** | Pubblico per regolamento (REMIT, TP) | Quasi dataset completo | **Sì** — QA + forecast = dove si vince |

In energia un desk piccolo con **entsoe-py + meteo + epftoolbox** ha in mano quasi lo stesso dataset di una utility. In FX no — l'open source chiude il *pipeline*, non il *moat* informativo.

**Attenzione energia:** ENTSO-E Transparency Platform è patchy (buchi, serie mancanti). La pre-analisi (gap fill, validazione cross-source) è il vero edge — modulo `qa_series` in bridge.

---

## FX — ingestion

| Tool | Autore / maintainer | Ruolo desk | Adapter stran |
|------|---------------------|------------|---------------|
| [findatapy](https://github.com/cuemacro/findatapy) | Cuemacro (Saeed Amen) | Download unificato FRED/ALFRED, Dukascopy tick, Quandl, Yahoo; Arctic/Parquet | `findatapy_harvest` (off) |
| [finmarketpy](https://github.com/cuemacro/finmarketpy) | Cuemacro | Event studies NFP/CPI | doc only |
| [databento](https://github.com/databento/databento-python) | Databento | CME FX futures OHLCV — feed Nautilus | `databento_harvest` (off) |
| dukascopy-python | community | Spot tick storico gratuito | `dukascopy_harvest` (off) |
| [cryptofeed](https://github.com/bmoscon/cryptofeed) | bmoscon | Crypto-FX live | estensione `crypto.c` futura |

**Oggi in desk:** FRED daily + ECB ref (`data.c`) → proxy pysystemtrade export.

**Upgrade path FX:**
1. Dukascopy tick → research intraday
2. Databento 6E/6J → carry/momentum serio + Nautilus
3. findatapy → unifica tutto quando hai chiavi Bloomberg/Eikon

---

## FX — storage / pre-analisi

| Tool | Ruolo |
|------|--------|
| [ArcticDB](https://github.com/man-group/ArcticDB) | TS/tick store production (Man Group) |
| [QuestDB](https://github.com/questdb/questdb) | Streaming ingest + SQL (Databento→QuestDB→Grafana) |
| pandas-market-calendars | Sessioni FX, rollover 17:00 NY, festività |

Target desk: `cache/arctic/` o export Parquet in `cache/exports/`.

---

## Energia — ingestion

| Tool | Ruolo desk | Adapter stran |
|------|------------|---------------|
| [entsoe-py](https://github.com/EnergieID/entsoe-py) | Standard EU: DA, load, gen, flows, NTC | `entsoe_py_harvest` **on** |
| [gridstatus](https://github.com/gridstatus/gridstatus) | US ISO: CAISO, ERCOT, PJM… | `gridstatus_harvest` (off) |
| Open Power System Data | Capacity, plants EU | harvest script futuro |
| GIE / ENTSOG py | Gas storage ALSI/AGSI | `research/run_gas.py` |

**Oggi in desk:** C `ingest_entsoe.c` + `harvest_entsoe.py` → bridge preferisce entsoe-py se installato.

---

## Energia — modelling / forecast

| Tool | Ruolo |
|------|--------|
| [PyPSA](https://github.com/PyPSA/PyPSA) + PyPSA-Eur | Simulazione sistema EU |
| [atlite](https://github.com/PyPSA/atlite) | ERA5 → profili wind/solar |
| [epftoolbox](https://github.com/javieralbacete/epftoolbox) | Benchmark forecast DA (LEAR, DNN) |

Modulo `epftoolbox_status` pronto quando abiliti pip install.

---

## Execution (cross-sector)

| Tool | Settore | Consuma export desk |
|------|---------|---------------------|
| [pysystemtrade](https://github.com/pst-group/pysystemtrade) | FX futures | `cache/exports/pysystemtrade/` |
| [NautilusTrader](https://github.com/nautechsystems/nautilus_trader) | FX/crypto | `cache/exports/databento/` (target) |

---

## Layer stack vs progetto stran

```
                    ┌─────────────────────────────────┐
                    │  config/data_sources.json        │
                    │  config/modules.json             │
                    └───────────────┬─────────────────┘
                                    │
     FX: findatapy / databento / dukascopy (optional)
     EN: entsoe-py / gridstatus (optional)
     QA: qa_series (always)
                                    │
                                    ▼
                         bridge/module_runner.py
                                    │
              cache/spine/modules/*.json  +  cache/exports/
                                    │
                                    ▼
                         world_clocks.exe (C UI)
```

---

## Install rapido

```powershell
# Solo QA + grafo (zero pip):
python scripts\spine_build.py

# Stack energia (consigliato — massimo ROI):
.\scripts\install_bridge_extras.ps1 -Sector energy

# Stack FX (quando hai chiavi):
.\scripts\install_bridge_extras.ps1 -Sector fx
```

Token ENTSO-E: `ENTSOE_API_TOKEN` o `cache/entsoe.key`.

---

## Meteo → economia (NWP → energia / FX)

**Documentazione completa:** `docs/STACK_WEATHER.md`

Due rami dal raw NWP al segnale di trading, con allocazione ~80% energia / ~20% FX overlay.

| Layer | Energia | FX |
|-------|---------|-----|
| Ingestion | Herbie, ERA5, open-meteo, AI models | stesso + NOAA ONI |
| Transform | atlite, pvlib, HDD/CDD | HDD→TTF, ENSO→commodity |
| Forecast | epftoolbox, Nixtla quantili | overlay pysystemtrade |
| Segnali | PWR-01/02/03 | FX-ENSO, GAS-X |

**Moduli ON oggi:** `weather_open_meteo`, `weather_hdd_cdd`, `weather_enso`, `weather_signals`  
**Moduli OFF (prossimo):** `herbie_harvest`, `era5_harvest`, `atlite_profiles`, `epftoolbox_status`

In energia un desk piccolo con **entsoe-py + meteo + epftoolbox** ha in mano quasi lo stesso dataset di una utility — il meteo *è* il moat operativo a breve. In FX il meteo è overlay su carry/momentum, non alpha standalone.

---

## Priorità implementazione

0. **Fatto:** catalogo **30 reference projects** in `config/reference_projects.json` + sezione REF in ingest manifest
1. **Fatto:** QA serie, entsoe-py adapter, registry OSS, export pysystemtrade, **pipeline meteo→economia** (open-meteo, HDD/CDD, ENSO, weather_signals)
2. **Prossimo:** Herbie GEFS + ERA5/atlite CF; hourly ENTSO-E export per epftoolbox; gridstatus CAISO vs HUB gas spread
3. **FX live:** Databento 6E quando hai API key; sostituisce proxy FRED in export
4. **Storage:** ArcticDB backend per tick Dukascopy quando volume cresce
