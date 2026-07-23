#include "fin.h"
#include <math.h>
#include <string.h>

float fin_logret_at(const DataSeries *s, int end_idx) {
    float a, b;

    if (!s || end_idx < 1 || end_idx >= (int)s->n) return 0.0f;
    a = s->val[end_idx - 1];
    b = s->val[end_idx];
    if (a <= 0.0f || b <= 0.0f) return 0.0f;
    return (float)log((double)b / (double)a);
}

int fin_logrets_tail(const DataSeries *s, int nret, float *out, int cap) {
    int i, n = 0, start;

    if (!s || !out || cap < 1 || s->n < 2 || nret < 1) return 0;
    start = (int)s->n - nret - 1;
    if (start < 0) start = 0;
    for (i = start + 1; i < (int)s->n && n < cap; i++) {
        out[n++] = fin_logret_at(s, i);
        if (n >= nret) break;
    }
    return n;
}

float fin_stdev(const float *x, int n) {
    double sum = 0.0, sum2 = 0.0, m, v;
    int i;

    if (!x || n < 2) return 0.0f;
    for (i = 0; i < n; i++) {
        sum += x[i];
        sum2 += (double)x[i] * x[i];
    }
    m = sum / n;
    v = (sum2 - n * m * m) / (n - 1);
    if (v < 1e-18) return 0.0f;
    return (float)sqrt(v);
}

float fin_rv_ann_pct(const DataSeries *s, int win, int crypto) {
    float rets[512];
    int n;
    double scale;

    if (!s || win < 2) return 0.0f;
    if (win > 512) win = 512;
    n = fin_logrets_tail(s, win, rets, win);
    if (n < 2) return 0.0f;
    scale = crypto ? sqrt(FIN_DAYS_CRYPTO) : sqrt(FIN_DAYS_EQ);
    return fin_stdev(rets, n) * (float)scale * 100.0f;
}

float fin_level_zscore(const DataSeries *s, int win) {
    int i, start, cnt = 0;
    double sum = 0.0, sum2 = 0.0, m, v, last;

    if (!s || s->n < 10) return 0.0f;
    if (win < 5) win = 5;
    start = (int)s->n - win;
    if (start < 0) start = 0;
    for (i = start; i < (int)s->n; i++) {
        sum += s->val[i];
        sum2 += (double)s->val[i] * s->val[i];
        cnt++;
    }
    if (cnt < 5) return 0.0f;
    m = sum / cnt;
    v = sum2 / cnt - m * m;
    if (v < 1e-12) return 0.0f;
    last = series_last(s);
    return (float)((last - m) / sqrt(v));
}

float fin_ret_zscore(const DataSeries *s, int win) {
    float rets[512];
    int n;
    double m, v, last;

    if (!s || win < 5) return 0.0f;
    if (win > 512) win = 512;
    n = fin_logrets_tail(s, win, rets, win);
    if (n < 5) return 0.0f;
    {
        double sum = 0.0, sum2 = 0.0;
        int i;
        for (i = 0; i < n - 1; i++) {
            sum += rets[i];
            sum2 += (double)rets[i] * rets[i];
        }
        m = sum / (n - 1);
        v = sum2 / (n - 1) - m * m;
        if (v < 1e-18) return 0.0f;
        last = rets[n - 1];
        return (float)((last - m) / sqrt(v));
    }
}

static void fin_sort_asc(float *a, int n) {
    int i, j;

    for (i = 1; i < n; i++) {
        float key = a[i];
        j = i - 1;
        while (j >= 0 && a[j] > key) {
            a[j + 1] = a[j];
            j--;
        }
        a[j + 1] = key;
    }
}

float fin_var95_pct(const DataSeries *s, int win) {
    float rets[512];
    int n, idx;
    float q;

    if (!s || win < 20) return 0.0f;
    if (win > 512) win = 512;
    n = fin_logrets_tail(s, win, rets, win);
    if (n < 20) return 0.0f;
    fin_sort_asc(rets, n);
    idx = (int)((0.05 * (double)n) + 0.5);
    if (idx < 0) idx = 0;
    if (idx >= n) idx = n - 1;
    q = rets[idx];
    return q < 0.0f ? -q * 100.0f : 0.0f;
}

float fin_ewma_vol_ann(const DataSeries *s, int win, int crypto) {
    float rets[512];
    int n, i;
    double var, scale;

    if (!s || win < 5) return 0.0f;
    if (win > 512) win = 512;
    n = fin_logrets_tail(s, win, rets, win);
    if (n < 5) return 0.0f;
    var = (double)rets[0] * (double)rets[0];
    for (i = 1; i < n; i++) {
        double r = rets[i];
        var = FIN_LAMBDA_EWMA * var + (1.0 - FIN_LAMBDA_EWMA) * r * r;
    }
    scale = crypto ? sqrt(FIN_DAYS_CRYPTO) : sqrt(FIN_DAYS_EQ);
    return (float)(sqrt(var) * scale * 100.0);
}

float fin_max_dd_pct(const DataSeries *s) {
    float peak, max_dd = 0.0f;
    int i;

    if (!s || s->n < 2) return 0.0f;
    peak = s->val[0];
    for (i = 0; i < (int)s->n; i++) {
        float v = s->val[i];
        if (v > peak) peak = v;
        if (peak > 0.0f) {
            float dd = (peak - v) / peak;
            if (dd > max_dd) max_dd = dd;
        }
    }
    return max_dd * 100.0f;
}

int fin_yield_spread_bps(const SeriesStore *st, const char *long_id,
                         const char *short_id, float *out_bps) {
    const DataSeries *lg, *sh;
    float spread;

    if (!st || !long_id || !short_id || !out_bps) return 0;
    lg = series_get((SeriesStore *)st, long_id);
    sh = series_get((SeriesStore *)st, short_id);
    if (!lg || !sh || lg->n < 1 || sh->n < 1) return 0;
    spread = series_last(lg) - series_last(sh);
    *out_bps = spread * 100.0f;
    return 1;
}

float fin_percentile_rank(const DataSeries *s, int win) {
    float last, below = 0.0f;
    int i, n, start;

    if (!s || s->n < 3 || win < 3) return 50.0f;
    n = (int)s->n;
    start = n - win;
    if (start < 0) start = 0;
    last = series_last(s);
    for (i = start; i < n; i++) {
        if (s->val[i] <= last) below += 1.0f;
    }
    return below / (float)(n - start) * 100.0f;
}
