#include "ingest_entsoe.h"
#include "ingest_curl.h"
#include "histdb.h"
#include "ingest.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    const char *desk_id;
    const char *eic;
} EntsoeZone;

static const EntsoeZone g_zones[] = {
    { "PDE", "10Y1001A1001A82H" },
    { "PFR", "10YFR-RTE------C" },
    { "PIT", "10Y1001A1001A73I" },
    { "PNL", "10YNL----------L" },
    { "PPL", "10YPL-AREA-----S" },
};

static char g_entsoe_key[128];
static int  g_entsoe_loaded;

static void entsoe_load_key(void) {
    FILE *f;

    if (g_entsoe_loaded) return;
    g_entsoe_loaded = 1;
    g_entsoe_key[0] = 0;
    if (GetEnvironmentVariableA("ENTSOE_API_TOKEN", g_entsoe_key, (DWORD)sizeof(g_entsoe_key)) > 0)
        return;
    if (GetEnvironmentVariableA("HEDGE_ENTSOE_TOKEN", g_entsoe_key, (DWORD)sizeof(g_entsoe_key)) > 0)
        return;
    f = fopen("cache\\entsoe.key", "r");
    if (!f) return;
    if (fgets(g_entsoe_key, (int)sizeof(g_entsoe_key), f)) {
        int n = (int)strlen(g_entsoe_key);
        while (n > 0 && (g_entsoe_key[n - 1] == '\n' || g_entsoe_key[n - 1] == '\r'))
            g_entsoe_key[--n] = 0;
    }
    fclose(f);
}

BOOL ingest_entsoe_have_key(void) {
    entsoe_load_key();
    return g_entsoe_key[0] != 0;
}

static void period_utc(int hours_back, int hours_fwd, char *start, char *end) {
    FILETIME ft;
    ULARGE_INTEGER u;
    SYSTEMTIME st;
    uint64_t t;

    GetSystemTimeAsFileTime(&ft);
    u.LowPart = ft.dwLowDateTime;
    u.HighPart = ft.dwHighDateTime;
    t = u.QuadPart - (uint64_t)hours_back * 36000000000ULL;
    ft.dwLowDateTime = (DWORD)t;
    ft.dwHighDateTime = (DWORD)(t >> 32);
    FileTimeToSystemTime(&ft, &st);
    wsprintfA(start, "%04u%02u%02u%02u%02u",
        st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute);

    t = u.QuadPart + (uint64_t)hours_fwd * 36000000000ULL;
    ft.dwLowDateTime = (DWORD)t;
    ft.dwHighDateTime = (DWORD)(t >> 32);
    FileTimeToSystemTime(&ft, &st);
    wsprintfA(end, "%04u%02u%02u%02u%02u",
        st.wYear, st.wMonth, st.wDay, st.wHour, st.wMinute);
}

static int parse_prices(const char *xml, float *out, int max_n) {
    const char *p = xml;
    int n = 0;

    while (n < max_n && (p = strstr(p, "<price.amount>")) != NULL) {
        p += 14;
        out[n++] = (float)strtod(p, NULL);
    }
    return n;
}

static float price_mean(const float *v, int n) {
    int i;
    double s = 0.0;

    if (n <= 0) return 0.0f;
    for (i = 0; i < n; i++) s += v[i];
    return (float)(s / (double)n);
}

static void today_ymd(char *out, int cap) {
    SYSTEMTIME st;

    GetSystemTime(&st);
    wsprintfA(out, "%04u-%02u-%02u", st.wYear, st.wMonth, st.wDay);
}

static BOOL merge_daily_csv(const char *desk_id, float avg_eur_mwh) {
    static char body[INGEST_BODY_MAX];
    char day[16], newline[48], *p, *line;
    size_t len, nlen;
    int found = 0;

    if (avg_eur_mwh <= 0.0f) return FALSE;
    histdb_init();
    today_ymd(day, (int)sizeof(day));
    wsprintfA(newline, "%s,%.4f\n", day, avg_eur_mwh);
    nlen = strlen(newline);

    if (!histdb_load(desk_id, body, sizeof(body), &len, 0)) {
        wsprintfA(body, "DATE,%s\n%s", desk_id, newline);
        return histdb_save(desk_id, body, strlen(body));
    }

    p = body;
    while (*p) {
        line = p;
        while (*p && *p != '\n' && *p != '\r') p++;
        if ((size_t)(p - line) >= 10 && strncmp(line, day, 10) == 0 && line[10] == ',') {
            size_t tail = strlen(p);
            memmove(line + nlen, p, tail + 1);
            memcpy(line, newline, nlen);
            found = 1;
            break;
        }
        if (*p) p++;
        while (*p == '\r' || *p == '\n') p++;
    }

    if (!found) {
        if (len + nlen + 1 >= sizeof(body)) {
            char *nl = strchr(body, '\n');
            if (nl) {
                char *nl2 = strchr(nl + 1, '\n');
                if (nl2)
                    memmove(nl + 1, nl2 + 1, strlen(nl2 + 1) + 1);
            }
        }
        lstrcatA(body, newline);
    }
    return histdb_save(desk_id, body, strlen(body));
}

static BOOL fetch_zone(IngestSession *sess, const EntsoeZone *z, float *avg_out) {
    wchar_t url[1024];
    char body[262144];
    char ps[16], pe[16];
    float prices[192];
    size_t len = 0;
    DWORD st = 0, err = 0;
    int n;

    period_utc(72, 24, ps, pe);
    wsprintfW(url,
        L"https://web-api.tp.entsoe.eu/api?"
        L"securityToken=%hs&documentType=A44"
        L"&in_Domain=%hs&out_Domain=%hs"
        L"&periodStart=%hs&periodEnd=%hs",
        g_entsoe_key, z->eic, z->eic, ps, pe);

    if (!ingest_session_get(sess, url, body, sizeof(body), &len) || len < 64)
        return FALSE;
    if (strstr(body, "No matching data") || strstr(body, "Acknowledgement_MarketDocument"))
        return FALSE;
    n = parse_prices(body, prices, (int)(sizeof(prices) / sizeof(prices[0])));
    if (n <= 0) return FALSE;
    *avg_out = price_mean(prices, n);
    return merge_daily_csv(z->desk_id, *avg_out);
}

int ingest_entsoe_refresh(IngestSession *sess) {
    int i, ok = 0;
    float avg;

    if (!sess) return 0;
    entsoe_load_key();
    if (!g_entsoe_key[0]) return 0;

    for (i = 0; i < (int)(sizeof(g_zones) / sizeof(g_zones[0])); i++) {
        if (fetch_zone(sess, &g_zones[i], &avg))
            ok++;
    }
    return ok;
}
