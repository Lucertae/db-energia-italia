#include "fin.h"
#include <stdio.h>
#include <string.h>
#include <math.h>

static DataSeries mk_gbm(const char *id, int n, float mu, float sigma) {
    DataSeries s;
    int i;

    memset(&s, 0, sizeof(s));
    s.id[0] = id[0];
    s.id[1] = id[1];
    s.id[2] = id[2];
    s.n = (uint16_t)n;
    s.val[0] = 100.0f;
    s.ymd[0] = 20240101u;
    for (i = 1; i < n; i++) {
        float shock = (i % 7 == 0) ? sigma * 2.0f : -sigma * 0.3f;
        s.val[i] = s.val[i - 1] * (float)exp(mu + shock);
        s.ymd[i] = 20240101u + (uint32_t)i;
    }
    s.min_h = s.val[0];
    s.max_h = s.val[n - 1];
    return s;
}

int main(void) {
    DataSeries s = mk_gbm("TST", 300, 0.0002f, 0.02f);
    float rv, z, var, dd;
    int n;

    n = fin_logrets_tail(&s, 30, NULL, 0);
    if (n != 0) {
        fprintf(stderr, "fin_logrets_tail cap=0 should return 0, got %d\n", n);
        return 1;
    }

    rv = fin_rv_ann_pct(&s, 30, 0);
    if (rv <= 0.0f || rv > 200.0f) {
        fprintf(stderr, "fin_rv_ann_pct out of range: %.2f\n", rv);
        return 1;
    }

    z = fin_level_zscore(&s, 90);
    if (fabsf(z) > 10.0f) {
        fprintf(stderr, "fin_level_zscore extreme: %.2f\n", z);
        return 1;
    }

    var = fin_var95_pct(&s, 252);
    if (var < 0.0f) {
        fprintf(stderr, "fin_var95_pct negative: %.2f\n", var);
        return 1;
    }

    dd = fin_max_dd_pct(&s);
    if (dd < 0.0f) {
        fprintf(stderr, "fin_max_dd_pct negative: %.2f\n", dd);
        return 1;
    }

    printf("fin_test OK rv=%.1f%% z=%.2f var95=%.2f%% dd=%.1f%%\n", rv, z, var, dd);
    return 0;
}
