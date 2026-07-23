#include "ingest_inet.h"
#include <wininet.h>
#include <string.h>

#pragma comment(lib, "wininet.lib")

BOOL ingest_inet_get(const wchar_t *url, char *buf, size_t cap, size_t *out_len,
                     DWORD *out_status, DWORD *out_err) {
    HINTERNET inet = NULL, req = NULL;
    DWORD read, total = 0, status = 0, status_sz = sizeof(status);
    BOOL ok = FALSE;

    if (out_status) *out_status = 0;
    if (out_err) *out_err = 0;
    if (out_len) *out_len = 0;
    if (!url || !buf || cap < 2) return FALSE;

    inet = InternetOpenW(L"OPSDesk/1.0", INTERNET_OPEN_TYPE_PRECONFIG,
                         NULL, NULL, 0);
    if (!inet) {
        if (out_err) *out_err = GetLastError();
        return FALSE;
    }

    req = InternetOpenUrlW(inet, url, NULL, 0,
                           INTERNET_FLAG_SECURE | INTERNET_FLAG_RELOAD |
                           INTERNET_FLAG_NO_CACHE_WRITE | INTERNET_FLAG_NO_UI, 0);
    if (!req) {
        if (out_err) *out_err = GetLastError();
        goto done;
    }

    if (HttpQueryInfoW(req, HTTP_QUERY_STATUS_CODE | HTTP_QUERY_FLAG_NUMBER,
                       &status, &status_sz, NULL) && out_status)
        *out_status = status;
    if (status != 200) {
        if (out_err) *out_err = status ? status : ERROR_INVALID_PARAMETER;
        goto done;
    }

    for (;;) {
        if (!InternetReadFile(req, buf + total, (DWORD)(cap - 1 - total), &read)) {
            if (total == 0 && out_err) *out_err = GetLastError();
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
    if (req) InternetCloseHandle(req);
    if (inet) InternetCloseHandle(inet);
    return ok;
}
