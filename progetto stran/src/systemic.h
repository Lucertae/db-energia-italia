#ifndef SYSTEMIC_H
#define SYSTEMIC_H

#include "series.h"

typedef struct {
    float stress;         /* 0..100 composite */
    float vix_z;          /* VIX vs 90d mean (sigma) */
    float hy_chg_5d;      /* HY OAS 5d change bp */
    float btc_energy_rho; /* mean |rho90| BTC vs BRT/HUB/TTF */
    float curve_2s10s_bps;/* U10 − U2 in bp */
    float curve_5s30s_bps;/* U30 − U5 in bp */
    char  hot_a[4];
    char  hot_b[4];
    float hot_rho;
    int   ok;
} SystemicSnap;

void systemic_compute(const SeriesStore *st, SystemicSnap *out);

void systemic_paint_banner(HDC dc, const RECT *rc, const SeriesStore *st);

#endif
