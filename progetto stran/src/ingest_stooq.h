#ifndef INGEST_STOOQ_H
#define INGEST_STOOQ_H

#include "common.h"
#include <stddef.h>

/* Stooq daily last close: symbol es. "xom.us" */
BOOL ingest_stooq_quote(const char *symbol, float *out_close, float *out_prev);

/* Batch fino a 16 simboli, fn(symbol, close, prev, ctx) per ogni riga ok */
typedef void (*StooqFn)(const char *symbol, float close, float prev, void *ctx);
int ingest_stooq_batch(const char **symbols, int n, StooqFn fn, void *ctx);

#endif
