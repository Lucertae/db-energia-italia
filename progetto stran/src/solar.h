#ifndef SOLAR_H
#define SOLAR_H

#include "common.h"

extern int solar_days, solar_nights;
extern wchar_t solar_footer[96];
extern wchar_t solar_hub[3][48];

void solar_update(void);
void solar_paint(HDC dc);
void solar_paint_footer(HDC dc);

#endif
