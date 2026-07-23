#include "astro.h"

BOOL astro_jd_from_utc(const SYSTEMTIME *utc, double *jd) {
    FILETIME ft;
    SYSTEMTIME s = *utc;
    ULARGE_INTEGER q;

    if (!SystemTimeToFileTime(&s, &ft)) return FALSE;
    q.LowPart = ft.dwLowDateTime;
    q.HighPart = ft.dwHighDateTime;
    *jd = (double)q.QuadPart / 864000000000.0 + 2305813.5;
    return TRUE;
}

BOOL astro_utc_from_jd(double jd, SYSTEMTIME *utc) {
    ULARGE_INTEGER q;
    FILETIME ft;

    q.QuadPart = (ULONGLONG)((jd - 2305813.5) * 864000000000.0);
    ft.dwLowDateTime = q.LowPart;
    ft.dwHighDateTime = q.HighPart;
    return FileTimeToSystemTime(&ft, utc) != 0;
}
