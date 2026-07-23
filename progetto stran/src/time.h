#ifndef TIME_H
#define TIME_H

#include "common.h"

#define CLOCK_N   15
#define MAX_TZ    256
#define I_UTC     0
#define I_LON     5
#define I_NYC     1
#define I_DXB     8
#define I_TYO     13

typedef struct {
    const wchar_t *city, *abbr, *tz_id;
    double lat, lon;
    DYNAMIC_TIME_ZONE_INFORMATION tz;
    WORD dy, dm, dd;
    BYTE ok, sun_s, day;
    SYSTEMTIME rise, set, loc;
    RECT row;
    wchar_t t[9];
} Clock;

BOOL time_init(void);
void time_calc_sun(Clock *c, const SYSTEMTIME *loc);
void time_layout_rows(void);
void time_update(const SYSTEMTIME *utc);
void time_paint_header(HDC dc);
void time_paint_panel(HDC dc);

Clock *time_get(int i);
int time_region_days(int a, int b);
const wchar_t *time_utc_hms(void);
const wchar_t *time_local_hms(void);
const wchar_t *time_local_lbl(void);

#endif
