#include "series.h"
#include <string.h>

void series_init(SeriesStore *st) {
    memset(st, 0, sizeof(*st));
}

void series_clear(SeriesStore *st) {
    st->n = 0;
    memset(st->s, 0, sizeof(st->s));
}

DataSeries *series_get(SeriesStore *st, const char *id) {
    int i;

    for (i = 0; i < st->n; i++) {
        if (st->s[i].id[0] == id[0] && st->s[i].id[1] == id[1] &&
            st->s[i].id[2] == id[2])
            return &st->s[i];
    }
    return NULL;
}

DataSeries *series_add(SeriesStore *st, const char *id, const wchar_t *label, uint8_t kind) {
    DataSeries *d;

    d = series_get(st, id);
    if (d) return d;
    if (st->n >= SER_MAX) return NULL;
    d = &st->s[st->n++];
    memset(d, 0, sizeof(*d));
    d->id[0] = id[0];
    d->id[1] = id[1];
    d->id[2] = id[2];
    d->id[3] = 0;
    d->kind = kind;
    if (label) lstrcpynW(d->label, label, 14);
    return d;
}

void series_load(SeriesStore *st, const char *id, const uint32_t *ymd, const float *val,
                 int n, float live) {
    DataSeries *d;
    int i, start;
    float mn, mx;

    if (!st || !id || n <= 0) return;
    d = series_get(st, id);
    if (!d) return;
    if (n > SER_POINTS) {
        start = n - SER_POINTS;
        n = SER_POINTS;
    } else {
        start = 0;
    }
    d->n = (uint16_t)n;
    mn = mx = val[start];
    for (i = 0; i < n; i++) {
        d->ymd[i] = ymd[start + i];
        d->val[i] = val[start + i];
        if (d->val[i] < mn) mn = d->val[i];
        if (d->val[i] > mx) mx = d->val[i];
    }
    d->live = live > 0.0f ? live : (n ? d->val[n - 1] : 0.0f);
    if (d->live < mn) mn = d->live;
    if (d->live > mx) mx = d->live;
    d->min_h = mn;
    d->max_h = mx;
}

float series_last(const DataSeries *s) {
    if (!s) return 0.0f;
    if (s->live > 0.0f) return s->live;
    return s->n ? s->val[s->n - 1] : 0.0f;
}

void series_touch_day(DataSeries *d, uint32_t ymd, float v) {
    int i;
    float mn, mx;

    if (!d || v <= 0.0f) return;
    if (d->n == 0) {
        d->ymd[0] = ymd;
        d->val[0] = v;
        d->n = 1;
    } else if (d->ymd[d->n - 1] == ymd) {
        d->val[d->n - 1] = v;
    } else if (d->n < SER_POINTS) {
        d->ymd[d->n] = ymd;
        d->val[d->n] = v;
        d->n++;
    } else {
        memmove(d->ymd, d->ymd + 1, (SER_POINTS - 1) * sizeof(d->ymd[0]));
        memmove(d->val, d->val + 1, (SER_POINTS - 1) * sizeof(d->val[0]));
        d->ymd[SER_POINTS - 1] = ymd;
        d->val[SER_POINTS - 1] = v;
    }
    d->live = v;
    mn = mx = d->val[0];
    for (i = 1; i < d->n; i++) {
        if (d->val[i] < mn) mn = d->val[i];
        if (d->val[i] > mx) mx = d->val[i];
    }
    if (v < mn) mn = v;
    if (v > mx) mx = v;
    d->min_h = mn;
    d->max_h = mx;
}

void series_range(const DataSeries *s, float *out_min, float *out_max, float *out_last) {
    if (!s) return;
    if (out_min) *out_min = s->min_h;
    if (out_max) *out_max = s->max_h;
    if (out_last) *out_last = series_last(s);
}
