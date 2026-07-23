#include "corr.h"
#include <stdio.h>
#include <string.h>

static DataSeries mk(const char *id, int n) {
    DataSeries s;
    int i;
    memset(&s, 0, sizeof(s));
    s.id[0] = id[0]; s.id[1] = id[1]; s.id[2] = id[2];
    s.n = (uint16_t)n;
    for (i = 0; i < n; i++) {
        s.ymd[i] = 20240101u + (uint32_t)i;
        s.val[i] = 100.0f + (float)i * 0.5f;
    }
    return s;
}

int main(void) {
    DataSeries a = mk("AAA", 120);
    DataSeries b = mk("BBB", 120);
    int i;
    CorrPair cp;

    for (i = 0; i < 120; i++)
        b.val[i] = 50.0f + (float)i * 0.25f;

    corr_pair_compute(&a, &b, &cp);
    if (!cp.ok) {
        fprintf(stderr, "corr_pair_compute failed n90=%d\n", cp.n90);
        return 1;
    }
    if (cp.rho90 < 0.99f) {
        fprintf(stderr, "expected rho~1, got %.3f\n", cp.rho90);
        return 1;
    }
    printf("corr_test OK rho90=%.3f beta=%.3f n=%d\n", cp.rho90, cp.beta90, cp.n90);
    return 0;
}
