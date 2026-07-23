#include "ingest_sole.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

BOOL ingest_json_float(const char *json, const char *key, float *out) {
    char pat[64];
    const char *p;
    char *e = NULL;

    if (!json || !key || !out) return FALSE;
    wsprintfA(pat, "\"%s\":", key);
    p = strstr(json, pat);
    if (!p) return FALSE;
    p += strlen(pat);
    while (*p == ' ') p++;
    if (*p == '"') return FALSE;
    *out = (float)strtod(p, &e);
    return e != p;
}

BOOL ingest_json_last_float(const char *json, const char *key, float *out) {
    char pat[64];
    const char *p = json, *last = NULL;
    char *e = NULL;

    if (!json || !key || !out) return FALSE;
    wsprintfA(pat, "\"%s\":", key);
    while ((p = strstr(p, pat))) {
        last = p;
        p++;
    }
    if (!last) return FALSE;
    p = last + strlen(pat);
    while (*p == ' ') p++;
    *out = (float)strtod(p, &e);
    return e != p;
}

BOOL ingest_json_last_string(const char *json, const char *key, char *out, size_t cap) {
    char pat[64];
    const char *p = json, *last = NULL, *q, *e;
    size_t n;

    if (!json || !key || !out || cap < 2) return FALSE;
    out[0] = 0;
    wsprintfA(pat, "\"%s\":\"", key);
    while ((p = strstr(p, pat))) {
        last = p;
        p++;
    }
    if (!last) return FALSE;
    q = last + strlen(pat);
    e = strchr(q, '"');
    if (!e) return FALSE;
    n = (size_t)(e - q);
    if (n >= cap) n = cap - 1;
    memcpy(out, q, n);
    out[n] = 0;
    return out[0] != 0;
}

BOOL ingest_ace_swepam_last(const char *text, float *density, float *speed_kms) {
    const char *p, *line, *best = NULL;
    float d, s;

    if (!text || !density || !speed_kms) return FALSE;
    for (p = text; *p; p++) {
        if (*p == '\n') {
            const char *nxt = p + 1;
            if (nxt[0] >= '0' && nxt[0] <= '9')
                line = nxt;
            else
                continue;
            if (sscanf(line, "%*d %*d %*d %*d %*d %*d %*d %f %f", &d, &s) == 2 &&
                d > 0.0f && s > 0.0f)
                best = line;
        }
    }
    if (!best) return FALSE;
    if (sscanf(best, "%*d %*d %*d %*d %*d %*d %*d %f %f", density, speed_kms) != 2)
        return FALSE;
    return *density > 0.0f && *speed_kms > 0.0f;
}

BOOL ingest_json_float_array(const char *json, const char *key, float *out, int max_n, int *out_n) {
    char pat[64];
    const char *p, *e;
    int n = 0;

    if (!json || !key || !out || max_n <= 0) return FALSE;
    wsprintfA(pat, "\"%s\":[", key);
    p = strstr(json, pat);
    if (!p) return FALSE;
    p += strlen(pat);
    while (n < max_n) {
        while (*p == ' ' || *p == '\n' || *p == '\r') p++;
        if (*p == ']') break;
        out[n] = (float)strtod(p, (char **)&e);
        if (e == p) break;
        n++;
        p = e;
        while (*p == ' ') p++;
        if (*p == ',') p++;
        else if (*p == ']') break;
    }
    if (out_n) *out_n = n;
    return n > 0;
}
