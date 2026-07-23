# Test-case: target sbagliato → segnale spurio robusto (PWR-01 v1)

**Modulo:** `bridge/backtest/pwr_v1_diagnostic.py`  
**Output:** `cache/spine/modules/backtest_pwr_v1_diagnostic.json`

## Meccanismo

Il vento deprime il prezzo DA **contemporaneo** P(D) (merit order, rinnovabili).  
Il target v1 era **Δ(D+1) = P(D+1) − P(D)** con feature vento a D.

Quando vento_D è alto:

1. P(D) è **basso** (effetto reale same-day)
2. Δ(D+1) tende **positivo** per mean-reversion / denominatore — non perché il vento “preveda” un prezzo alto domani

## Risultati PDE (2026-07-09)

| Test | IC | t_NW | Interpretazione |
|------|-----|------|-----------------|
| **A** vento vs P(D) | **−0.237** | −7.37 | Vento alto → prezzo oggi basso (merit order) |
| **B** vento vs Δ(D+1) | **+0.190** | +8.24 | Segnale v1 spurio (target sbagliato) |
| **C** P(D+1) \| P(D) | **+0.144** (vs B +0.190) | Parziale più debole — residuo non è edge |

**artifact_confirmed: true** su PDE → il t_NW=8.17 di PWR-01 v1 è riflesso meccanico, non edge.

## Cosa verifica il diagnostic

| Test | Atteso se artefatto |
|------|---------------------|
| **A** corr(vento_D, P(D)) | IC **negativo** forte |
| **B** corr(vento_D, Δ(D+1)) | IC **positivo** (v1 spurio) |
| **C** P(D+1) ~ vento + P(D) | IC parziale vento **debole** vs B |

Se A<0, B>0 e C<<B → **artifact_confirmed: true**.

## Uso nel gate

`backtest_pwr_signals` (PWR-01) **non promuove** — questo documento spiega *perché* il t_NW alto non è edge.

## v2 inference (2026-07-09)

| Split | Inferenza | Gate t |
|-------|-----------|--------|
| full / train / test | Pearson `t_ic` su serie oraria **contigua** | `min_t_nw` |
| conditional_* | **Block bootstrap** 24h, filtro ricalcolato in ogni replica | `min_t_boot` |

Non usare Newey-West su sotto-campioni condizionali (ore sparse) — produce t gonfiati (~20×).

Gate aggiuntivi conditional: `hit_rate_signed` (monotono), Spearman vs Pearson (`tail_signal`), `economic_edge` (|spread|·1{correct} − costi).

## v2

PWR-01-v2 usa delta forecast−published al gate e target `imbalance − DA` orario, con conditioning su decile |delta| e ore 4–11 m/s.
