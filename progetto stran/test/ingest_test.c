#include <stdio.h>
#include "ingest.h"
#include "series.h"
#include "histdb.h"

static void count_fx(const char *iso, double rate, void *ctx) {
    int *n = (int *)ctx;
    (void)iso;
    (void)rate;
    (*n)++;
}

static uint32_t ymd[SER_POINTS];
static float val[SER_POINTS];
static char body[INGEST_BODY_MAX];

int main(void) {
    size_t len = 0;
    int n = 0;
    float live = 0.0f;
    IngestSession *s;

    s = ingest_session_open();
    if (!s) {
        printf("session FAIL\n");
        return 1;
    }

    if (ingest_session_get(s, L"https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml",
                           body, sizeof(body), &len)) {
        n = ingest_ecb_fx(body, len, count_fx, &n);
        printf("ECB OK len=%u pairs=%d\n", (unsigned)len, n);
    } else {
        printf("ECB FAIL status=%u err=%u\n", ingest_last_status(), ingest_last_error());
    }

    n = ingest_fred_fetch_hist_ex(s, "DCOILBRENTEU", body, sizeof(body),
                                  ymd, val, SER_POINTS, &live, 1900);
    if (n > 0) {
        printf("FRED Brent hist n=%d  first=%u %.2f  last=%u %.2f  live=%.2f\n",
               n, ymd[0], val[0], ymd[n - 1], val[n - 1], live);
        histdb_init();
        if (histdb_save("BRT", body, strlen(body)))
            printf("cache save OK\n");
        if (histdb_load("BRT", body, sizeof(body), &len, 3600)) {
            n = ingest_fred_hist(body, len, ymd, val, SER_POINTS);
            printf("cache load OK n=%d\n", n);
        }
    } else {
        printf("FRED hist FAIL status=%u err=%u\n", ingest_last_status(), ingest_last_error());
    }

    n = ingest_fred_fetch_hist_ex(s, "DEXJPUS", body, sizeof(body),
                                  ymd, val, SER_POINTS, &live, 1900);
    printf("FRED JPY hist n=%d live=%.2f\n", n, live);

    ingest_session_close(s);
    return 0;
}
