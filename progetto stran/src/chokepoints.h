#ifndef CHOKEPOINTS_H
#define CHOKEPOINTS_H

#include "common.h"

#define CP_MAX_ROWS   12
#define CP_MAX_HEAD   128
#define CP_NAME_LEN   40

typedef struct {
    char     desk_id[12];
    char     pw_id[20];
    char     name[CP_NAME_LEN];
    char     last_date[12];
    int      n_total;
    int      n_tanker;
    int      baseline_total;
    int      delta_pct;
    int      ais_live;
    float    lat;
    float    lon;
    float    bbox[4];
} ChokepointRow;

typedef struct {
    char     ts[24];
    char     source[12];
    char     title[200];
    char     url[256];
} IntelHeadline;

void chokepoints_init(void);
int  chokepoints_reload(void);
void chokepoints_ais_update(void);
int  chokepoints_count(void);
const ChokepointRow *chokepoints_get(int i);
void chokepoints_brief(wchar_t *out, int cap);

int  intel_headline_count(void);
const IntelHeadline *intel_headline_get(int i);
int  intel_reload_headlines(void);

void chokepoints_lng_eu_stats(int *count7, int *delta);
void chokepoints_paint(HDC dc, const RECT *rc);

#endif
