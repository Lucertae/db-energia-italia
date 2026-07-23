#ifndef MOON_H
#define MOON_H

#include "common.h"

typedef struct {
    double phase, illum, age, to_full, to_new;
    double tidal_coef;
    BYTE waxing;
    wchar_t name[24], cycle[32], line1[48], line2[48];
    wchar_t tidal_note[56];
    wchar_t solar_note[56];
    wchar_t wind_note[56];
    wchar_t hydro_note[56];
    wchar_t tide_pwr_note[56];
} MoonState;

void moon_update(const SYSTEMTIME *utc);
void moon_paint_icon(HDC dc);
void moon_paint_popup(HDC dc);
void moon_paint_page(HDC dc, const RECT *rc);
const MoonState *moon_state(void);

/* 1 = popup dettaglio visibile (toggle da click sull'icona) */
extern int g_moon_open;

#endif
