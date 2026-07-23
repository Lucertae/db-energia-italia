# Dati storici per OPS DESK (desk serio)

Obiettivo: **5 anni daily** minimo su spot/macro, **10+ anni** dove disponibile su tassi/FX;
**weekly** su inventari; **monthly** su produzione/consumo; **annual** su bilanci energetici nazionali.

Stima spazio cache totale (CSV + JSON): **80–120 MB** (comprimibile a ~25 MB).

Legenda stato: **OK** = già in `sources.c` + cache; **PARZ** = parziale nel codice; **TODO** = da aggiungere.

---

## 1. Energia — petrolio e raffinazione

| ID | Serie / fonte | Freq | Storico | Stato | Note |
|----|---------------|------|---------|-------|------|
| BRT | FRED `DCOILBRENTEU` | daily | 5y+ | OK | Brent EU spot |
| WTI | FRED `DCOILWTICO` | daily | 5y+ | OK | WTI Cushing |
| CRU | FRED `WCESTUS1` | weekly | 5y+ | OK | Inventario crude US es-SPR |
| SPR | EIA `PET.WCESTUS1` (SPR) | weekly | 5y+ | TODO | Strategic petroleum reserve |
| BRE | ICE Brent futures curve M1–M12 | daily | 2y | TODO | Contango/backwardation |
| WTC | CME WTI futures curve | daily | 2y | TODO | |
| CR3 | Crack 3-2-1 (calc da futures) | daily | 2y | TODO | Margine raffinazione |
| RBO | FRED gasoline / heating oil | daily | 5y+ | TODO | Product cracks US |

---

## 2. Energia — gas

| ID | Serie / fonte | Freq | Storico | Stato | Note |
|----|---------------|------|---------|-------|------|
| HUB | FRED `DHHNGSP` | daily | 5y+ | OK | Henry Hub |
| TTF | FRED `PNGASEUUSDM` | daily | 5y+ | OK | Gas EU (proxy TTF) |
| JKM | FRED `PNGASJPUSDM` | daily | 5y+ | OK | LNG Asia |
| NGS | FRED `NGSTUS` | weekly | 5y+ | OK | Storage gas US |
| GIE | GIE AGSI+ / ALSI | daily | 3y | TODO | Storage gas EU % |
| HHF | CME Henry Hub futures | daily | 2y | TODO | Curva gas US |
| TTFF | ICE TTF futures | daily | 2y | TODO | Curva gas EU |
| LNG | GIIGNL / Kpler flows | monthly | 3y | TODO | Flussi LNG per rotta |

---

## 3. Energia — carbone, carbon, power

| ID | Serie / fonte | Freq | Storico | Stato | Note |
|----|---------------|------|---------|-------|------|
| COA | FRED `PCOALAUUSDM` | daily | 5y+ | OK | Coal Australia |
| EUA | ICE EUA / Ember | daily | 3y | TODO | Carbon EU — driver spread gas/coal |
| API2 | Coal API2 Rotterdam | daily | 5y | TODO | Dark spread EU |
| PWR_DE | ENTSOE DE generation | hourly→daily | 2y | TODO | Mix per fonte Germania |
| PWR_FR | ENTSOE FR | hourly→daily | 2y | TODO | |
| PWR_GB | ENTSOE/NGESO | hourly→daily | 2y | TODO | |
| PWR_IT | ENTSOE IT | hourly→daily | 2y | TODO | |
| PWR_ES | ENTSOE ES | hourly→daily | 2y | TODO | |
| SUN/US… | FRED `SUNEPUS` etc. | monthly | 10y | PARZ | Solo US in `production.c` |

---

## 4. FX — spot e cross

| ID | Serie / fonte | Freq | Storico | Stato | Note |
|----|---------------|------|---------|-------|------|
| EUR/USD… | ECB `eurofxref` | daily | live | OK | 29 valute live |
| EUF…GBF | FRED `DEX*` | daily | 5y+ | OK | USD pairs |
| CAD,NOK,SEK,CHF | FRED `DEXCAUS`, `DEXNOUS`… | daily | 5y+ | PARZ | CAD OK; NOK/SEK TODO |
| DXY | FRED `DTWEXBGS` | daily | 10y | TODO | Broad USD |
| XAU | FRED `GOLDAMGBD228NLBM` | daily | 10y | TODO | Gold — risk proxy |
| Cross EUR | derivati in `data.c` | daily | 5y+ | OK | EUR/JPY, EUR/BRL… |

---

## 5. Tassi e inflazione (WACC / DCF)

| ID | Serie / fonte | Freq | Storico | Stato | Note |
|----|---------------|------|---------|-------|------|
| U10 | FRED `DGS10` | daily | 10y+ | OK | US 10Y |
| U2 | FRED `DGS2` | daily | 10y+ | TODO | US 2Y |
| U5 | FRED `DGS5` | daily | 10y+ | TODO | Curva US |
| SOF | FRED `SOFR` | daily | 5y+ | OK | |
| E10 | FRED `IRLTLT01EZM156N` | daily | 10y+ | OK | EA 10Y |
| EDF | FRED `ECBDFR` | daily | 5y+ | OK | ECB deposit |
| Z10 | FRED `IRLTLT01ZAM156N` | daily | 10y+ | OK | ZA 10Y |
| BE5 | FRED `T5YIE` | daily | 10y+ | OK | Breakeven 5Y US |
| BE10 | FRED `T10YIE` | daily | 10y+ | TODO | Breakeven 10Y |
| EURIBOR | ECB / FRED | daily | 5y+ | TODO | CIP EUR legs |

---

## 6. Macro / risk

| ID | Serie / fonte | Freq | Storico | Stato | Note |
|----|---------------|------|---------|-------|------|
| VIX | FRED `VIXCLS` | daily | 10y+ | OK | |
| CPR | FRED `PCOPPUSDM` | daily | 10y+ | OK | Copper — proxy Cina |
| SPX | FRED `SP500` | daily | 10y+ | TODO | Risk-on |
| HYG | ETF / FRED | daily | 5y+ | TODO | Credit risk |
| OAS | ICE BofA HY OAS | daily | 10y+ | TODO | Costo debito energy |

---

## 7. Produzione / consumo per paese

| Paese | Produzione per fonte | Domanda/consumo | Fonte | Stato |
|-------|----------------------|-----------------|-------|-------|
| US | solar, wind, hydro, nuc, gas, coal, oil | TWh + Mtoe | FRED/EIA | PARZ |
| DE, FR, GB, IT, ES | mix elettrico | Mtoe | ENTSOE + EIA intl | TODO |
| CN, IN, JP, BR | — | petroleum Mtoe | FRED `PCEPET*` | PARZ |
| SA, RU, NO, AE | — | Mtoe | EIA API v2 | TODO (serve `cache/eia.key`) |
| EU27 | aggregato | Mtoe | Eurostat / IEA | TODO |

File chiave: `cache/eia.key` (API EIA gratuita).

---

## 8. Aziende (prezzi + fondamentali storici)

| Tier | Dati storici necessari | Fonte | Stato |
|------|------------------------|-------|-------|
| Major IOC / NOC | OHLCV daily 5y | Stooq / Yahoo | PARZ (solo last in `companies.c`) |
| Semi / refining | idem | Stooq | PARZ |
| Utility / distrib | idem | Stooq | PARZ |
| Fondamentali | revenue, FCF, debt, EV | SEC EDGAR / provider | TODO |
| Dividend yield | annual | FRED / issuer | TODO |

Catalogo: `src/data/companies.c` (~35 ticker); target **150–250** per desk globale.

---

## 9. Calendario / eventi (non serie ma necessari)

| Evento | Fonte | Uso |
|--------|-------|-----|
| EIA petroleum weekly | eia.gov | Volatilità crude |
| EIA gas storage | eia.gov | HH driver |
| FOMC, ECB, BoE | feed calendario | Rates |
| OPEC+ meeting | manuale/API | Supply shock |
| ENTSOE outages | transparency | Power EU |

---

## 10. Priorità implementazione

### Fase A — già coperta (mantieni cache aggiornata)
Tutte le serie **OK** in `src/data/sources.c` + cross EUR + ECB live.

### Fase B — alto impatto, fonti free
1. `DTWEXBGS` (DXY), `T10YIE`, `DGS2/5`
2. ENTSOE generation per DE/FR/IT/ES/GB (token free)
3. EIA weekly inventories + `eia.key` per Mtoe paesi
4. Stooq OHLCV storico 5y per catalogo aziende

### Fase C — desk istituzionale
1. Futures curves (Brent/WTI/HH/TTF)
2. EUA carbon
3. GIE gas storage EU
4. Fondamentali SEC per DCF su issuer
5. Eurostat/IEA annual balancio energetico completo

---

## Layout cache consigliato

```
cache/
  fred/          # CSV per id serie (attuale: flat *.csv → migrazione opzionale)
  ecb/           # snapshot XML giornalieri
  eia/           # JSON annuali per paese
  entsoe/        # generation per BZ
  stooq/         # OHLCV aziende
  eia.key        # API key (non committare)
```

Dimensioni indicative per **5y daily × 80 serie**: ~40 MB CSV.
