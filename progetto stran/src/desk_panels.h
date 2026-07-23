#ifndef DESK_PANELS_H
#define DESK_PANELS_H

#include "common.h"
#include "series.h"

void desk_paint_entsoe_capacity(HDC dc, const RECT *rc);
void desk_paint_entsoe_wind(HDC dc, const RECT *rc, const SeriesStore *st);
void desk_paint_entsoe_hourly(HDC dc, const RECT *rc, const char *desk);
void desk_paint_georisk(HDC dc, const RECT *rc, const SeriesStore *st);

#endif
