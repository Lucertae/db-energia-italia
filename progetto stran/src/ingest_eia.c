#include "ingest_eia.h"
#include "ingest_curl.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char g_eia_key[64];
static int  g_eia_key_loaded = 0;

static void eia_load_key(void) {
    FILE *f;

    if (g_eia_key_loaded) return;
    g_eia_key_loaded = 1;
    g_eia_key[0] = 0;
    if (GetEnvironmentVariableA("EIA_API_KEY", g_eia_key, (DWORD)sizeof(g_eia_key)) > 0)
        return;
    f = fopen("cache\\eia.key", "r");
    if (!f) return;
    if (fgets(g_eia_key, (int)sizeof(g_eia_key), f)) {
        int n = (int)strlen(g_eia_key);
        while (n > 0 && (g_eia_key[n - 1] == '\n' || g_eia_key[n - 1] == '\r'))
            g_eia_key[--n] = 0;
    }
    fclose(f);
}

BOOL ingest_eia_have_key(void) {
    eia_load_key();
    return g_eia_key[0] != 0;
}

static float eia_json_last_float(const char *json, const char *key) {
    char pat[48], *p, *e;
    float v;

    wsprintfA(pat, "\"%s\":", key);
    p = strstr(json, pat);
    if (!p) return 0.0f;
    p += strlen(pat);
    while (*p == ' ') p++;
    v = (float)strtod(p, &e);
    return v;
}

BOOL ingest_eia_country_primary(const char *country_iso2, float *out_mtoe, uint16_t *out_year) {
    wchar_t url[1024];
    char body[65536];
    size_t len = 0;
    DWORD st = 0, err = 0;
    float v;
    int y;

    if (!country_iso2 || !out_mtoe) return FALSE;
    eia_load_key();
    if (!g_eia_key[0]) return FALSE;

    wsprintfW(url,
        L"https://api.eia.gov/v2/international/data/?"
        L"api_key=%hs&frequency=annual&data[0]=value"
        L"&facets[countryRegionId][]=%hs&facets[activityId][]=2"
        L"&facets[productId][]=2&facets[unit][]=Q&sort[0][column]=period"
        L"&sort[0][direction]=desc&length=1",
        g_eia_key, country_iso2);

    if (!ingest_curl_get(url, body, sizeof(body), &len, &st, &err) || len < 32)
        return FALSE;
    v = eia_json_last_float(body, "value");
    if (v <= 0.0f) return FALSE;
  {
        char *pp = strstr(body, "\"period\":");
        y = 0;
        if (pp) y = atoi(pp + 9);
    }
    *out_mtoe = v / 1000.0f;
    if (out_year) *out_year = (uint16_t)y;
    return TRUE;
}
