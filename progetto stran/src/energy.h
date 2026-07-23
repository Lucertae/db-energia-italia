#ifndef ENERGY_H
#define ENERGY_H

#include "common.h"
#include "series.h"

void energy_spread_brt_wti(const SeriesStore *st, float *spread, float *chg);
void energy_spread_ttf_hh(const SeriesStore *st, float *ratio, float *chg);
void energy_spread_dark(const SeriesStore *st, float *ratio, float *chg);
void energy_spread_spark(const SeriesStore *st, float *ratio, float *chg, float *rho90);
void energy_paint_page(HDC dc, const RECT *rc, const SeriesStore *st);
void energy_paint_desk(HDC dc, const RECT *rc, const SeriesStore *st);

#endif
