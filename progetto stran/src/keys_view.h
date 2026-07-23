#ifndef KEYS_VIEW_H
#define KEYS_VIEW_H

#include "common.h"

void keys_view_init(void);
void keys_view_paint(HDC dc, const RECT *rc);
void keys_view_scroll(int lines);
int  keys_view_key(int vk);
int  keys_view_wheel(int delta);
int  keys_view_hit(POINT pt);
void keys_view_char(wchar_t ch);
void keys_view_clear_edit(void);
int  keys_view_editing(void); /* 1 if edit buffer active */
void keys_view_select(int idx);
void keys_view_edit_selected(void);

#endif
