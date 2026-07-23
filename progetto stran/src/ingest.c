#include "ingest.h"
#include "ingest_inet.h"
#include "ingest_curl.h"
#include <winhttp.h>
#include <stdlib.h>
#include <string.h>

#pragma comment(lib, "winhttp.lib")

struct IngestSession {
    HINTERNET ses;
};

static DWORD g_last_http_err;
static DWORD g_last_http_status;

DWORD ingest_last_error(void) {
    return g_last_http_err;
}

DWORD ingest_last_status(void) {
    return g_last_http_status;
}

static void session_config(HINTERNET ses) {
    DWORD timeout = 15000;
    DWORD protocols = WINHTTP_FLAG_SECURE_PROTOCOL_TLS1_2;
    DWORD ipv6_fb = 1;

#ifdef WINHTTP_FLAG_SECURE_PROTOCOL_TLS1_3
    protocols |= WINHTTP_FLAG_SECURE_PROTOCOL_TLS1_3;
#endif

    WinHttpSetOption(ses, WINHTTP_OPTION_SECURE_PROTOCOLS, &protocols, sizeof(protocols));
    WinHttpSetOption(ses, WINHTTP_OPTION_CONNECT_TIMEOUT, &timeout, sizeof(timeout));
    WinHttpSetOption(ses, WINHTTP_OPTION_SEND_TIMEOUT, &timeout, sizeof(timeout));
    WinHttpSetOption(ses, WINHTTP_OPTION_RECEIVE_TIMEOUT, &timeout, sizeof(timeout));
    WinHttpSetOption(ses, WINHTTP_OPTION_IPV6_FAST_FALLBACK, &ipv6_fb, sizeof(ipv6_fb));
}

IngestSession *ingest_session_open(void) {
    IngestSession *s;
    DWORD access[] = {
        WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY,
        WINHTTP_ACCESS_TYPE_NO_PROXY,
        WINHTTP_ACCESS_TYPE_DEFAULT_PROXY
    };
    int i;

    s = (IngestSession *)malloc(sizeof(*s));
    if (!s) return NULL;
    s->ses = NULL;
    for (i = 0; i < 3; i++) {
        s->ses = WinHttpOpen(L"OPSDesk/1.0", access[i],
                             WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
        if (s->ses) break;
    }
    if (!s->ses) {
        free(s);
        return NULL;
    }
    session_config(s->ses);
    return s;
}

void ingest_session_close(IngestSession *s) {
    if (!s) return;
    if (s->ses) WinHttpCloseHandle(s->ses);
    free(s);
}

static BOOL http_get_ex(HINTERNET ses, const wchar_t *url, char *buf, size_t cap, size_t *out_len) {
    URL_COMPONENTS uc;
    wchar_t host[256], path[512], extra[512], req_path[1024];
    HINTERNET con = NULL, req = NULL;
    INTERNET_PORT port;
    DWORD flags, read, total = 0, status = 0, status_sz;
    BOOL ok = FALSE;

    g_last_http_err = 0;
    g_last_http_status = 0;
    if (out_len) *out_len = 0;
    if (!ses || !url || !buf || cap < 2) return FALSE;

    memset(&uc, 0, sizeof(uc));
    uc.dwStructSize = sizeof(uc);
    uc.lpszHostName = host;
    uc.dwHostNameLength = (DWORD)(sizeof(host) / sizeof(wchar_t));
    uc.lpszUrlPath = path;
    uc.dwUrlPathLength = (DWORD)(sizeof(path) / sizeof(wchar_t));
    uc.lpszExtraInfo = extra;
    uc.dwExtraInfoLength = (DWORD)(sizeof(extra) / sizeof(wchar_t));

    if (!WinHttpCrackUrl(url, 0, 0, &uc)) {
        g_last_http_err = GetLastError();
        return FALSE;
    }

    if (extra[0])
        wsprintfW(req_path, L"%s%s", path, extra);
    else
        lstrcpyW(req_path, path);

    port = uc.nPort;
    if (!port)
        port = (uc.nScheme == INTERNET_SCHEME_HTTPS) ? 443 : 80;

    con = WinHttpConnect(ses, host, port, 0);
    if (!con) {
        g_last_http_err = GetLastError();
        goto done;
    }

    flags = (uc.nScheme == INTERNET_SCHEME_HTTPS) ? WINHTTP_FLAG_SECURE : 0;
    req = WinHttpOpenRequest(con, L"GET", req_path, NULL, WINHTTP_NO_REFERER,
                             WINHTTP_DEFAULT_ACCEPT_TYPES, flags);
    if (!req) {
        g_last_http_err = GetLastError();
        goto done;
    }

    if (!WinHttpSendRequest(req, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                            WINHTTP_NO_REQUEST_DATA, 0, 0, 0)) {
        g_last_http_err = GetLastError();
        goto done;
    }
    if (!WinHttpReceiveResponse(req, NULL)) {
        g_last_http_err = GetLastError();
        goto done;
    }

    status_sz = sizeof(status);
    if (WinHttpQueryHeaders(req,
            WINHTTP_QUERY_STATUS_CODE | WINHTTP_QUERY_FLAG_NUMBER,
            WINHTTP_HEADER_NAME_BY_INDEX, &status, &status_sz, WINHTTP_NO_HEADER_INDEX))
        g_last_http_status = status;
    if (status != 200) {
        g_last_http_err = status;
        goto done;
    }

    for (;;) {
        if (!WinHttpReadData(req, buf + total, (DWORD)(cap - 1 - total), &read)) {
            if (total == 0) g_last_http_err = GetLastError();
            break;
        }
        if (read == 0) break;
        total += read;
        if (total >= cap - 1) break;
    }

    buf[total] = 0;
    if (out_len) *out_len = total;
    ok = total > 0;

done:
    if (req) WinHttpCloseHandle(req);
    if (con) WinHttpCloseHandle(con);
    return ok;
}

static BOOL host_prefers_curl(const wchar_t *url) {
    return url && wcsstr(url, L"stlouisfed.org") != NULL;
}

BOOL ingest_http_get(const wchar_t *url, char *buf, size_t cap, size_t *out_len) {
    IngestSession *s = ingest_session_open();
    BOOL ok;

    if (!s) return FALSE;
    ok = ingest_session_get(s, url, buf, cap, out_len);
    ingest_session_close(s);
    return ok;
}

BOOL ingest_session_get(IngestSession *s, const wchar_t *url, char *buf, size_t cap, size_t *out_len) {
    if (!s) return FALSE;
    if (host_prefers_curl(url)) {
        if (ingest_curl_get(url, buf, cap, out_len, &g_last_http_status, &g_last_http_err))
            return TRUE;
        return ingest_inet_get(url, buf, cap, out_len, &g_last_http_status, &g_last_http_err);
    }
    if (http_get_ex(s->ses, url, buf, cap, out_len))
        return TRUE;
    if (ingest_curl_get(url, buf, cap, out_len, &g_last_http_status, &g_last_http_err))
        return TRUE;
    return ingest_inet_get(url, buf, cap, out_len, &g_last_http_status, &g_last_http_err);
}

static const char *find_attr(const char *p, const char *key, char *out, int out_sz) {
    char pat[32];
    const char *q, *r;
    char quote;
    int n;

    wsprintfA(pat, "%s=", key);
    q = strstr(p, pat);
    if (!q) return NULL;
    q += lstrlenA(pat);
    quote = *q;
    if (quote != '\'' && quote != '"') return NULL;
    q++;
    r = strchr(q, quote);
    if (!r) return NULL;
    n = (int)(r - q);
    if (n >= out_sz) n = out_sz - 1;
    memcpy(out, q, (size_t)n);
    out[n] = 0;
    return out;
}

int ingest_ecb_fx(const char *xml, size_t len, IngestFxFn fn, void *ctx) {
    const char *p, *end;
    char iso[8], rate_s[32];
    int n = 0;

    if (!xml || !fn) return 0;
    end = xml + len;
    p = xml;
    while (p < end) {
        p = strstr(p, "currency=");
        if (!p || p >= end) break;
        if (!find_attr(p, "currency", iso, sizeof(iso))) { p++; continue; }
        if (!find_attr(p, "rate", rate_s, sizeof(rate_s))) { p++; continue; }
        if (lstrlenA(iso) == 3) {
            fn(iso, atof(rate_s), ctx);
            n++;
        }
        p++;
    }
    return n;
}

BOOL ingest_fred_last(const char *csv, size_t len, double *out) {
    const char *p, *end, *line_end, *comma;
    double v = 0.0;
    int got = 0;

    if (!csv) return FALSE;
    end = csv + len;
    p = csv;
    while (p < end) {
        line_end = p;
        while (line_end < end && *line_end != '\n' && *line_end != '\r') line_end++;
        comma = line_end - 1;
        while (comma > p && *comma != ',') comma--;
        if (comma > p && comma < line_end - 1) {
            comma++;
            if ((*comma >= '0' && *comma <= '9') || *comma == '-' ||
                (*comma == '.' && comma[1] >= '0' && comma[1] <= '9')) {
                v = atof(comma);
                if (v > 0.0) got = 1;
            }
        }
        p = line_end;
        while (p < end && (*p == '\n' || *p == '\r')) p++;
    }
    if (got && out) *out = v;
    return got;
}

static void fred_range_suffix(wchar_t *suffix, int days) {
    SYSTEMTIME end, start;
    FILETIME ft;
    ULARGE_INTEGER u;

    GetSystemTime(&end);
    SystemTimeToFileTime(&end, &ft);
    u.LowPart = ft.dwLowDateTime;
    u.HighPart = ft.dwHighDateTime;
    u.QuadPart -= (ULONGLONG)days * 24ULL * 3600ULL * 10000000ULL;
    ft.dwLowDateTime = u.LowPart;
    ft.dwHighDateTime = u.HighPart;
    FileTimeToSystemTime(&ft, &start);
    wsprintfW(suffix, L"&cosd=%04u-%02u-%02u&coed=%04u-%02u-%02u",
              start.wYear, start.wMonth, start.wDay,
              end.wYear, end.wMonth, end.wDay);
}

static uint32_t parse_ymd(const char *p) {
    int y, m, d;

    if (!p || lstrlenA(p) < 10) return 0;
    y = (p[0] - '0') * 1000 + (p[1] - '0') * 100 +
        (p[2] - '0') * 10 + (p[3] - '0');
    m = (p[5] - '0') * 10 + (p[6] - '0');
    d = (p[8] - '0') * 10 + (p[9] - '0');
    if (y < 1900 || y > 2200 || m < 1 || m > 12 || d < 1 || d > 31) return 0;
    return (uint32_t)(y * 10000 + m * 100 + d);
}

int ingest_fred_hist(const char *csv, size_t len, uint32_t *ymd, float *val, int max_n) {
    const char *p, *end, *line_end, *comma;
    int n = 0;
    uint32_t d;
    double v;

    if (!csv || !ymd || !val || max_n <= 0) return 0;
    end = csv + len;
    p = csv;
    while (p < end) {
        while (p < end && (*p == '\n' || *p == '\r')) p++;
        if (p >= end) break;
        line_end = p;
        while (line_end < end && *line_end != '\n' && *line_end != '\r') line_end++;
        if (strncmp(p, "observation", 11) == 0 || strncmp(p, "DATE", 4) == 0) {
            p = line_end;
            continue;
        }
        comma = p;
        while (comma < line_end && *comma != ',') comma++;
        if (comma >= line_end) {
            p = line_end;
            continue;
        }
        d = parse_ymd(p);
        comma++;
        if (!d ||
            !((*comma >= '0' && *comma <= '9') || *comma == '-' ||
              (*comma == '.' && comma[1] >= '0' && comma[1] <= '9'))) {
            p = line_end;
            continue;
        }
        v = atof(comma);
        if (v == 0.0 && *comma != '0') {
            p = line_end;
            continue;
        }
        if (n == max_n) {
            /* keep the tail: drop oldest eighth, keep parsing to EOF */
            int keep = max_n - max_n / 8;
            memmove(ymd, ymd + (n - keep), (size_t)keep * sizeof(ymd[0]));
            memmove(val, val + (n - keep), (size_t)keep * sizeof(val[0]));
            n = keep;
        }
        ymd[n] = d;
        val[n] = (float)v;
        n++;
        p = line_end;
    }
    return n;
}

void ingest_fred_url(const char *series_id, int days, wchar_t *url, int cap) {
    wchar_t range[64];

    if (!series_id || !url || cap < 64) return;
    fred_range_suffix(range, days);
    wsprintfW(url, L"https://fred.stlouisfed.org/graph/fredgraph.csv?id=%hs%s",
              series_id, range);
}

BOOL ingest_fred_fetch_ex(IngestSession *s, const char *series_id,
                          char *buf, size_t cap, double *out) {
    wchar_t url[320];
    size_t len = 0;

    if (!series_id || !buf || !out) return FALSE;
    ingest_fred_url(series_id, 120, url, (int)(sizeof(url) / sizeof(url[0])));
    if (!ingest_session_get(s, url, buf, cap, &len)) return FALSE;
    return ingest_fred_last(buf, len, out);
}

int ingest_fred_fetch_hist_ex(IngestSession *s, const char *series_id, char *buf, size_t cap,
                              uint32_t *ymd, float *val, int max_n, float *out_live, int days) {
    wchar_t url[320];
    size_t len = 0;
    int n;
    double last = 0.0;

    if (!series_id || !buf || !ymd || !val || max_n <= 0) return 0;
    ingest_fred_url(series_id, days > 0 ? days : 365, url, (int)(sizeof(url) / sizeof(url[0])));
    if (!ingest_session_get(s, url, buf, cap, &len)) return 0;
    n = ingest_fred_hist(buf, len, ymd, val, max_n);
    if (n > 0 && ingest_fred_last(buf, len, &last) && out_live)
        *out_live = (float)last;
    return n;
}

BOOL ingest_fred_fetch(const char *series_id, char *buf, size_t cap, double *out) {
    IngestSession *s = ingest_session_open();
    BOOL ok;

    if (!s) return FALSE;
    ok = ingest_fred_fetch_ex(s, series_id, buf, cap, out);
    ingest_session_close(s);
    return ok;
}
