#ifndef FIN_H
#define FIN_H

#include "series.h"

#define FIN_LAMBDA_EWMA 0.94
#define FIN_DAYS_EQ     252.0
#define FIN_DAYS_CRYPTO 365.0

float fin_logret_at(const DataSeries *s, int end_idx);

/* Ultimi nret rendimenti log consecutivi (fine serie). */
int fin_logrets_tail(const DataSeries *s, int nret, float *out, int cap);

float fin_stdev(const float *x, int n);

/* Vol realizzata annualizzata (%), rendimenti log. crypto!=0 → 365gg. */
float fin_rv_ann_pct(const DataSeries *s, int win, int crypto);

/* Z-score dell'ultimo livello vs finestra trailing. */
float fin_level_zscore(const DataSeries *s, int win);

/* Z-score dell'ultimo rendimento log vs finestra trailing. */
float fin_ret_zscore(const DataSeries *s, int win);

/* EWMA vol annualizzata (%), lambda=FIN_LAMBDA_EWMA. */
float fin_ewma_vol_ann(const DataSeries *s, int win, int crypto);

/* VaR storico 95% su rendimenti log, perdita positiva in %. */
float fin_var95_pct(const DataSeries *s, int win);

/* Max drawdown % sull'intera serie. */
float fin_max_dd_pct(const DataSeries *s);

/* Spread tassi in bp: long_id − short_id (serie in %). */
int fin_yield_spread_bps(const SeriesStore *st, const char *long_id,
                         const char *short_id, float *out_bps);

/* Percentile rank 0..100 dell'ultimo valore nella finestra. */
float fin_percentile_rank(const DataSeries *s, int win);

#endif
