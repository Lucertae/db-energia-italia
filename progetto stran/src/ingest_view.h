#ifndef INGEST_VIEW_H
#define INGEST_VIEW_H

#include "common.h"

#define ING_TAB_COUNT  8

extern int g_ing_tab;

void ingest_view_init(void);
void ingest_view_reload(void);
void ingest_view_paint(HDC dc, const RECT *rc);
void ingest_view_scroll(int lines);
void ingest_view_tab_next(int dir);
void ingest_view_tick(void);
int  ingest_view_poll(void);
int  ingest_view_key(int vk);
int  ingest_view_wheel(int delta);
int  ingest_view_hit(POINT pt);
void ingest_view_char(wchar_t ch);
void ingest_view_clear_search(void);
void ingest_view_force_rebuild(void);

#endif
