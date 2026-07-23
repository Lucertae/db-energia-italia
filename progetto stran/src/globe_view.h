#ifndef GLOBE_VIEW_H
#define GLOBE_VIEW_H

#include "common.h"

void globe_view_init(void);
void globe_view_paint(HDC dc, const RECT *rc);
void globe_view_show(HWND parent, const RECT *content);
void globe_view_hide(void);
int  globe_view_running(void);

#endif
