#ifndef SPINE_H
#define SPINE_H

#include "common.h"

typedef struct {
    char   id[16];
    char   status[20];
    int    age_h;
    int    max_age_h;
    char   tier[12];
} SpineRow;

typedef struct {
    char   id[16];
    char   status[16];
    char   title[120];
} SpineSignal;

typedef struct {
    char   id[16];
    char   msg[96];
    int    alert;
} SpineLive;

void spine_init(void);
void spine_spawn_build(void);
int  spine_reload(void);
void spine_get_summary(int *ok, int *stale, int *missing);
const char *spine_brief(void);
int  spine_series_count(void);
const SpineRow *spine_series_get(int i);
int  spine_signal_count(void);
const SpineSignal *spine_signal_get(int i);
int  spine_live_count(void);
const SpineLive *spine_live_get(int i);
void spine_paint_ops(HDC dc, RECT *body, int *y);

#endif
