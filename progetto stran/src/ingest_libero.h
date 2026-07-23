#ifndef INGEST_LIBERO_H
#define INGEST_LIBERO_H

#include "common.h"
#include <stdint.h>

#define LIBERO_REFRESH_SEC  21600

int  ingest_libero_refresh(uint32_t max_age_sec);
BOOL ingest_libero_cache_age(const char *id, uint32_t *age_sec);
int  ingest_libero_cvi_from_btc(void);

#endif
