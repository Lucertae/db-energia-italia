#ifndef INGEST_H
#define INGEST_H

#include "common.h"
#include <stddef.h>
#include <stdint.h>

#define INGEST_BODY_MAX (256 * 1024)

typedef struct IngestSession IngestSession;
typedef void (*IngestFxFn)(const char *iso3, double eur_rate, void *ctx);

IngestSession *ingest_session_open(void);
void ingest_session_close(IngestSession *s);
BOOL ingest_session_get(IngestSession *s, const wchar_t *url, char *buf, size_t cap, size_t *out_len);

BOOL ingest_http_get(const wchar_t *url, char *buf, size_t cap, size_t *out_len);
int  ingest_ecb_fx(const char *xml, size_t len, IngestFxFn fn, void *ctx);
BOOL ingest_fred_last(const char *csv, size_t len, double *out);
int  ingest_fred_hist(const char *csv, size_t len, uint32_t *ymd, float *val, int max_n);
void ingest_fred_url(const char *series_id, int days, wchar_t *url, int cap);
BOOL ingest_fred_fetch(const char *series_id, char *buf, size_t cap, double *out);
BOOL ingest_fred_fetch_ex(IngestSession *s, const char *series_id, char *buf, size_t cap, double *out);
int  ingest_fred_fetch_hist_ex(IngestSession *s, const char *series_id, char *buf, size_t cap,
                               uint32_t *ymd, float *val, int max_n, float *out_live, int days);
DWORD ingest_last_error(void);
DWORD ingest_last_status(void);

#endif
