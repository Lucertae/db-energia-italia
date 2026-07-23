#include "ingest_curl.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static BOOL read_file_all(const wchar_t *path, char *buf, size_t cap, size_t *out_len) {
    HANDLE hf;
    DWORD read, total = 0;
    LARGE_INTEGER sz;

    if (out_len) *out_len = 0;
    hf = CreateFileW(path, GENERIC_READ, FILE_SHARE_READ, NULL, OPEN_EXISTING,
                     FILE_ATTRIBUTE_NORMAL, NULL);
    if (hf == INVALID_HANDLE_VALUE) return FALSE;

    if (GetFileSizeEx(hf, &sz) && (size_t)sz.QuadPart >= cap)
        sz.QuadPart = (LONGLONG)cap - 1;

    if (sz.QuadPart > 0) {
        if (!ReadFile(hf, buf, (DWORD)sz.QuadPart, &read, NULL) || read == 0) {
            CloseHandle(hf);
            return FALSE;
        }
        total = read;
    }
    CloseHandle(hf);
    buf[total] = 0;
    if (out_len) *out_len = total;
    return total > 0;
}

BOOL ingest_curl_get(const wchar_t *url, char *buf, size_t cap, size_t *out_len,
                     DWORD *out_status, DWORD *out_err) {
    wchar_t tmp_dir[MAX_PATH], tmp_file[MAX_PATH], cmd[4096];
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    DWORD exit_code = 1, wait;
    BOOL ok = FALSE;

    if (out_status) *out_status = 0;
    if (out_err) *out_err = 0;
    if (out_len) *out_len = 0;
    if (!url || !buf || cap < 2) return FALSE;

    if (!GetTempPathW(MAX_PATH, tmp_dir)) return FALSE;
    if (!GetTempFileNameW(tmp_dir, L"ops", 0, tmp_file)) return FALSE;
    DeleteFileW(tmp_file);

    wsprintfW(cmd,
              L"curl.exe -sS -L --max-time 45 -o \"%s\" -w \"%%{http_code}\" \"%s\"",
              tmp_file, url);

    memset(&si, 0, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    memset(&pi, 0, sizeof(pi));

    if (!CreateProcessW(NULL, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW,
                        NULL, NULL, &si, &pi)) {
        if (out_err) *out_err = GetLastError();
        return FALSE;
    }

    wait = WaitForSingleObject(pi.hProcess, 50000);
    if (wait != WAIT_OBJECT_0) {
        TerminateProcess(pi.hProcess, 1);
        if (out_err) *out_err = ERROR_TIMEOUT;
        CloseHandle(pi.hThread);
        CloseHandle(pi.hProcess);
        DeleteFileW(tmp_file);
        return FALSE;
    }

    GetExitCodeProcess(pi.hProcess, &exit_code);
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);

    if (exit_code != 0) {
        if (out_err) *out_err = (DWORD)exit_code;
        DeleteFileW(tmp_file);
        return FALSE;
    }

    ok = read_file_all(tmp_file, buf, cap, out_len);
    DeleteFileW(tmp_file);
    if (ok && out_status) *out_status = 200;
    if (!ok && out_err && !*out_err) *out_err = ERROR_READ_FAULT;
    return ok;
}
