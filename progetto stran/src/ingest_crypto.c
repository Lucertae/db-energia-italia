#include "ingest_crypto.h"
#include "ingest_curl.h"
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static uint32_t ms_to_ymd_utc(long long ms) {
    FILETIME ft;
    ULARGE_INTEGER u;
    SYSTEMTIME st;

    u.QuadPart = (ULONGLONG)ms * 10000ULL + 116444736000000000ULL;
    ft.dwLowDateTime = u.LowPart;
    ft.dwHighDateTime = u.HighPart;
    FileTimeToSystemTime(&ft, &st);
    return (uint32_t)(st.wYear * 10000u + st.wMonth * 100u + st.wDay);
}

static float json_num_after(const char *json, const char *key) {
    char pat[64];
    const char *p;

    if (!json || !key) return 0.0f;
    wsprintfA(pat, "\"%s\":\"", key);
    p = strstr(json, pat);
    if (!p) {
        wsprintfA(pat, "\"%s\":", key);
        p = strstr(json, pat);
        if (!p) return 0.0f;
        p += strlen(pat);
    } else {
        p += strlen(pat);
    }
    while (*p == ' ') p++;
    return (float)strtod(p, NULL);
}

static float kraken_best_bid(const char *json, const char *pair) {
    char pat[48];
    const char *p, *a;

    wsprintfA(pat, "\"%s\":", pair);
    p = strstr(json, pat);
    if (!p) return 0.0f;
    a = strstr(p, "\"a\":[\"");
    if (!a) return 0.0f;
    return (float)strtod(a + 6, NULL);
}

BOOL ingest_binance_ticker(const char *symbol, CryptoVenueTick *out) {
    wchar_t url[256];
    char body[32768];
    size_t len = 0;
    DWORD st = 0, err = 0;

    if (!symbol || !out) return FALSE;
    memset(out, 0, sizeof(*out));
    wsprintfW(url, L"https://api.binance.com/api/v3/ticker/24hr?symbol=%hs", symbol);
    if (!ingest_curl_get(url, body, sizeof(body), &len, &st, &err) || len < 32)
        return FALSE;
    out->usd = json_num_after(body, "lastPrice");
    out->chg_pct = json_num_after(body, "priceChangePercent");
    out->high_24h = json_num_after(body, "highPrice");
    out->low_24h = json_num_after(body, "lowPrice");
    out->vol_usd = json_num_after(body, "quoteVolume");
    out->ok = out->usd > 0.0f;
    return out->ok;
}

BOOL ingest_kraken_ticker(const char *kraken_pair, CryptoVenueTick *out) {
    wchar_t url[320];
    char body[65536];
    size_t len = 0;
    DWORD st = 0, err = 0;
    float px;

    if (!kraken_pair || !out) return FALSE;
    memset(out, 0, sizeof(*out));
    wsprintfW(url, L"https://api.kraken.com/0/public/Ticker?pair=%hs", kraken_pair);
    if (!ingest_curl_get(url, body, sizeof(body), &len, &st, &err) || len < 32)
        return FALSE;
    px = kraken_best_bid(body, kraken_pair);
    if (px <= 0.0f)
        px = kraken_best_bid(body, "XBTUSD");
    out->usd = px;
    out->ok = px > 0.0f;
    return out->ok;
}

static int parse_kline_close(const char *row, uint32_t *ymd, float *close) {
    const char *p = row;
    int field = 0;
    char tok[32];
    int ti = 0;
    long long ms = 0;

    while (*p && field < 6) {
        if (*p == '[' || *p == ']' || *p == ' ' || *p == ',') {
            if (ti > 0) {
                tok[ti] = 0;
                if (field == 0) ms = _atoi64(tok);
                if (field == 4) *close = (float)atof(tok);
                ti = 0;
                field++;
            }
            p++;
            continue;
        }
        if (*p == '"') { p++; continue; }
        if (ti < (int)sizeof(tok) - 1) tok[ti++] = *p;
        p++;
    }
    if (ms <= 0 || *close <= 0.0f) return 0;
    *ymd = ms_to_ymd_utc(ms);
    return 1;
}

int ingest_binance_klines(const char *symbol, int limit, char *buf, size_t cap) {
    wchar_t url[320];
    char body[262144];
    size_t len = 0, pos = 0;
    DWORD st = 0, err = 0;
    const char *p;
    int n = 0;

    if (!symbol || !buf || cap < 64 || limit <= 0) return 0;
    if (limit > 1000) limit = 1000;
    wsprintfW(url,
        L"https://api.binance.com/api/v3/klines?symbol=%hs&interval=1d&limit=%d",
        symbol, limit);
    if (!ingest_curl_get(url, body, sizeof(body), &len, &st, &err) || len < 16)
        return 0;

    lstrcpynA(buf, "DATE,VALUE\n", (int)cap);
    pos = strlen(buf);
    p = body;
    while (n < limit && (p = strchr(p, '[')) != NULL) {
        const char *end;
        char row[512];
        uint32_t ymd = 0;
        float close = 0.0f;
        int rl;

        if (p[1] == '[') { p++; continue; }
        end = strchr(p, ']');
        if (!end) break;
        rl = (int)(end - p + 1);
        if (rl >= (int)sizeof(row)) rl = (int)sizeof(row) - 1;
        memcpy(row, p, (size_t)rl);
        row[rl] = 0;
        p = end + 1;
        if (!parse_kline_close(row, &ymd, &close)) continue;
        if (pos + 24 < cap) {
            int w = wsprintfA(buf + pos, "%04u-%02u-%02u,%.8f\n",
                ymd / 10000u, (ymd / 100u) % 100u, ymd % 100u, close);
            if (w > 0) { pos += (size_t)w; n++; }
        }
    }
    return n;
}

BOOL ingest_binance_funding(const char *symbol, float *out_pct) {
    wchar_t url[256];
    char body[4096];
    size_t len = 0;
    DWORD st = 0, err = 0;
    float r;

    if (!symbol || !out_pct) return FALSE;
    wsprintfW(url, L"https://fapi.binance.com/fapi/v1/premiumIndex?symbol=%hs", symbol);
    if (!ingest_curl_get(url, body, sizeof(body), &len, &st, &err) || len < 16)
        return FALSE;
    if (!strstr(body, "lastFundingRate")) return FALSE;
    r = json_num_after(body, "lastFundingRate");
    *out_pct = r * 100.0f;
    return TRUE;
}
