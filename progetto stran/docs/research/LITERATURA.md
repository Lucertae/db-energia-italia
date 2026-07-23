# Letteratura e metodologia — OPS DESK research layer

**Aggiornato:** 2026-07-07  
**Scopo:** tradurre ricerca accademica recente in regole operative per ingest, pulizia, feature e pre-analisi.

---

## 1. Cosa dice l'accademia (sintesi)

### 1.1 Petrolio — inventari e prezzo

- [Qu & Li, Energy Economics 2023](https://ideas.repec.org/a/eee/eneeco/v120y2023ics0140988323001019.html): i cambiamenti di inventario crude hanno dinamiche **multi-frequenza** (buffering lungo periodo, speculazione corto). Metodi wavelet + ARDL-SVR battono benchmark istituzionali su **sign consistency** (+19%).
- [MDPI Forecasting 2025](https://www.mdpi.com/2504-4990/7/4/127): su orizzonte daily (2015–2024), i predittori più forti per oil returns sono **VIX, OVX, MOVE** e lagged returns; meta-learner R² ≈ 0.53 out-of-sample vs ~0 per random walk.
- [Financial Innovation 2025](https://doi.org/10.1186/s40854-025-00837-1): forecasting crude richiede **multisource predictors + factor screening + forecast combination**; sliding window obbligatorio; nessun singolo modello domina tutti i regimi.
- [Computers 2026](https://www.mdpi.com/2073-431X/15/2/88): evitare **lookahead bias** — usare solo lagged prices + variabili disponibili al tempo t; decomposizione serie prima del fit.

**Implicazioni desk:**
- Trattare inventario (CRU/EIA weekly) come segnale **separato** dal prezzo spot, non come semplice correlazione contemporanea.
- Includere indici volatilità (VIX minimo; OVX se disponibile) come feature macro.
- Validare segnali con **rolling window**, non su tutto lo storico in-sample.

### 1.2 Gas — theory of storage

- [Journal of Commodity Markets 2023](https://doi.org/10.1016/j.jcomm.2022.100310): theory of storage spiega **parzialmente** il gas EU/UK; convenience yield dipende da volatilità spot, shock domanda, **livelli inventario**, attività futures.
- [Energy Economics 2009 — Fama-French tests EU](https://www.sciencedirect.com/science/article/abs/pii/S0301421509005898): NBP/TTF/Zeebrugge — arbitraggio stagionale esiste ma **non** al benchmark competitivo puro; basis e inventory weakly coupled.
- [Journal of Applied Econometrics 2024](https://doi.org/10.1002/jae.3089): shock 2022 Germania — prezzo guidato da **flow supply** (Russia) + **storage demand shocks** (riempimento pre-inverno); SVAR necessario per interpretare regimi.
- [Journal of Cleaner Production 2024](https://www.sciencedirect.com/science/article/abs/pii/S0301479723012343): post-Ucraina, modelli ibridi (feature selection + SVR) su Henry Hub; variabili esogene (inventario, meteo) migliorano MAPE.

**Implicazioni desk:**
- HUB (daily HH spot) e TTF (proxy FRED monthly USD/MMBtu) **non sono omogenei** — allineare a frequenza comune prima di correlare.
- Segnali gas da studiare: **spread TTF−HUB**, deviazione inventario US da media stagionale, basis proxy.
- Regime 2022+ è strutturalmente diverso — pre-analisi deve essere **sub-period aware**.

### 1.3 Qualità dati e point-in-time

- [Macrosynergy — PIT economics](https://macrosynergy.com/research/point-in-time-economics-and-financial-market-forecasting/): backtest su dati finali = **lookahead bias**; serve vintage per macro.
- [Journal of Applied Econometrics 2023 — BVAR under revision](https://ideas.repec.org/a/wly/japmet/v38y2023i2p164-185.html): density forecast migliora modellando esplicitamente revisioni.
- [Clements — Encyclopedia of Forecasting (Reading)](https://centaur.reading.ac.uk/78512/1/encyc_final.pdf): approcci — ignorare revisioni (convenzionale), modellare revisioni, usare dati largely unrevised.
- [CRAN reviser](https://doi.org/10.32614/cran.package.reviser): toolkit per news/noise decomposition su vintage.

**Implicazioni desk:**
- FRED spot/inventari EIA: rischio revisione **basso** → candidati Phase 1.
- Macro (CPI, UNRATE) e ENTSO-E realized: Phase 2 con vintage.
- Ogni run research deve loggare **data vintage** (mtime file cache).

### 1.4 Feature engineering energia (survey)

- [IOPscience SLR deep learning energy 2025](https://beta.iopscience.iop.org/article/10.1088/2631-8695/ae76d8): performance dipende da **preprocessing + decomposition + market context**; nessun modello universale.
- [Computers & Chemical Engineering 2024 — EPIC](https://doi.org/10.1016/j.compchemeng.2024.108740): framework ibrido — stagionalità, trend, outlier detection prima del fit; DNN > ARIMA su molti prodotti ma non tutti.
- [MDPI Energies 2025](https://www.mdpi.com/1996-1073/18/6/1387): Fourier terms, differencing, window stats, SARIMAX + XGBoost residual.
- [Applied Sciences 2020 — technical indicators power](https://www.mdpi.com/2076-3417/10/1/255): EMA, Bollinger su electricity prices migliorano ML lineari.
- [Energy Informatics 2025](https://link.springer.com/article/10.1186/s42162-025-00583-9): VMD/CEEMD decomposition + feature selection prima di LSTM.

**Implicazioni desk — pipeline minima accettabile:**
1. QA: coverage, gap, outlier, unità, freq
2. Clean: missing policy documentata, winsorize opzionale, business-day align
3. Features: returns, log-returns, rolling vol/z-score, spread, seasonal deviation (inventari)
4. Explore: correlazione rolling, cross-correlation lead-lag, stabilità per sub-periodo
5. Solo dopo: portare segnale validato nel terminale C

---

## 2. Priorità implementazione (derivata da letteratura)

| Priorità | Dominio | Serie desk | Ipotesi da testare | Fonte |
|----------|---------|------------|-------------------|-------|
| P0 | Gas US/EU | HUB, TTF, NGS | Storage deviation → HUB returns (lag 1–4 sett.) | Theory of storage |
| P0 | Gas spread | TTF, HUB | Spread mean-reverts con regime breaks 2022 | JAE 2024 |
| P1 | Oil + vol | BRT, CRU, VIX | VIX lagged → BRT daily returns | MDPI 2025 |
| P1 | Oil inventory | CRU, BRT | Inventory change sign vs price direction | Energy Economics 2023 |
| P2 | Power EU | ENTSO-E DA | HDD + wind forecast → price (da math/data) | IOP SLR 2025 |
| P3 | Macro PIT | CPI, UNRATE | Vintage-aware only | Macrosynergy |

---

## 3. Metriche di validazione segnale

Adottiamo standard da letteratura forecasting:

| Metrica | Uso | Soglia indicativa |
|---------|-----|-------------------|
| Rolling Pearson ρ | Associazione lineare | \|ρ\| > 0.15 su finestra 252d |
| Lead-lag CCF peak | Timing segnale | Lag esplicito, no contemporaneo se causale |
| Sign consistency | Inventario → prezzo | > 55% out-of-sample |
| Sub-period stability | Regime 2022+ | Segnale non deve esistere solo pre-2020 |
| Coverage QA | Affidabilità dato | > 95% giorni attesi, gap documentati |

---

## 4. Anti-pattern (da evitare)

1. Correlare TTF monthly con HUB daily senza resampling.
2. Usare `.` FRED come zero invece di NaN.
3. Backtest su CPI/UNRATE senza vintage.
4. Trattare PNGASEUUSDM (FRED proxy) come TTF futures ICE.
5. Ottimizzare ML prima di QA e allineamento temporale.

---

## Sources

- [Qu & Li 2023 — oil inventory forecasting](https://ideas.repec.org/a/eee/eneeco/v120y2023ics0140988323001019.html)
- [MDPI 2025 — short-term oil forecasting](https://www.mdpi.com/2504-4990/7/4/127)
- [Financial Innovation 2025 — multisource crude oil](https://doi.org/10.1186/s40854-025-00837-1)
- [Computers 2026 — crude oil futures attention](https://www.mdpi.com/2073-431X/15/2/88)
- [Martínez & Torró 2023 — theory of storage EU gas](https://doi.org/10.1016/j.jcomm.2022.100310)
- [Pirker et al. 2009 — Fama-French EU gas storage](https://www.sciencedirect.com/science/article/abs/pii/S0301421509005898)
- [Breitenlechner et al. 2024 — German gas SVAR](https://doi.org/10.1002/jae.3089)
- [Macrosynergy — point-in-time economics](https://macrosynergy.com/research/point-in-time-economics-and-financial-market-forecasting/)
- [Clements & Galvão 2023 — BVAR under data uncertainty](https://ideas.repec.org/a/wly/japmet/v38y2023i2p164-185.html)
- [IOPscience 2025 — deep learning energy SLR](https://beta.iopscience.iop.org/article/10.1088/2631-8695/ae76d8)
- [Baratsas et al. 2024 — EPIC framework](https://doi.org/10.1016/j.compchemeng.2024.108740)
