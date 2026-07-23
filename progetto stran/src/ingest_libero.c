#include "ingest_libero.h"
#include "ingest_curl.h"
#include "histdb.h"
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static BOOL cache_needs_refresh(const char *id, uint32_t max_age_sec) {
    wchar_t path[MAX_PATH];
    WIN32_FILE_ATTRIBUTE_DATA fa;
    FILETIME now_ft;
    ULARGE_INTEGER now_u, wt_u;

    wsprintfW(path, L"cache\\%hs.csv", id);
    if (!GetFileAttributesExW(path, GetFileExInfoStandard, &fa))
        return TRUE;
    if (max_age_sec == 0) return FALSE;
    GetSystemTimeAsFileTime(&now_ft);
    now_u.LowPart = now_ft.dwLowDateTime;
    now_u.HighPart = now_ft.dwHighDateTime;
    wt_u.LowPart = fa.ftLastWriteTime.dwLowDateTime;
    wt_u.HighPart = fa.ftLastWriteTime.dwHighDateTime;
    if (now_u.QuadPart <= wt_u.QuadPart) return FALSE;
    return (now_u.QuadPart - wt_u.QuadPart) / 10000000ULL > (ULONGLONG)max_age_sec;
}

BOOL ingest_libero_cache_age(const char *id, uint32_t *age_sec) {
    wchar_t path[MAX_PATH];
    WIN32_FILE_ATTRIBUTE_DATA fa;
    FILETIME now_ft;
    ULARGE_INTEGER now_u, wt_u;

    if (age_sec) *age_sec = 0;
    if (!id) return FALSE;
    wsprintfW(path, L"cache\\%hs.csv", id);
    if (!GetFileAttributesExW(path, GetFileExInfoStandard, &fa)) return FALSE;
    GetSystemTimeAsFileTime(&now_ft);
    now_u.LowPart = now_ft.dwLowDateTime;
    now_u.HighPart = now_ft.dwHighDateTime;
    wt_u.LowPart = fa.ftLastWriteTime.dwLowDateTime;
    wt_u.HighPart = fa.ftLastWriteTime.dwHighDateTime;
    if (age_sec && now_u.QuadPart > wt_u.QuadPart)
        *age_sec = (uint32_t)((now_u.QuadPart - wt_u.QuadPart) / 10000000ULL);
    return TRUE;
}

static BOOL save_csv_body(const char *id, const char *body, size_t len) {
    if (!id || !body || len < 16) return FALSE;
    histdb_init();
    return histdb_save(id, body, len);
}

static uint32_t ts_to_ymd(long ts) {
    FILETIME ft;
    ULARGE_INTEGER u;
    SYSTEMTIME st;

    u.QuadPart = (ULONGLONG)ts * 10000000ULL + 116444736000000000ULL;
    ft.dwLowDateTime = u.LowPart;
    ft.dwHighDateTime = u.HighPart;
    FileTimeToSystemTime(&ft, &st);
    return (uint32_t)(st.wYear * 10000u + st.wMonth * 100u + st.wDay);
}

static const char *json_array_after(const char *json, const char *key) {
    char pat[48];
    const char *p;

    wsprintfA(pat, "\"%s\":[", key);
    p = strstr(json, pat);
    return p ? p + strlen(pat) : NULL;
}

static BOOL yahoo_fetch_csv(const char *symbol, char *out, size_t cap) {
    wchar_t url[512];
    char body[512 * 1024];
    size_t len = 0;
    DWORD st = 0, err = 0;
    const char *ts_a, *cl_a, *tp, *cp;
    size_t pos = 0;
    int n = 0;

    if (!symbol || !out || cap < 64) return FALSE;
    wsprintfW(url,
        L"https://query1.finance.yahoo.com/v8/finance/chart/%hs?interval=1d&range=5y",
        symbol);
    if (!ingest_curl_get(url, body, sizeof(body), &len, &st, &err) || len < 64)
        return FALSE;
    ts_a = json_array_after(body, "timestamp");
    cl_a = json_array_after(body, "close");
    if (!ts_a || !cl_a) return FALSE;

    pos = (size_t)wsprintfA(out, "DATE,VALUE\n");
    tp = ts_a;
    cp = cl_a;
    while (n < 1400 && pos + 32 < cap) {
        long ts = (long)strtol(tp, (char **)&tp, 10);
        double close = strtod(cp, (char **)&cp);
        uint32_t ymd;
        int w;

        while (*tp && (*tp == ',' || *tp == ' ')) tp++;
        while (*cp && (*cp == ',' || *cp == ' ')) cp++;
        if (*tp == ']' || *cp == ']') break;
        if (ts <= 0 || close != close || close <= 0.0) continue;
        ymd = ts_to_ymd(ts);
        w = wsprintfA(out + pos, "%04u-%02u-%02u,%.8f\n",
                      ymd / 10000u, (ymd / 100u) % 100u, ymd % 100u, close);
        if (w > 0) { pos += (size_t)w; n++; }
    }
    return n >= 10;
}

static BOOL blockchain_fetch_csv(const char *chart, char *out, size_t cap) {
    wchar_t url[320];
    char body[1024 * 1024];
    size_t len = 0;
    DWORD st = 0, err = 0;
    const char *p;
    size_t pos = 0;
    int n = 0;

    wsprintfW(url,
        L"https://api.blockchain.info/charts/%hs?timespan=all&format=json&sampled=true&metadata=false",
        chart);
    if (!ingest_curl_get(url, body, sizeof(body), &len, &st, &err) || len < 32)
        return FALSE;
    p = strstr(body, "\"values\":");
    if (!p) return FALSE;
    pos = (size_t)wsprintfA(out, "DATE,VALUE\n");
    p = strchr(p, '[');
    if (!p) return FALSE;
    p++;
    while (n < 1400 && pos + 40 < cap && *p && *p != ']') {
        const char *x = strstr(p, "\"x\":");
        const char *y = strstr(p, "\"y\":");
        long ts;
        double val;
        uint32_t ymd;
        int w;

        if (!x || !y) break;
        ts = strtol(x + 4, NULL, 10);
        val = strtod(y + 4, NULL);
        p = y + 4;
        if (ts <= 0 || val != val) continue;
        ymd = ts_to_ymd(ts);
        w = wsprintfA(out + pos, "%04u-%02u-%02u,%.8f\n",
                      ymd / 10000u, (ymd / 100u) % 100u, ymd % 100u, val);
        if (w > 0) { pos += (size_t)w; n++; }
        p = strchr(p, '}');
        if (!p) break;
        p++;
    }
    return n >= 10;
}

static BOOL cpu_fetch_csv(char *out, size_t cap) {
    wchar_t url[] = L"https://www.policyuncertainty.com/media/cpu_base_pos_neg_all_countries_monthly.csv";
    char body[512 * 1024];
    size_t len = 0;
    DWORD st = 0, err = 0;
    const char *p, *end;
    size_t pos = 0;
    int n = 0;

    if (!ingest_curl_get(url, body, sizeof(body), &len, &st, &err) || len < 64)
        return FALSE;
    p = body;
    while (*p && strncmp(p, "cit,", 4) != 0) {
        p = strchr(p, '\n');
        if (!p) return FALSE;
        p++;
    }
    p = strchr(p, '\n');
    if (!p) return FALSE;
    p++;
    pos = (size_t)wsprintfA(out, "DATE,VALUE\n");
    end = body + len;
    while (p < end && n < 120 && pos + 32 < cap) {
        char line[256];
        const char *le;
        int y, m, w;
        float v;
        char *e;

        le = strchr(p, '\n');
        if (!le) le = end;
        if ((size_t)(le - p) >= sizeof(line)) { p = le + 1; continue; }
        memcpy(line, p, (size_t)(le - p));
        line[le - p] = 0;
        e = strstr(line, "CPU_US");
        if (!e) { p = le + 1; continue; }
        if (sscanf(line, "%*[^,],%d,%d", &y, &m) < 2) { p = le + 1; continue; }
        e = strrchr(line, ',');
        if (!e) { p = le + 1; continue; }
        v = (float)strtod(e + 1, NULL);
        if (v != v || y < 1990) { p = le + 1; continue; }
        w = wsprintfA(out + pos, "%04d-%02d-28,%.6f\n", y, m, v);
        if (w > 0) { pos += (size_t)w; n++; }
        p = le + 1;
    }
    return n >= 10;
}

static BOOL spawn_python_libero(void) {
    wchar_t cmd[640];
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    DWORD exit_code = 1;

    wsprintfW(cmd,
        L"cmd.exe /c python \"scripts\\libero\\fetch_all.py\" all");
    memset(&si, 0, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    memset(&pi, 0, sizeof(pi));
    if (!CreateProcessW(NULL, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi))
        return FALSE;
    WaitForSingleObject(pi.hProcess, 600000);
    GetExitCodeProcess(pi.hProcess, &exit_code);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return exit_code == 0;
}

static int refresh_yahoo_pair(const char *sym, const char *id, uint32_t max_age, char *buf, size_t cap) {
    if (!cache_needs_refresh(id, max_age)) return 0;
    if (!yahoo_fetch_csv(sym, buf, cap)) return 0;
    return save_csv_body(id, buf, strlen(buf)) ? 1 : 0;
}

static int refresh_blockchain(const char *chart, const char *id, uint32_t max_age, char *buf, size_t cap) {
    if (!cache_needs_refresh(id, max_age)) return 0;
    if (!blockchain_fetch_csv(chart, buf, cap)) return 0;
    return save_csv_body(id, buf, strlen(buf)) ? 1 : 0;
}

int ingest_libero_cvi_from_btc(void) {
    wchar_t path[MAX_PATH];
    FILE *f;
    static char line[128];
    static float px[512];
    static uint32_t ymd[512];
    static char out[65536];
    int n = 0, i, w, pos;
    double sum = 0.0, sum2 = 0.0;
    int win = 30;

    wsprintfW(path, L"cache\\crypto\\BTC.csv");
    f = _wfopen(path, L"r");
    if (!f) {
        wsprintfW(path, L"cache\\BTC.csv");
        f = _wfopen(path, L"r");
    }
    if (!f) return 0;
    while (fgets(line, sizeof(line), f) && n < 512) {
        int y, mo, d;
        float v;
        if (line[0] == 'D') continue;
        if (sscanf(line, "%d-%d-%d,%f", &y, &mo, &d, &v) < 4) continue;
        if (v <= 0.0f) continue;
        ymd[n] = (uint32_t)(y * 10000 + mo * 100 + d);
        px[n] = v;
        n++;
    }
    fclose(f);
    if (n < win + 5) return 0;

    pos = wsprintfA(out, "DATE,VALUE\n");
    for (i = win; i < n; i++) {
        int j;
        double mean = 0.0, var = 0.0, rv;
        float lr;

        lr = (float)log((double)px[i] / (double)px[i - 1]);
        for (j = i - win + 1; j <= i; j++) {
            double r = log((double)px[j] / (double)px[j - 1]);
            mean += r;
        }
        mean /= win;
        for (j = i - win + 1; j <= i; j++) {
            double r = log((double)px[j] / (double)px[j - 1]);
            double d = r - mean;
            var += d * d;
        }
        var /= (win - 1);
        rv = sqrt(var) * sqrt(365.0) * 100.0;
        w = wsprintfA(out + pos, "%04u-%02u-%02u,%.6f\n",
                      ymd[i] / 10000u, (ymd[i] / 100u) % 100u, ymd[i] % 100u, rv);
        if (w > 0) pos += w;
    }
  (void)sum; (void)sum2;
    return save_csv_body("CVI", out, (size_t)pos) ? 1 : 0;
}

int ingest_libero_refresh(uint32_t max_age_sec) {
    static char buf[1024 * 1024];
    int ok = 0;

    histdb_init();
    ok += refresh_yahoo_pair("ICLN", "GRN", max_age_sec, buf, sizeof(buf));
    ok += refresh_yahoo_pair("XLE", "DIR", max_age_sec, buf, sizeof(buf));
    ok += refresh_yahoo_pair("KRBN", "EUA", max_age_sec, buf, sizeof(buf));
    ok += refresh_yahoo_pair("NG%%3DF", "NGF", max_age_sec, buf, sizeof(buf));
    ok += refresh_blockchain("hash-rate", "HAS", max_age_sec, buf, sizeof(buf));
    ok += refresh_blockchain("transaction-fees", "FEE", max_age_sec, buf, sizeof(buf));
    ok += refresh_blockchain("difficulty", "DIF", max_age_sec, buf, sizeof(buf));
    ok += refresh_blockchain("miners-revenue", "REV", max_age_sec, buf, sizeof(buf));

    if (cache_needs_refresh("CPU", max_age_sec) && cpu_fetch_csv(buf, sizeof(buf)))
        ok += save_csv_body("CPU", buf, strlen(buf)) ? 1 : 0;

    if (cache_needs_refresh("GPR", max_age_sec) || cache_needs_refresh("CBE", max_age_sec) ||
        cache_needs_refresh("EMI", max_age_sec) || cache_needs_refresh("BVL", max_age_sec) ||
        cache_needs_refresh("MCP", max_age_sec)) {
        if (spawn_python_libero())
            ok++;
    }

    if (cache_needs_refresh("CVI", max_age_sec) || cache_needs_refresh("BTC", max_age_sec))
        ok += ingest_libero_cvi_from_btc();

    return ok;
}
