#include "histdb.h"

static void cache_path(const char *id, wchar_t *out, int cap) {
    wsprintfW(out, L"cache\\%hs.csv", id);
    (void)cap;
}

void histdb_init(void) {
    CreateDirectoryW(L"cache", NULL);
}

BOOL histdb_save(const char *id, const char *body, size_t len) {
    wchar_t path[MAX_PATH];
    HANDLE hf;
    DWORD written = 0;
    BOOL ok;

    if (!id || !body || len == 0) return FALSE;
    cache_path(id, path, MAX_PATH);
    hf = CreateFileW(path, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
                     FILE_ATTRIBUTE_NORMAL, NULL);
    if (hf == INVALID_HANDLE_VALUE) return FALSE;
    ok = WriteFile(hf, body, (DWORD)len, &written, NULL) && written == (DWORD)len;
    CloseHandle(hf);
    return ok;
}

BOOL histdb_load(const char *id, char *buf, size_t cap, size_t *out_len, uint32_t max_age_sec) {
    wchar_t path[MAX_PATH];
    WIN32_FILE_ATTRIBUTE_DATA fa;
    HANDLE hf;
    DWORD read = 0;
    LARGE_INTEGER sz;

    if (out_len) *out_len = 0;
    if (!id || !buf || cap < 2) return FALSE;
    cache_path(id, path, MAX_PATH);

    if (max_age_sec > 0) {
        FILETIME now_ft;
        ULARGE_INTEGER now_u, wt_u;

        if (!GetFileAttributesExW(path, GetFileExInfoStandard, &fa)) return FALSE;
        GetSystemTimeAsFileTime(&now_ft);
        now_u.LowPart = now_ft.dwLowDateTime;
        now_u.HighPart = now_ft.dwHighDateTime;
        wt_u.LowPart = fa.ftLastWriteTime.dwLowDateTime;
        wt_u.HighPart = fa.ftLastWriteTime.dwHighDateTime;
        if (now_u.QuadPart > wt_u.QuadPart &&
            (now_u.QuadPart - wt_u.QuadPart) / 10000000ULL > (ULONGLONG)max_age_sec)
            return FALSE;
    }

    hf = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
                     FILE_ATTRIBUTE_NORMAL, NULL);
    if (hf == INVALID_HANDLE_VALUE) return FALSE;
    if (GetFileSizeEx(hf, &sz) && (size_t)sz.QuadPart >= cap)
        sz.QuadPart = (LONGLONG)cap - 1;
    if (sz.QuadPart <= 0 ||
        !ReadFile(hf, buf, (DWORD)sz.QuadPart, &read, NULL) || read == 0) {
        CloseHandle(hf);
        return FALSE;
    }
    CloseHandle(hf);
    buf[read] = 0;
    if (out_len) *out_len = read;
    return TRUE;
}
