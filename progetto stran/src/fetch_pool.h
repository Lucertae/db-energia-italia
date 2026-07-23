#ifndef FETCH_POOL_H
#define FETCH_POOL_H

#include "ingest.h"
#include <stddef.h>

#define FETCH_POOL_MAX 32

typedef struct {
    wchar_t url[512];
    char   *body;
    size_t  body_cap;
    size_t  len;
    DWORD   err;
    DWORD   status;
    int     ok;
} FetchSlot;

typedef struct {
    FetchSlot slot[FETCH_POOL_MAX];
    int       n;
} FetchPool;

void fetch_pool_init(FetchPool *p);
int  fetch_pool_add(FetchPool *p, const wchar_t *url, char *body, size_t cap);
int  fetch_pool_run(FetchPool *p, IngestSession *sess);

#endif
