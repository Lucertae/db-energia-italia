#ifndef COUNTRIES_H
#define COUNTRIES_H

#include "common.h"
#include "series.h"

#define CTRY_MAX       24
#define CTRY_HIST_MAX  70

void countries_init(void);
void countries_reload(void);
int  countries_count(void);
int  countries_selected(void);
void countries_set_selected(int i);
int  countries_list_hit(POINT pt);
void countries_paint(HDC dc, const RECT *rc);
const wchar_t *countries_status_line(void);

#endif
