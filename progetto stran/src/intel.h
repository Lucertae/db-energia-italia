#ifndef INTEL_H
#define INTEL_H

#include "common.h"

#define INTEL_CAT_N    8
#define INTEL_HEAD_MAX 1024
#define INTEL_EVT_MAX  80
#define INTEL_NAME_LEN 48

typedef struct {
    char     desk[12];
    char     ts[24];
    char     source[12];
    char     name[INTEL_NAME_LEN];
    char     title[220];
    char     url[256];
} IntelRow;

typedef struct {
    char     type[12];
    char     ts[24];
    char     title[200];
    char     severity[16];
    char     source[16];
    char     url[256];
    float    lat;
    float    lon;
} IntelEvent;

void intel_desk_init(void);
int  intel_desk_reload(void);
int  intel_desk_poll(void);
const char *intel_desk_built_at(void);
void intel_desk_set_category(int cat);
int  intel_desk_category(void);
int  intel_desk_scroll(void);
void intel_desk_scroll_delta(int lines);
int  intel_desk_visible_count(void);
const wchar_t *intel_desk_cat_label(int cat);
int  intel_desk_cat_count(int cat);

void intel_paint_page(HDC dc, const RECT *rc);
void intel_paint_ticker(HDC dc, const RECT *rc, const char *desk_filter, int max_rows);
void intel_paint_events(HDC dc, const RECT *rc, int max_rows);
int  intel_desk_key(int vk);
int  intel_desk_wheel(int delta);
int  intel_desk_cat_hit(POINT pt, const RECT *sidebar);

#endif
