#include "ingest_ais.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

BOOL ingest_ais_load_key(char *out, size_t cap) {
    FILE *f;
    char *env;

    if (!out || cap < 8) return FALSE;
    out[0] = 0;
    env = getenv("AISSTREAM_API_KEY");
    if (env && env[0]) {
        lstrcpynA(out, env, (int)cap);
        return TRUE;
    }
    CreateDirectoryW(L"cache", NULL);
    f = fopen("cache\\ais.key", "r");
    if (!f) return FALSE;
    if (!fgets(out, (int)cap, f)) {
        fclose(f);
        return FALSE;
    }
    fclose(f);
    {
        size_t n = strlen(out);
        while (n > 0 && (out[n - 1] == '\n' || out[n - 1] == '\r' || out[n - 1] == ' '))
            out[--n] = 0;
    }
    return out[0] != 0;
}

BOOL ingest_ais_json_float(const char *json, const char *key, float *out) {
    char pat[64];
    const char *p;
    char *e = NULL;

    if (!json || !key || !out) return FALSE;
    wsprintfA(pat, "\"%s\":", key);
    p = strstr(json, pat);
    if (!p) return FALSE;
    p += strlen(pat);
    while (*p == ' ') p++;
    *out = (float)strtod(p, &e);
    return e != p;
}

BOOL ingest_ais_json_uint(const char *json, const char *key, uint32_t *out) {
    float f;

    if (!out || !ingest_ais_json_float(json, key, &f)) return FALSE;
    if (f < 0.0f) return FALSE;
    *out = (uint32_t)f;
    return TRUE;
}
