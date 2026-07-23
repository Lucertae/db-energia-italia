#include "corr.h"
#include <math.h>
#include <string.h>

int corr_align_logret(const DataSeries *a, const DataSeries *b,
                      float *ra, float *rb, int cap) {
    int i = 0, j = 0, n = 0;
    float prev_a = 0.0f, prev_b = 0.0f;
    int have_prev = 0;

    if (!a || !b || !ra || !rb || cap < 2) return 0;

    while (i < a->n && j < b->n && n < cap) {
        if (a->ymd[i] == b->ymd[j]) {
            float va = a->val[i], vb = b->val[j];
            if (have_prev && prev_a > 0.0f && prev_b > 0.0f && va > 0.0f && vb > 0.0f) {
                ra[n] = (float)log((double)va / (double)prev_a);
                rb[n] = (float)log((double)vb / (double)prev_b);
                n++;
            }
            prev_a = va;
            prev_b = vb;
            have_prev = 1;
            i++;
            j++;
        } else if (a->ymd[i] < b->ymd[j]) {
            i++;
        } else {
            j++;
        }
    }
    return n;
}

float corr_pearson(const float *x, const float *y, int n) {
    double sx = 0.0, sy = 0.0, sxx = 0.0, syy = 0.0, sxy = 0.0;
    int i;

    if (!x || !y || n < 3) return 0.0f;
    for (i = 0; i < n; i++) {
        sx += x[i];
        sy += y[i];
        sxx += (double)x[i] * x[i];
        syy += (double)y[i] * y[i];
        sxy += (double)x[i] * y[i];
    }
  {
    double den = (n * sxx - sx * sx) * (n * syy - sy * sy);
    double num = n * sxy - sx * sy;
    if (den <= 1e-18) return 0.0f;
    return (float)(num / sqrt(den));
  }
}

float corr_beta(const float *y, const float *x, int n) {
    double sx = 0.0, sy = 0.0, sxx = 0.0, sxy = 0.0;
    int i;

    if (!x || !y || n < 3) return 0.0f;
    for (i = 0; i < n; i++) {
        sx += x[i];
        sy += y[i];
        sxx += (double)x[i] * x[i];
        sxy += (double)x[i] * y[i];
    }
  {
    double den = n * sxx - sx * sx;
    if (fabs(den) < 1e-18) return 0.0f;
    return (float)((n * sxy - sx * sy) / den);
  }
}

static void corr_window(const float *ra, const float *rb, int total, int win,
                        float *rho, int *nout) {
    int start;

    if (rho) *rho = 0.0f;
    if (nout) *nout = 0;
    if (total < 5) return;
    start = total > win ? total - win : 0;
    if (nout) *nout = total - start;
    if (rho && total - start >= 3)
        *rho = corr_pearson(ra + start, rb + start, total - start);
}

void corr_pair_compute(const DataSeries *a, const DataSeries *b, CorrPair *out) {
    static float ra[SER_POINTS];
    static float rb[SER_POINTS];
    int n;

    if (!out) return;
    memset(out, 0, sizeof(*out));
    if (!a || !b || a->n < 5 || b->n < 5) return;

    n = corr_align_logret(a, b, ra, rb, SER_POINTS);
    if (n < 5) return;

    corr_window(ra, rb, n, 30, &out->rho30, &out->n30);
    corr_window(ra, rb, n, 90, &out->rho90, &out->n90);
    corr_window(ra, rb, n, 252, &out->rho252, &out->n252);
    if (out->n90 >= 5)
        out->beta90 = corr_beta(ra + (n - out->n90), rb + (n - out->n90), out->n90);
    out->ok = out->n90 >= 5;
}

int corr_strongest(const SeriesStore *st, const char (*pairs)[2][4], int npairs,
                   char out_a[4], char out_b[4], float *out_rho) {
    int i;
    float best = -2.0f;
    int found = 0;

    if (!st || !pairs || npairs <= 0) return 0;
    for (i = 0; i < npairs; i++) {
        const DataSeries *a = series_get((SeriesStore *)st, pairs[i][0]);
        const DataSeries *b = series_get((SeriesStore *)st, pairs[i][1]);
        CorrPair cp;

        if (!a || !b) continue;
        corr_pair_compute(a, b, &cp);
        if (!cp.ok) continue;
        if (fabsf(cp.rho90) > best) {
            best = fabsf(cp.rho90);
            if (out_a) lstrcpynA(out_a, pairs[i][0], 4);
            if (out_b) lstrcpynA(out_b, pairs[i][1], 4);
            if (out_rho) *out_rho = cp.rho90;
            found = 1;
        }
    }
    return found;
}
