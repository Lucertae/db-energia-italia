# DATI DA SCARICARE — checklist completa OPS DESK

**Progetto:** `C:\Users\jecho\Desktop\terminal`  
**Aggiornato:** 2026-07-07  
**Obiettivo storico:** 5y daily (spot/macro), 10y+ (tassi/FX), weekly (inventari), monthly (produzione), annual (bilanci energetici).

Legenda stato:

| Simbolo | Significato |
|---------|-------------|
| ✅ | Già in `cache/` o scaricato automaticamente all’avvio |
| 📦 | Già sul PC — copia/link, non riscaricare da internet |
| 🔑 | Richiede API key / registrazione gratuita |
| ⬇️ | Da scaricare |
| 💰 | A pagamento / istituzionale |
| 🔄 | Refresh periodico (live o schedulato) |

Stima spazio finale cache desk: **80–120 MB** (solo serie desk) · **+2–5 GB** se importi bulk EU/IT da `math/data` e Terna.

---

## Indice

1. [Credenziali e file chiave](#1-credenziali-e-file-chiave)
2. [Già sul PC (riuso immediato)](#2-già-sul-pc-riuso-immediato)
3. [FRED — serie già attive](#3-fred--serie-già-attive)
4. [FRED — serie da aggiungere](#4-fred--serie-da-aggiungere)
5. [ECB — FX live](#5-ecb--fx-live)
6. [EIA — inventari e bilanci paese](#6-eia--inventari-e-bilanci-paese)
7. [Produzione/consumo — FRED petroleum + US gen](#7-produzioneconsumo--fred-petroleum--us-gen)
8. [ENTSO-E Transparency Platform](#8-entso-e-transparency-platform)
9. [Prezzi power EU (day-ahead / intraday)](#9-prezzi-power-eu-day-ahead--intraday)
10. [Italia — Terna Download Center (61 dataset)](#10-italia--terna-download-center-61-dataset)
11. [Italia — GME mercato elettrico e gas](#11-italia--gme-mercato-elettrico-e-gas)
12. [Gas EU — GIE, Snam, flussi LNG](#12-gas-eu--gie-snam-flussi-lng)
13. [Carbone, carbon, raffinazione, futures](#13-carbone-carbon-raffinazione-futures)
14. [Power US / Asia / Oceania (TSO free API)](#14-power-us--asia--oceania-tso-free-api)
15. [Aziende — Stooq OHLCV + fondamentali](#15-aziende--stooq-ohlcv--fondamentali)
16. [Macro, risk, credit](#16-macro-risk-credit)
17. [Meteo, RES, HDD/CDD](#17-meteo-res-hddcdd)
18. [Eventi, outage, REMIT, calendario](#18-eventi-outage-remit-calendario)
19. [Bilanci energetici annuali (Eurostat / IEA / Ember)](#19-bilanci-energetici-annuali-eurostat--iea--ember)
20. [Infrastruttura, impianti, GIS](#20-infrastruttura-impianti-gis)
21. [Segnali alt / shark tier (opzionale)](#21-segnali-alt--shark-tier-opzionale)
22. [Geopolitica, sanzioni, AIS](#22-geopolitica-sanzioni-ais)
23. [Dati istituzionali / a pagamento](#23-dati-istituzionali--a-pagamento)
24. [Layout cache consigliato](#24-layout-cache-consigliato)
25. [Ordine di download consigliato](#25-ordine-di-download-consigliato)
26. [Comandi e script sul PC](#26-comandi-e-script-sul-pc)

URL base FRED CSV: `https://fred.stlouisfed.org/graph/fredgraph.csv?id={SERIE}&cosd={YYYY-MM-DD}`

---

## 1. Credenziali e file chiave

| File / env | Fonte | Stato | Azione |
|------------|-------|-------|--------|
| `cache/eia.key` | https://www.eia.gov/opendata/register.php | ⬇️ 🔑 | Registrati → prima riga = API key |
| `cache/entsoe.key` o env `ENTSOE_API_TOKEN` | https://transparency.entsoe.eu | 📦 🔑 | Copia da `math\data\euenergy_token.txt` o `lac\hedge\.env` (`HEDGE_ENTSOE_TOKEN`) |
| `cache/terna.key` o env `TERNA_API_KEY` | https://api.terna.it | 📦 🔑 | Copia da `lac\hedge\.env` se presente |
| `cache/gie.key` o env `HEDGE_GIE_API_KEY` | https://agsi.gie.eu | 📦 🔑 | Copia da `lac\hedge\.env` |
| Credenziali GME APIService | https://www.mercatoelettrico.org/en-us/Home/APIService | ⬇️ 🔑 | JWT per MI / archivio zip |
| CDS Copernicus (ERA5) | https://cds.climate.copernicus.eu | ⬇️ 🔑 | Solo se serve meteo storico bulk |
| EUMETSAT / NASA Earthdata | registrazione | ⬇️ 🔑 | SARAH-3, VIIRS night lights |
| `OPENCHARGEMAP_API_KEY` | https://openchargemap.org | ⬇️ 🔑 | Opzionale EV charging |
| AISStream | https://aisstream.io | ⬇️ 🔑 | Opzionale flussi nave |

**Non committare** file `*.key` o `.env`.

---

## 2. Già sul PC (riuso immediato)

| Asset | Path | Dimensione | Uso desk |
|-------|------|------------|----------|
| Prezzi day-ahead EU unificati | `math\data\unified\prices_unified.csv` | ~162 MB | Zone AT, BE, CH, CZ, DE-LU, DK1/2, FR, HU, IT-NORTH, NL, NO2, PL, SI (fonte SMARD) |
| Snapshot per zona | `math\data\unified\latest_by_zone.csv` | piccolo | Last price EU |
| Registry fonti energia | `math\data\energy_data_sources_registry.json` | — | Mappa gap/script |
| Token ENTSO-E | `math\data\euenergy_token.txt` | — | → `cache/entsoe.key` |
| Pipeline hedge IT/EU | `lac\hedge\` | variabile | ENTSO-E, Terna, GME, gas, TTF, GIE ingest Python |
| Catalogo fonti globali | `lac\hedge\docs\global-speculative-data-sources.md` | — | Riferimento esteso |
| Spine ingest ENTSO-E | `lac\hedge\config\ingest\spine_entsoe.yaml` | — | Document types + lag |
| Status ingest live | `lac\hedge\data\status.json` | — | Health panel |
| Catalogo Terna DC | `trn\_datasets.json` | 61 voci | Lista §10 |
| Downloader Terna | `trn\download_terna.py` | — | CSV 2021–2026 |
| OSINT regolatori | `sf\archivio-osint\` | — | ACER, FERC, OTE |
| Research ENTSO-E URL | `eu\archive\` | — | Link storici per paese |

---

## 3. FRED — serie già attive

Scaricate automaticamente all’avvio (`sources.c` → `cache\{ID}.csv`, ~5y daily).

| ID desk | FRED ID | Descrizione | Stato |
|---------|---------|-------------|-------|
| BRT | DCOILBRENTEU | Brent EU spot | ✅ |
| WTI | DCOILWTICO | WTI Cushing | ✅ |
| HUB | DHHNGSP | Henry Hub gas | ✅ |
| TTF | PNGASEUUSDM | Gas EU (proxy TTF) | ✅ |
| COA | PCOALAUUSDM | Coal Australia | ✅ |
| JKM | PNGASJPUSDM | LNG Asia | ✅ |
| CRU | WCESTUS1 | Inventario crude US (es-SPR) | ✅ |
| NGS | NGSTUS | Storage gas US weekly | ✅ |
| EUF | DEXUSEU | USD/EUR | ✅ |
| GBF | DEXUSUK | USD/GBP | ✅ |
| JPF | DEXJPUS | USD/JPY | ✅ |
| CNF | DEXCHUS | USD/CNY | ✅ |
| INF | DEXINUS | USD/INR | ✅ |
| BRF | DEXBZUS | USD/BRL | ✅ |
| MXF | DEXMXUS | USD/MXN | ✅ |
| KEF | DEXKOUS | USD/KRW | ✅ |
| NZF | DEXUSNZ | USD/NZD | ✅ |
| ZAF | DEXSFUS | USD/ZAR | ✅ |
| CAD | DEXCAUS | USD/CAD | ✅ |
| U10 | DGS10 | US 10Y | ✅ |
| E10 | IRLTLT01EZM156N | EA 10Y | ✅ |
| Z10 | IRLTLT01ZAM156N | ZA 10Y | ✅ |
| SOF | SOFR | SOFR | ✅ |
| EDF | ECBDFR | ECB deposit rate | ✅ |
| CPR | PCOPPUSDM | Copper | ✅ |
| BE5 | T5YIE | Breakeven inflazione 5Y US | ✅ |
| VIX | VIXCLS | VIX | ✅ |

---

## 4. FRED — serie da aggiungere

### 4.1 FX e commodity

| ID desk | FRED ID | Storico | Stato | Note |
|---------|---------|---------|-------|------|
| DXY | DTWEXBGS | 10y | ⬇️ | Broad USD index |
| NOK | DEXNOUS | 10y | ⬇️ | USD/NOK |
| SEK | DEXSDUS | 10y | ⬇️ | USD/SEK |
| XAU | GOLDAMGBD228NLBM | 10y | ⬇️ | Gold LBMA — risk proxy |
| XAG | — | — | ⬇️ | Non su FRED standard; Stooq `xauusd` / `xagusd` o LBMA |

### 4.2 Tassi e curva US / EA

| ID desk | FRED ID | Storico | Stato |
|---------|---------|---------|-------|
| U2 | DGS2 | 10y+ | ⬇️ |
| U5 | DGS5 | 10y+ | ⬇️ |
| U30 | DGS30 | 10y+ | ⬇️ |
| BE10 | T10YIE | 10y+ | ⬇️ |
| TIPS5 | DFII5 | 10y+ | ⬇️ |
| TIPS10 | DFII10 | 10y+ | ⬇️ |
| FF | DFF | 10y+ | ⬇️ | Fed funds effective |
| EUR3M | — | — | ⬇️ | ECB SDW o FRED `IR3TIB01EZM156N` |
| EURIBOR3M | — | — | ⬇️ | EMMI / FRED proxy |

### 4.3 Energia — prodotti e inventari

| ID desk | FRED ID | Freq | Stato | Note |
|---------|---------|------|-------|------|
| SPR | WCSSTUS1 | weekly | ⬇️ | Strategic Petroleum Reserve |
| RBO | GASREGW | weekly | ⬇️ | Gasoline retail US |
| HOL | HOILBTE | daily | ⬇️ | Heating oil — crack |
| PROP | DPROPANEMBTX | weekly | ⬇️ | Propane Mont Belvieu |
| NGPROD | NGGPUS | monthly | ⬇️ | US gas production |
| NGCONS | NGCPUS | monthly | ⬇️ | US gas consumption |
| REFUTIL | — | weekly | ⬇️ | EIA `PET.WPULEUS3.W` refinery utilization |

### 4.4 Macro / equity

| ID desk | FRED ID | Storico | Stato |
|---------|---------|---------|-------|
| SPX | SP500 | 10y+ | ⬇️ |
| NAS | NASDAQCOM | 10y+ | ⬇️ |
| HY_OAS | BAMLH0A0HYM2 | 10y+ | ⬇️ | ICE BofA HY OAS |
| IG_OAS | BAMLC0A0CM | 10y+ | ⬇️ |
| UNRATE | UNRATE | monthly | ⬇️ |
| CPI | CPIAUCSL | monthly | ⬇️ |
| ISM | — | monthly | ⬇️ | ISM PMI — scrape o FRED `NAPM` legacy |

---

## 5. ECB — FX live

| Dato | URL | Stato | Note |
|------|-----|-------|------|
| `eurofxref-daily.xml` | https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml | ✅ 🔄 | ~30 valute vs EUR, refresh ogni fetch |
| Storico ECB | https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml | ⬇️ | Cross EUR storici 5y+ in cache |
| SDW tassi EA | https://data.ecb.europa.eu | ⬇️ | Euribor, deposit, MRO se serve CIP |

---

## 6. EIA — inventari e bilanci paese

**Prerequisito:** `cache/eia.key`

### 6.1 Serie US weekly/daily (API v2)

| Serie | Route EIA v2 | Freq | Stato |
|-------|--------------|------|-------|
| Crude stocks ex-SPR | `petroleum/stoc/wstk/data` | weekly | ⬇️ | complemento FRED |
| SPR | `petroleum/stoc/wstk` filter SPR | weekly | ⬇️ |
| Gas storage | `natural-gas/stor/wkly/data` | weekly | ⬇️ |
| Gas production | `natural-gas/prod/sum/data` | monthly | ⬇️ |
| Refinery utilization | `petroleum/pnp/wiup/data` | weekly | ⬇️ |
| Henry Hub spot | `natural-gas/pri/fut/data` | daily | ⬇️ |
| US generation by fuel | `electricity/electric-power-operational-data` | monthly | ⬇️ | complemento FRED SUNEPUS… |
| US consumption petroleum | `international/data` | annual | ⬇️ |

### 6.2 Primary energy consumption per paese (scheda PRODUCTION)

API: `https://api.eia.gov/v2/international/data/?api_key=…&frequency=annual&data[0]=value&facets[countryRegionId][]={ISO3}&facets[activityId][]=2` (primary energy)

| ISO2 | Paese | Stato |
|------|-------|-------|
| US | United States | ⬇️ 🔑 |
| CHN | China | ⬇️ 🔑 |
| DEU | Germany | ⬇️ 🔑 |
| JPN | Japan | ⬇️ 🔑 |
| IND | India | ⬇️ 🔑 |
| BRA | Brazil | ⬇️ 🔑 |
| GBR | United Kingdom | ⬇️ 🔑 |
| FRA | France | ⬇️ 🔑 |
| ITA | Italy | ⬇️ 🔑 |
| RUS | Russia | ⬇️ 🔑 |
| AUS | Australia | ⬇️ 🔑 |
| MEX | Mexico | ⬇️ 🔑 |
| KOR | South Korea | ⬇️ 🔑 |
| ZAF | South Africa | ⬇️ 🔑 |
| CAN | Canada | ⬇️ 🔑 |
| ESP | Spain | ⬇️ 🔑 |
| NLD | Netherlands | ⬇️ 🔑 |
| NOR | Norway | ⬇️ 🔑 |
| POL | Poland | ⬇️ 🔑 |
| SAU | Saudi Arabia | ⬇️ 🔑 |
| ARE | UAE | ⬇️ 🔑 |
| TUR | Turkey | ⬇️ 🔑 |

---

## 7. Produzione/consumo — FRED petroleum + US gen

Usati da `production.c` — **non** ancora in `cache/` come serie storiche complete.

### 7.1 Consumo petroleum (monthly, Mtoe proxy)

| Paese | FRED ID | Stato |
|-------|---------|-------|
| US | PCEPETUSDM | ⬇️ |
| CN | PCEPETCHNM | ⬇️ |
| DE | PCEPETDEUM | ⬇️ |
| JP | PCEPETJPNM | ⬇️ |
| IN | PCEPETINM | ⬇️ |
| BR | PCEPETBZZM | ⬇️ |
| GB | PCEPETGBRM | ⬇️ |
| FR | PCEPETFRAM | ⬇️ |
| IT | PCEPETITAM | ⬇️ |
| RU | PCEPETRUSM | ⬇️ |
| AU | PCEPETAUSM | ⬇️ |
| MX | PCEPETMEXM | ⬇️ |
| KR | PCEPETKORM | ⬇️ |
| ZA | PCEPETZAFCM | ⬇️ |
| CA | PCEPETCANM | ⬇️ |
| ES | PCEPETESPM | ⬇️ |
| NL | PCEPETNLDM | ⬇️ |
| NO | PCEPETNORM | ⬇️ |
| PL | PCEPETPOLM | ⬇️ |
| TR | PCEPETTURM | ⬇️ |

### 7.2 Generazione elettrica US per fonte (monthly TWh)

| Fonte | FRED ID | Stato |
|-------|---------|-------|
| Solar | SUNEPUS | ⬇️ |
| Wind | WNDEPUS | ⬇️ |
| Hydro | HYDEPUS | ⬇️ |
| Nuclear | NUCEPUS | ⬇️ |
| Gas | NGNEPUS | ⬇️ |
| Coal | CLEPUS | ⬇️ |
| Oil | PETEPUS | ⬇️ |

### 7.3 Generazione EU per fonte (ENTSO-E — vedi §8)

Per **DE, FR, GB, IT, ES, NL, PL, NO, AT, BE, CZ, DK, HU, SI** — mix orario→daily aggregato.

---

## 8. ENTSO-E Transparency Platform

**Endpoint:** `https://web-api.tp.entsoe.eu/api`  
**Auth:** token §1 · **Rate limit:** ~400 req/min

### 8.1 Document types (tutti da backfill 2015→oggi dove applicabile)

| Code | Contenuto | Granularità | Zone minime desk | Stato |
|------|-----------|-------------|------------------|-------|
| A44 | Day-ahead prices | PT60M | DE, FR, IT-NORD, ES, NL, BE, AT, PL, NO2, DK1, SE3, GB | ⬇️ 📦 |
| A65 | Actual total load | PT15M | stesse + IT | ⬇️ 📦 |
| A75 | Actual generation per type | PT15M | stesse | ⬇️ 📦 |
| A11 | Cross-border physical flow | PT15M | coppie IT-FR, IT-CH, DE-FR, DE-NL… | ⬇️ 📦 |
| A61 | Offered capacity (NTC) | PT60M | border IT | ⬇️ |
| A69 | Generation forecast (wind/solar) | PT15M | IT, DE, ES | ⬇️ |
| A71 | Load forecast | PT15M | IT, DE | ⬇️ |
| A77 | Unavailability of generation units | event | IT, DE, FR | ⬇️ |
| A80 | Planned unavailability cross-border | event | IT | ⬇️ |
| A81 | Planned unavailability production | event | IT | ⬇️ |
| A83 | Actual generation output per unit | PT15M | campione IT | ⬇️ |
| A85 | Installed generation capacity | annual | per BZ | ⬇️ |

**EIC bidding zone** (riferimento): IT-NORD `10YIT-GRTN---B`, DE-LU `10Y1001A1001A83F`, FR `10YFR-RTE------C`, ES `10YES-REE------0`, GB `10YGB----------A`, NL `10YNL----------L`, BE `10YBE----------2`, AT `10YAT-APG------L`, PL `10YPL-AREA-----S`, NO2 `10YNO-2--------T`, DK1 `10YDK-1--------W`, SE3 `10YSE-3--------L`.

**Script PC:** `math\data\fetch_entsoe_history.py`, `fetch_entsoe_load_history.py`, `fetch_entsoe_it_fundamentals.py` · `lac\hedge` → `hedge backfill-entsoe-realized`

---

## 9. Prezzi power EU (day-ahead / intraday)

| Fonte | URL | Zone / scope | Storico | Stato |
|-------|-----|--------------|---------|-------|
| SMARD (Bundesnetz) | https://www.smard.de | DE + cross DE | 2014+ | 📦 in `prices_unified.csv` |
| Energy-Charts | https://api.energy-charts.info | 40+ zone EU | 2y+ live | ⬇️ 🔄 |
| Open Power System Data | https://data.open-power-system-data.org/time_series | EU hourly | fino ~2020 | ⬇️ |
| Nord Pool Data Portal | https://www.nordpoolgroup.com | Nordic | 💰 delayed free | ⬇️ |
| EPEX SPOT public | https://webshop.eex-group.com/epex-spot-public-market-data | EU DA | 💰 EOD | ⬇️ |
| GME pubblicazioni | https://www.mercatoelettrico.org | IT MGP/MI | zip | ⬇️ |
| Ember Climate | https://ember-climate.org/data/data-explorer/ | EU prices gen | CC-BY | ⬇️ |
| OWID energy-data | https://github.com/owid/energy-data | global annual | static | ⬇️ |

**Zone da estendere oltre SMARD attuale:** SE1–4, FI, EE, LV, LT, IE, RO, BG, GR, PT, SK, HR, RS, UA (via ENTSO-E A44).

---

## 10. Italia — Terna Download Center (61 dataset)

**Catalogo:** `trn\_datasets.json` · **Script:** `trn\download_terna.py` → destinazione consigliata `cache/terna/`

| Cluster | Dataset ID | Label | Stato |
|---------|------------|-------|-------|
| Load | TotalLoad | fabbisogno-italia | ⬇️ |
| Load | MarketLoad | fabbisogno-mercato | ⬇️ |
| Load | PeakValleyLoad | picchi-massimi-minimi | ⬇️ |
| Load | DailyDataIndexes | confronto-dati-giornalieri | ⬇️ |
| Load | InternationalComparisons | confronti-internazionali | ⬇️ |
| Statistics | IMCEI | imcei | ⬇️ |
| Statistics | IMSER | imser | ⬇️ |
| Consumption | ElectricalEnergy | energia-elettrica-settore | ⬇️ |
| Consumption | Market | mercato | ⬇️ |
| Consumption | IndustrialSector | settore-industria | ⬇️ |
| Consumption | ServiceSector | settore-servizi | ⬇️ |
| Consumption | Total | totale | ⬇️ |
| Demand | ConsumptionBySource | copertura-domanda-fonte | ⬇️ |
| Demand | ElectricityItaly | energia-elettrica-italia | ⬇️ |
| Demand | ElectricityByType | energia-elettrica-tipologia | ⬇️ |
| Generation | ActualGeneration | generazione-attuale | ⬇️ |
| Generation | RenewableGeneration | generazione-rinnovabile | ⬇️ |
| Generation | EnergyBalance | bilancio-energetico | ⬇️ |
| Generation | RenewableSources | installato-rinnovabili | ⬇️ |
| Generation | NonRenewableSources | installato-non-rinnovabili | ⬇️ |
| Generation | Storage | accumuli | ⬇️ |
| Generation | InternationalComparisons | confronti-internazionali | ⬇️ |
| Production | ElectricityBySource | energia-elettrica-fonte | ⬇️ |
| Production | ProductionRenewableSources | fonti-rinnovabili | ⬇️ |
| Production | HydroPower | idrica | ⬇️ |
| Production | GrossVsCO2Emissions | lorda-emissioni | ⬇️ |
| Production | ProductionThermal | termoelettrica | ⬇️ |
| Production | ThermalHeat | termoelettrica-calore | ⬇️ |
| Capacity | CapacityRenewableSources | fonti-rinnovabili | ⬇️ |
| Capacity | GenerationPlants | impianti-generazione | ⬇️ |
| Capacity | CapacityThermal | termoelettrica | ⬇️ |
| Transmission | SchedForeignExchg | scambio-estero-programmato | ⬇️ |
| Transmission | SchedInternalExchg | scambio-interno-programmato | ⬇️ |
| Transmission | PhysForeignFlow | flusso-fisico-estero | ⬇️ |
| Transmission | PhysInternalFlow | flusso-fisico-interno | ⬇️ |
| MGP | ForecastTransitLimit | limiti-transito-provvisori | ⬇️ |
| MGP | MGPForecastLoad | previsione-carico | ⬇️ |
| MGP | MGPTransitLimit | limiti-transito-definitivi | ⬇️ |
| Input | FCRInput | fcr-input | ⬇️ |
| Input | MITransitLimit | mi | ⬇️ |
| InputMSD | DemandReserve | fabbisogno-riserva | ⬇️ |
| InputMSD | MSDTransitLimit | limiti-transito | ⬇️ |
| InputMSD | WindProductionForecast | previsione-eolico | ⬇️ |
| InputMSD | SubmittedOffers | offerte-presentate | ⬇️ |
| Input | TERRETransitLimit | terre | ⬇️ |
| Input | SecondaryAdjustmentLevels | mb | ⬇️ |
| Input | ProjectPicassoConnections | picasso | ⬇️ |
| OutputMSD | TransitMargins | margini-transito | ⬇️ |
| OutputMSD | Prices | prezzi | ⬇️ |
| OutputMSD | Quantity | quantità | ⬇️ |
| OutputMSD | Costs | costi | ⬇️ |
| OutputMSD | AcceptedOffers | offerte-accettate | ⬇️ |
| Output | FCROutput | fcr-output | ⬇️ |
| Adequacy | ExpectedAvailableCapacity | previsione | ⬇️ |
| Adequacy | AggregateAvailableCapacity | consuntivo | ⬇️ |
| Connections | FER | fer | ⬇️ |
| Connections | Accumuli | accumuli | ⬇️ |
| OpenSeason | Microzones | microzone | ⬇️ |
| OpenSeason | Stations | stazioni | ⬇️ |
| OpenSeason | Sections | sezioni | ⬇️ |
| OpenSeason | Works | opere | ⬇️ |

### 10.1 Terna API OAuth (lac/hedge — complemento CSV)

| Endpoint | Contenuto | Stato |
|----------|-----------|-------|
| `/market/v1.0/input/transit-limit` | Transit limits D-1 | ⬇️ 🔑 |
| Unavailability productive units | outage IT | ⬇️ 🔑 |
| Market prices MSD | marginali UP/DOWN | ⬇️ 🔑 |
| Preliminary macrozonal imbalance | PT15M | ⬇️ 🔑 |
| Total/Market load v2 | forecast vs actual | ⬇️ 🔑 |
| Wind production forecast | D-1 | ⬇️ 🔑 |
| Expected available capacity | adequacy | ⬇️ 🔑 |

---

## 11. Italia — GME mercato elettrico e gas

| Dato | Fonte | Storico | Stato |
|------|-------|---------|-------|
| MGP prezzi orari | GME pubblicazioni / APIService | 2015+ | ⬇️ 🔑 |
| MI sessioni MI1–MI7 | GME APIService `RequestData` | 2019+ | ⬇️ 🔑 |
| MI-XBID 15m | GME APIService | 2025+ | ⬇️ 🔑 |
| MSD XML | mercatoelettrico.org | 2020+ | ⬇️ |
| MGP gas / MGS | GME zip gas hub | 2018+ | ⬇️ |
| PUN / zone prezzi | Energy-Charts proxy | 2019+ | ⬇️ |
| GSE open data | https://opendata.gse.it | variabile | ⬇️ |
| GSE Atlaimpianti | web export | snapshot | ⬇️ |
| ARERA tariffe | https://www.arera.it | trimestrale | ⬇️ |
| ARERA portale offerte | opendata | ⬇️ | `math\data\fetch_arera_portale_offerte_opendata.py` |

---

## 12. Gas EU — GIE, Snam, flussi LNG

| Dato | Fonte | Freq | Stato |
|------|-------|------|-------|
| AGSI+ storage EU % | https://agsi.gie.eu/api | daily | ⬇️ 🔑 |
| ALSI LNG storage | https://alsi.gie.eu/api | daily | ⬇️ 🔑 |
| Snam physical flows | Snam Rete Gas dashboard | hourly | ⬇️ |
| ENTSOG transparency | https://transparency.entsog.eu | hourly | ⬇️ |
| GIIGNL LNG trade | https://giignl.org | monthly | ⬇️ |
| Kpler / Vortexa LNG | — | RT | 💰 |
| IMF PortWatch chokepoints | https://portwatch.imf.org | weekly | ⬇️ |

---

## 13. Carbone, carbon, raffinazione, futures

| ID | Fonte | Storico | Stato |
|----|-------|---------|-------|
| EUA | ICE / Ember daily carbon | 3y+ | ⬇️ |
| API2 | ICE coal Rotterdam / Investing scrape | 5y | ⬇️ |
| NEWC | Global Coal index | 5y | ⬇️ |
| BRENT M1–M12 | ICE Brent futures | 2y | ⬇️ 💰 |
| WTI M1–M12 | CME WTI | 2y | ⬇️ 💰 |
| HH M1–M12 | CME NG | 2y | ⬇️ 💰 |
| TTF M1–M12 | ICE Endex TTF | 2y | ⬇️ 💰 |
| Crack 3-2-1 | calc da futures | 2y | ⬇️ | derivato |
| Spark spread | power vs gas | 2y | ⬇️ | derivato ENTSO-E + TTF |
| Dark spread | coal vs power | 2y | ⬇️ | derivato |

**Free proxy:** Stooq futures symbols (`cl.f`, `br.f`, `ng.f`) — EOD, non ufficiali exchange.

---

## 14. Power US / Asia / Oceania (TSO free API)

| Mercato | URL registrazione | Dati | Stato |
|---------|-------------------|------|-------|
| PJM | https://apiportal.pjm.com | LMP, load, gen | ⬇️ 🔑 |
| ERCOT | https://apiexplorer.ercot.com | DAM/RTM SPP, fuel mix | ⬇️ 🔑 |
| CAISO OASIS | https://oasis.caiso.com | LMP DA/RT | ⬇️ |
| MISO | https://www.misoenergy.org | market reports files | ⬇️ |
| NYISO | https://www.nyiso.com | LBMP | ⬇️ |
| ISO-NE | https://www.iso-ne.com | LMP | ⬇️ |
| SPP | https://www.spp.org | LMP | ⬇️ |
| AEMO NEM | https://nemweb.com.au | 5-min dispatch | ⬇️ |
| JEPX | https://www.jepx.jp | spot 30-min | ⬇️ CSV |
| KPX Korea | https://new.kpx.or.kr | hourly | ⬇️ |
| CENACE Mexico | https://www.cenace.gob.mx | MDA/MTR | ⬇️ |

---

## 15. Aziende — Stooq OHLCV + fondamentali

### 15.1 Catalogo attuale (`companies.c`) — OHLCV daily 5y ciascuno

| Symbol Stooq | Nome | Tier |
|--------------|------|------|
| xom.us | ExxonMobil | MAJOR |
| cvx.us | Chevron | MAJOR |
| shel.uk | Shell | MAJOR |
| bp.uk | BP | MAJOR |
| tte.fr | TotalEnergies | MAJOR |
| eqnr.us | Equinor | MAJOR |
| eni.it | Eni | MAJOR |
| rep.mc | Repsol | MAJOR |
| 2222.sa | Saudi Aramco | NOC |
| pbr.us | Petrobras | NOC |
| ptr.us | PetroChina | NOC |
| snpm.us | Sinopec | NOC |
| cop.us | ConocoPhillips | SEMI |
| eog.us | EOG Resources | SEMI |
| oxy.us | Occidental | SEMI |
| slb.us | SLB | SEMI |
| hal.us | Halliburton | SEMI |
| lng.us | Cheniere LNG | SEMI |
| vlo.us | Valero | SEMI |
| mpc.us | Marathon Petro | SEMI |
| enel.it | Enel | UTIL |
| ng.uk | National Grid | UTIL |
| eon.de | E.ON | UTIL |
| rwe.de | RWE | UTIL |
| ibe.mc | Iberdrola | UTIL |
| nee.us | NextEra Energy | UTIL |
| duk.us | Duke Energy | UTIL |
| engi.pa | Engie | UTIL |
| snam.it | Snam | DIST |
| ig.it | Italgas | DIST |
| wmb.us | Williams | DIST |
| kmi.us | Kinder Morgan | DIST |
| oke.us | ONEOK | DIST |
| edp.pt | EDP | UTIL |
| orsted.co | Orsted | UTIL |

**Stato live quote:** ✅ 🔄 · **Storico OHLCV 5y:** ⬇️ → `cache/stooq/{sym}.csv`

### 15.2 Espansione target desk globale (150–250 ticker) — da scaricare

| Segmento | Esempi symbol | Qtà target |
|----------|---------------|------------|
| NOC aggiuntive | rosneft (se listed), adnoc, gazprom adr | 10 |
| E&P US/EU | fang.us, oxy.us, eqt.us, hln.l | 25 |
| Refining EU | neste.he, galp.ls | 10 |
| LNG / midstream | trp.to, paa.us, et.us | 15 |
| Utilities EU | edf.fr, fortum.he, verb.vi | 30 |
| Renewables | vestas.co, enph.us, fslr.us | 20 |
| Oilfield services | bk.us, ftci.us | 10 |
| Coal miners | bhp.uk, glen.l, arch.us | 10 |
| Power equipment | ge.us, siemens.de | 10 |
| ETFs energy | xle.us, xop.us, icln.us | 10 |

### 15.3 Fondamentali (DCF)

| Dato | Fonte | Stato |
|------|-------|-------|
| Revenue, EBITDA, FCF, debt | SEC EDGAR XBRL | ⬇️ |
| Dividend yield | issuer / FRED | ⬇️ |
| EV/EBITDA peer set | calc da prezzo + filings | ⬇️ |
| Consensus estimates | 💰 Bloomberg/Refinitiv | 💰 |

---

## 16. Macro, risk, credit

| Serie | Fonte | Stato |
|-------|-------|-------|
| VIX | FRED | ✅ |
| SP500 | FRED | ⬇️ |
| HYG / LQD | Stooq ETF | ⬇️ |
| HY OAS | FRED BAML | ⬇️ |
| IG OAS | FRED BAML | ⬇️ |
| TED spread | FRED | ⬇️ |
| EPU index | policyuncertainty.com CSV | ⬇️ |
| World steel production | worldsteel.org monthly | ⬇️ |
| IAI aluminum production | world-aluminium.org | ⬇️ |
| ISM manufacturing | ISM / FRED | ⬇️ |
| S&P Global PMI Italy | press release | ⬇️ |
| CBECI mining map | ccaf.io | ⬇️ |

---

## 17. Meteo, RES, HDD/CDD

| Dato | Fonte | Granularità | Stato |
|------|-------|-------------|-------|
| Open-Meteo forecast | open-meteo.com | 15 min | ⬇️ 🔄 |
| Open-Meteo archive | archive-api.open-meteo.com | hourly 1940+ | ⬇️ |
| ECMWF HRES open-data | via Open-Meteo | 6-hourly | ⬇️ |
| GFS / ICON | Open-Meteo multi | 6-hourly | ⬇️ |
| NOAA CPC HDD/CDD US | cpc.ncep.noaa.gov | daily | ⬇️ |
| Eurostat HDD/CDD IT | eurostat API nrg_chdd_a | monthly | ⬇️ |
| ERA5-Land | Copernicus CDS | hourly | ⬇️ 🔑 |
| PVGIS hourly IT sites | JRC API | hourly | ⬇️ |
| NASA POWER | power.larc.nasa.gov | hourly/daily | ⬇️ |
| Renewables.ninja | renewables.ninja | hourly | ⬇️ |
| SARAH-3 irradiance | EUMETSAT CM SAF | daily | ⬇️ 🔑 |
| NHC hurricane advisories | nhc.noaa.gov | 6h | ⬇️ 🔄 |
| US Drought Monitor | droughtmonitor.unl.edu | weekly | ⬇️ |

**Script PC:** `math\data\fetch_open_meteo_*.py`, `fetch_nasa_power_*.py`, `fetch_pvgis_hourly_it_sites.py`, `lac\hedge` meteo backfill.

**Nota scheda MOON:** fasi lunari calcolate in-app (`moon.c`) — **nessun download**. Opzionale: coefficienti di marea da portolano / SHOM se serve precisione locale.

---

## 18. Eventi, outage, REMIT, calendario

| Evento / feed | Fonte | Stato |
|---------------|-------|-------|
| EIA petroleum status weekly | eia.gov calendar | ⬇️ 🔄 |
| EIA gas storage Thursday | eia.gov | ⬇️ 🔄 |
| FOMC dates | federalreserve.gov | ⬇️ |
| ECB Governing Council | ecb.europa.eu | ⬇️ |
| BoE MPC | bankofengland.co.uk | ⬇️ |
| OPEC+ meetings | opec.org | ⬇️ manuale |
| ENTSO-E A77/A81 outages | API §8 | ⬇️ 🔄 |
| ACER REMIT UMM | https://www.acer.europa.eu | ⬇️ 🔄 |
| ACER CHEST trades | aegis.acer.europa.eu | ⬇️ |
| Nord Pool UMM read | nordpoolgroup.com | ⬇️ |
| GME PIP outage | mercatoelettrico.org | ⬇️ |
| JAO auction results | jao.eu | ⬇️ |

---

## 19. Bilanci energetici annuali (Eurostat / IEA / Ember)

| Dataset | Fonte | Stato |
|---------|-------|-------|
| NRG_BAL_C — bilancio energetico | Eurostat API | ⬇️ |
| NRG_CB_* — consumo per prodotto | Eurostat | ⬇️ |
| SHARES — renewable share | Eurostat | ⬇️ |
| IEA World Energy Balances | iea.org (login) | ⬇️ 🔑 |
| IEA WEO scenarios | iea.org | ⬇️ 🔑 |
| Ember yearly electricity | ember-climate.org CSV | ⬇️ |
| OWID energy-data | GitHub CSV | ⬇️ |
| IRENA capacity/generation | pxweb.irena.org | ⬇️ |
| UN energy statistics | unstats.un.org | ⬇️ |
| BP Statistical Review | 💰 / legacy | 💰 |

**Script PC:** `math\data\fetch_eurostat_it_energy.py`, `fetch_irena_pxweb_it_capacity.py`

---

## 20. Infrastruttura, impianti, GIS

| Dataset | Fonte | Dimensione | Stato |
|---------|-------|------------|-------|
| WRI Global Power Plant DB | datasets.wri.org | ~50 MB | ⬇️ |
| GEM Coal Plant Tracker | globalenergymonitor.org | XLSX | ⬇️ |
| GEM Gas Plant Tracker | globalenergymonitor.org | XLSX | ⬇️ |
| OSM power Italy PBF | geofabrik.de | ~2.2 GB | ⬇️ |
| PyPSA-Eur grid | Zenodo 14230568 | ~100 MB+ | ⬇️ |
| PyPSA-Eur large assets | Zenodo 18164492 | ~850 MB | ⬇️ |
| ENTSO-E TYNDP 2024 | 2024.entsos-tyndp-scenarios.eu | static | ⬇️ |
| GADM admin boundaries | gadm.org | GeoPackage | ⬇️ |
| Eurostat NUTS 2021 | gisco-services.ec.europa.eu | shapefile | ⬇️ |
| ISTAT comuni | istat.it | shapefile | ⬇️ |

**Script PC:** `math\data\fetch_wri_global_power_plants_it.py`, `fetch_geofabrik_italy_osm_pbf.py`, `fetch_pypsa_eur_large_zenodo_assets.py`

---

## 21. Segnali alt / shark tier (opzionale)

| Segnale | Fonte | Stato |
|---------|-------|-------|
| Grid frequency OSF sample | OSF HTTP zip | ⬇️ |
| mainsfrequency.com snapshot | HTML | ⬇️ |
| NOAA ENSO / ONI | CPC FTP | ⬇️ |
| NOAA NAO monthly | CPC | ⬇️ |
| SILSO sunspot daily | silso.be | ⬇️ |
| ENTSO-E NTC day-ahead | entsoe A61 | ⬇️ |
| Google Trends IT energy | pytrends | ⬇️ |
| VIIRS night lights | NASA Earthdata | ⬇️ 🔑 |
| GDELT events | BigQuery gdelt-bq | ⬇️ |
| V-Dem regime | v-dem.net CSV | ⬇️ |

**Script PC:** `math\data\run_shark_tiers_bundle.py`, `fetch_shark_*.py`

---

## 22. Geopolitica, sanzioni, AIS

| Dato | Fonte | Stato |
|------|-------|-------|
| EU Sanctions Map | sanctionsmap.eu | ⬇️ 🔄 |
| OFAC SDN list | treasury.gov | ⬇️ 🔄 |
| OpenSanctions bulk | opensanctions.org | ⬇️ |
| ACLED conflicts | acleddata.com | ⬇️ 🔑 |
| AISStream positions | aisstream.io | ⬇️ 🔑 🔄 |
| VIIRS gas flaring | eogdata.mines.edu | ⬇️ |
| NASA FIRMS active fire | firms.modaps.eosdis.nasa.gov | ⬇️ |
| Climate TRACE emissions | climatetrace.org | ⬇️ |

---

## 23. Dati istituzionali / a pagamento

Non necessari per MVP desk; elencati per completezza roadmap.

| Vendor | Contenuto | Costo indicativo |
|--------|-----------|------------------|
| Nord Pool intraday RT | LOB 20 min delay | €4.5k+/regione/anno |
| EPEX SPOT CID EOD | tick trades | ~€910/anno |
| EPEX M7 API real-time | intraday LOB | ~€6.5k/anno |
| ICE Endex TTF/EUA RT | futures | membership |
| CME market data | NG/power futures | usage + license |
| Databento | EEX/ICE/CME normalized | da $199/mese |
| Kpler / Vortexa | LNG/coal/oil flows | €50k+/anno |
| Bloomberg / Refinitiv | everything | istituzionale |
| RS Metrics / Earth-i | satellite metals | istituzionale |
| World Climate Service | GWDD trader | ~$500+/mese |

---

## 24. Layout cache consigliato

```
cache/
  eia.key
  entsoe.key
  terna.key
  gie.key
  fred/              # {ID}.csv — migrare da flat attuale
  ecb/               # snapshot XML giornalieri
  eia/               # JSON annuali per paese + weekly
  entsoe/            # {BZ}_{A75|A65|A44}.csv
  terna/             # 61 dataset CSV
  gme/               # MI/MGP zip estratti
  stooq/             # OHLCV per symbol
  energy_charts/     # proxy prezzi EU
  eurostat/          # bilanci NRG
  meteo/             # open-meteo parquet/csv
  events/            # calendario JSON
```

---

## 25. Ordine di download consigliato

### Fase 0 — zero costo, sblocca subito (1 giorno)

1. Copia token: `euenergy_token.txt` → `cache/entsoe.key`
2. Registra e salva `cache/eia.key`
3. Aggiungi FRED mancanti ad alto impatto: `DTWEXBGS`, `DGS2`, `DGS5`, `T10YIE`, `SP500`
4. Scarica 7 serie US gen + 20 `PCEPET*` → `cache/fred/`
5. Copia slice `prices_unified.csv` → `cache/entsoe/prices/` (o symlink)

### Fase 1 — EU fundamentals (1 settimana)

6. Backfill ENTSO-E A75/A65/A44 per 12 zone (script `lac\hedge` o `math\data`)
7. `trn\download_terna.py` → tutti i 61 dataset
8. GIE AGSI+ daily storage EU
9. Stooq OHLCV 5y per 35 ticker §15.1

### Fase 2 — desk istituzionale (1 mese)

10. EIA country primary energy tutti i paesi §6.2
11. Energy-Charts live refresh + Ember annual
12. GME MI storico (credenziali APIService)
13. Espansione ticker §15.2
14. SEC EDGAR fundamentals top 20 issuer
15. Open-Meteo archive hub cities (LON, NYC, DXB, TYO per moon page meteo)

### Fase 3 — ricerca / alt (ongoing)

16. Bulk OPSD + OWID + IRENA
17. Shark tier bundle
18. OSM/PyPSA solo se serve mappa impianti
19. Valuta paid tier solo se serve LOB EU

---

## 26. Comandi e script sul PC

```bat
REM --- Token nel desk ---
copy C:\Users\jecho\Desktop\math\data\euenergy_token.txt C:\Users\jecho\Desktop\terminal\cache\entsoe.key

REM --- Terna bulk ---
cd C:\Users\jecho\Desktop\trn
python download_terna.py

REM --- ENTSO-E history (math) ---
cd C:\Users\jecho\Desktop\math\data
python fetch_entsoe_history.py
python fetch_entsoe_load_history.py
python fetch_entsoe_it_fundamentals.py

REM --- Hedge backfill (lac) ---
cd C:\Users\jecho\Desktop\lac\hedge
hedge backfill-entsoe-realized --from 2020-01-01 --to 2026-07-07
hedge backfill-meteo-pit --from 2024-03-14 --to 2026-07-07

REM --- Bundle esteso math ---
cd C:\Users\jecho\Desktop\math\data
python download_energy_data_bundle.py
python run_extended_opendata_bundle.py
python run_shark_tiers_bundle.py

REM --- Avvio desk (refresh FRED/ECB automatico) ---
cd C:\Users\jecho\Desktop\terminal
run.bat
```

---

## Riepilogo conteggi

| Categoria | Voci | Già ✅ | Da scaricare ⬇️ |
|-----------|------|--------|-----------------|
| FRED attive | 27 | 27 | 0 |
| FRED da aggiungere | ~35 | 0 | ~35 |
| FRED production (PCEPET + US gen) | 27 | 0 | 27 |
| EIA paesi + US weekly | ~30 | 0 | ~30 |
| ENTSO-E document types × zone | ~12 × 10 | parziale 📦 | ~100 serie |
| Terna Download Center | 61 | 0 | 61 |
| Terna API endpoints | 7 | 0 | 7 |
| Stooq OHLCV (attuale) | 35 | live only | 35 storici |
| Stooq espansione | ~115 | 0 | ~115 |
| Prezzi EU / TSO globali | ~25 fonti | 1 📦 | ~24 |
| Meteo / RES | ~15 | 0 | ~15 |
| Bilanci annuali | ~10 | 0 | ~10 |
| Eventi / REMIT | ~12 | 0 | ~12 |
| Infrastruttura GIS | ~10 | 0 | ~10 |
| Alt / geopolitica | ~15 | 0 | ~15 |
| Istituzionale 💰 | ~10 | — | opzionale |

**Totale voci tracciate:** **~500+** (inclusi dataset Terna singoli e combinazioni ENTSO-E zona×tipo).

---

*Documento correlato:* `docs/DATA_STORICO.md` (priorità implementazione codice) · *Fonti estese:* `lac\hedge\docs\global-speculative-data-sources.md` · `math\data\energy_data_sources_registry.json`
