# Segnali da studiare — OPS DESK

**Aggiornato:** 2026-07-07  
**Metodo:** ipotesi derivate da letteratura → test in `research/` → promozione al desk solo se stabili.

Legenda stato: `TODO` | `TESTING` | `VALIDATED` | `REJECTED` | `BLOCKED` (dati mancanti)

---

## Dominio GAS (P0)

| ID | Ipotesi | Feature | Letteratura | Stato | Note |
|----|---------|---------|-------------|-------|------|
| GAS-01 | Inventario US sopra media stagionale → pressione ribassista su HUB con lag 1–4 sett. | `ngs_deviation_pct`, `ngs_change_pct` → `hub_logret` | Theory of storage; J. Commodity Markets 2023 | TESTING | NGS via FRED NGSTUS; live z in spine |
| GAS-02 | Spread TTF−HUB mean-reverting con break strutturale 2022 | `ttf_hub_spread`, `spread_z_36m` | JAE 2024 German gas SVAR | TESTING | **ρ=0.41 full, 0.45 post-2022** (p<0.001) — candidato forte |
| GAS-03 | VIX lagged → hub returns (risk-off → gas demand proxy) | `vix_lag1m` → `hub_logret_1m` | MDPI oil forecasting 2025 (vol spillover) | REJECTED | ρ≈0, non significativo su monthly |
| GAS-04 | Convenience yield slope ↔ inventory (EU) | GIE AGSI % + TTF futures | Fama-French EU gas 2009 | BLOCKED | Serve GIE API + TTF ICE |
| GAS-05 | HUB e TTF returns co-movement instabile nel tempo | rolling ρ 24m | EPIC 2024 regime dependence | TESTING | vedi `gas_report.md` |

**Soglie promozione desk:**
- \|ρ\| > 0.15 su `full` E stabile segno su almeno 2 sub-periodi, oppure
- lead-lag CCF con lag ≥ 1 e \|ccf\| > 0.2 su n ≥ 36 mesi

---

## Dominio OIL (P1)

| ID | Ipotesi | Feature | Letteratura | Stato | Note |
|----|---------|---------|-------------|-------|------|
| OIL-01 | VIX/OVX lagged → BRT daily returns | `vix_lag`, `ovx_lag` | MDPI 2025 meta-learner | TODO | OVX da aggiungere |
| OIL-02 | Inventory change sign → BRT direction | ΔCRU weekly → BRT 5d return | Qu & Li 2023 inventory | TODO | CRU = EIA weekly |
| OIL-03 | Multisource factor screen batte univariato | panel 8 categorie | Financial Innovation 2025 | TODO | Phase 3 |
| OIL-04 | Brent-WTI spread ↔ US inventory glut | `brt_wti_spread`, CRU z | Classic storage | TODO | |

---

## Dominio POWER EU (P2)

| ID | Ipotesi | Feature | Letteratura | Stato | Note |
|----|---------|---------|-------------|-------|------|
| PWR-01 | Wind/solar forecast error → DA price spike | ENTSO-E gen + forecast | IOP SLR 2025 | BLOCKED | `math/data` integration |
| PWR-02 | HDD/CDD → gas/power co-movement | meteo hub cities | EPIC / hybrid ML 2024 | TODO | Open-Meteo archive |
| PWR-03 | Technical indicators (EMA, Bollinger) su DA IT | da `prices_unified.csv` | Applied Sciences 2020 | BLOCKED | 162 MB import |

---

## Dominio MACRO (P3 — PIT obbligatorio)

| ID | Ipotesi | Feature | Letteratura | Stato | Note |
|----|---------|---------|-------------|-------|------|
| MAC-01 | CPI first-release vs final → false signals | vintage CPI | Macrosynergy PIT | BLOCKED | vintage DB |
| MAC-02 | UNRATE revision noise | reviser news/noise | Clements 2023 BVAR | BLOCKED | |

---

## Dominio MARITTIMO — chokepoints (P0 post-2026)

| ID | Ipotesi | Feature | Letteratura / fonte | Stato | Note |
|----|---------|---------|---------------------|-------|------|
| MAR-01 | Hormuz transits ↓ → BRT premium + lag 5–10d | AIS count HORMUZ bbox | IEA, EIA, Windward mar 2026 | TODO | Richiede AIS o PortWatch |
| MAR-02 | Malacca transiti ↑ quando Hormuz stress | ratio MALACCA/HORMUZ | VanEck 2025 sequential nodes | TODO | **84% Hormuz oil → Asia via Malacca** |
| MAR-03 | Sunda+Lombok ↑ = VLCC stress / draft limit | RT-05 ratio | Ballast Markets, Eurasia Review 2026 | TODO | <5% volume ma leading indicator |
| MAR-04 | Fujairah loadings ↑ = bypass UAE attivo | RT-02 vs Hormuz | IEA ADCOP, National May 2026 | TODO | Espansione 3.4 mb/d |
| MAR-05 | Cape transits vs 7d MA ↑ = global reroute | RT-06 | Anadolu mar 2026 (+35%) | TODO | +10–20 gg, +freight |
| MAR-06 | Qatar LNG blocked → JKM spike, TTF decouple | LNG AIS Hormuz | IEA: no pipeline bypass | BLOCKED | 100% Ras Laffan via Hormuz |
| MAR-07 | Myanmar pipeline = marginal Malacca bypass | Kyaukpyu VLCC | Atlas 2025: 0.44 vs 6.5 mb/d | TODO | Strategic not volume |

**Documento completo:** `docs/research/CHOKEPOINTS_ROUTES.md`  
**Catalogo bbox AIS:** `research/chokepoints_catalog.json`

---

```bat
cd C:\Users\jecho\Desktop\terminal
python research\run_gas.py
type research\output\gas_report.md
```

Prossimi script:
- `research/run_oil.py` — BRT, CRU, VIX
- `research/run_chokepoints.py` — corridoi AIS / catalogo rotte
- `research/run_all.py` — orchestrator + summary

---

## Riferimenti

Vedi `docs/research/LITERATURA.md` per bibliografia completa e regole anti-pattern.
