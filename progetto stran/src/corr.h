#ifndef CORR_H
#define CORR_H

#include "series.h"

typedef struct {
    float rho30;
    float rho90;
    float rho252;
    float beta90;
    int   n30;
    int   n90;
    int   n252;
    int   ok;
} CorrPair;

/* Allinea due serie per data, calcola rendimenti log giornalieri consecutivi. */
int corr_align_logret(const DataSeries *a, const DataSeries *b,
                      float *ra, float *rb, int cap);

float corr_pearson(const float *x, const float *y, int n);
float corr_beta(const float *y, const float *x, int n);

void corr_pair_compute(const DataSeries *a, const DataSeries *b, CorrPair *out);

/* Coppia con |rho90| massimo tra elenco (per status bar). */
int corr_strongest(const SeriesStore *st, const char (*pairs)[2][4], int npairs,
                   char out_a[4], char out_b[4], float *out_rho);

#endif
