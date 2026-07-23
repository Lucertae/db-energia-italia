#include "ingest_intel.h"
#include "chokepoints.h"
#include "intel.h"
#include "common.h"
#include <stdio.h>
#include <string.h>

static BOOL file_age_sec(const wchar_t *path, uint32_t *age_sec) {
    WIN32_FILE_ATTRIBUTE_DATA fa;
    FILETIME now_ft;
    ULARGE_INTEGER now_u, wt_u;

    if (age_sec) *age_sec = 0;
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

static BOOL cache_stale(const wchar_t *path, uint32_t max_age_sec) {
    uint32_t age = 0;

    if (max_age_sec == 0) return FALSE;
    if (!file_age_sec(path, &age)) return TRUE;
    return age > max_age_sec;
}

int ingest_intel_refresh(uint32_t max_age_portwatch, uint32_t max_age_headlines) {
    int ok = 0;
    int spawned = 0;

    CreateDirectoryW(L"cache", NULL);
    CreateDirectoryW(L"cache\\portwatch", NULL);
    CreateDirectoryW(L"cache\\intel", NULL);

    if (cache_stale(L"cache\\portwatch\\chokepoints.csv", max_age_portwatch))
        if (desk_spawn_python(L"scripts\\desk_harvest\\harvest_portwatch.py"))
            ok++;

    if (cache_stale(L"cache\\intel\\headlines.csv", max_age_headlines)) {
        if (desk_spawn_python(L"scripts\\desk_harvest\\harvest_intel.py")) {
            ok++;
            spawned = 1;
        }
    } else if (cache_stale(L"cache\\intel\\desk_index.json", max_age_headlines)) {
        if (desk_spawn_python(L"scripts\\desk_harvest\\build_intel_index.py"))
            ok++;
    }

    if (chokepoints_reload() > 0) ok++;
    if (intel_reload_headlines() > 0) ok++;
    /* Se harvest in background, il reload da indice avviene via intel_desk_poll */
    if (!spawned)
        if (intel_desk_reload() > 0) ok++;

    if (cache_stale(L"cache\\NGS.csv", max_age_portwatch) ||
        cache_stale(L"cache\\CRU.csv", max_age_portwatch)) {
        if (desk_spawn_python(L"scripts\\desk_harvest\\eia_public_inventories.py"))
            ok++;
    }

    return ok;
}
