#ifndef INGEST_INET_H
#define INGEST_INET_H

#include <stddef.h>
#include <windows.h>

BOOL ingest_inet_get(const wchar_t *url, char *buf, size_t cap, size_t *out_len,
                     DWORD *out_status, DWORD *out_err);

#endif
