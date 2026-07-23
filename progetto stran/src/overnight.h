#ifndef OVERNIGHT_H
#define OVERNIGHT_H

#include "common.h"

typedef struct {
    BYTE us_open, asia_open, eu_open;
    BYTE us_overnight;
    wchar_t phase[40];
    wchar_t next_open[48];
    wchar_t pricer[48];
} OvernightState;

extern OvernightState g_ovn;

void overnight_update(void);
void overnight_paint(HDC dc, int x, int y, int w);

#endif
