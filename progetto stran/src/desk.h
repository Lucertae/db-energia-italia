#ifndef DESK_H
#define DESK_H

#include "common.h"

LRESULT CALLBACK desk_wndproc(HWND w, UINT m, WPARAM wp, LPARAM lp);
void desk_tick(void);
void desk_paint(HDC dc, const RECT *clip);

#endif
