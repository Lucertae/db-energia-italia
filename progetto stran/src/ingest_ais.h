#ifndef INGEST_AIS_H
#define INGEST_AIS_H

#include "common.h"
#include <stdint.h>

BOOL ingest_ais_load_key(char *out, size_t cap);
BOOL ingest_ais_json_float(const char *json, const char *key, float *out);
BOOL ingest_ais_json_uint(const char *json, const char *key, uint32_t *out);

#endif
