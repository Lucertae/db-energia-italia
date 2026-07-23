#ifndef ASTRO_H
#define ASTRO_H

#include <windows.h>

#define PI  3.14159265358979323846
#define RAD (PI / 180.0)

BOOL astro_jd_from_utc(const SYSTEMTIME *utc, double *jd);
BOOL astro_utc_from_jd(double jd, SYSTEMTIME *utc);

#endif
