#ifndef LAB_H
#define LAB_H

#include "common.h"
#include "series.h"

void lab_reload(void);
void lab_paint(HDC dc, const RECT *rc);
int  lab_key(int vk);
int  lab_row_count(void);
void lab_row_summary(int i, wchar_t *out, int cap);
void lab_ic_bars(HDC dc, const RECT *rc, int sel);

#endif
