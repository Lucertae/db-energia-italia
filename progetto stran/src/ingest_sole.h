#ifndef INGEST_SOLE_H
#define INGEST_SOLE_H

#include "common.h"
#include <stddef.h>

BOOL ingest_json_last_float(const char *json, const char *key, float *out);
BOOL ingest_json_float(const char *json, const char *key, float *out);
BOOL ingest_json_last_string(const char *json, const char *key, char *out, size_t cap);
BOOL ingest_ace_swepam_last(const char *text, float *density, float *speed_kms);

/* Open-Meteo multi-location: "key":[v1,v2,...] */
BOOL ingest_json_float_array(const char *json, const char *key, float *out, int max_n, int *out_n);

#endif
