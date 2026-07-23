#ifndef SERIES_H
#define SERIES_H

#include "common.h"
#include <stdint.h>

#define SER_MAX       128
#define SER_POINTS    1300

#define SER_ENERGY    0
#define SER_FX        1
#define SER_RATE      2
#define SER_MACRO     3
#define SER_CRYPTO    4

typedef struct {
    char     id[4];
    wchar_t  label[14];
    uint8_t  kind;
    uint16_t n;
    uint32_t ymd[SER_POINTS];
    float    val[SER_POINTS];
    float    live;
    float    min_h;
    float    max_h;
} DataSeries;

typedef struct {
    DataSeries s[SER_MAX];
    int        n;
} SeriesStore;

void series_init(SeriesStore *st);
void series_clear(SeriesStore *st);
DataSeries *series_get(SeriesStore *st, const char *id);
DataSeries *series_add(SeriesStore *st, const char *id, const wchar_t *label, uint8_t kind);
void series_load(SeriesStore *st, const char *id, const uint32_t *ymd, const float *val, int n, float live);
void series_touch_day(DataSeries *d, uint32_t ymd, float v);
float series_last(const DataSeries *s);
void series_range(const DataSeries *s, float *out_min, float *out_max, float *out_last);

#endif
