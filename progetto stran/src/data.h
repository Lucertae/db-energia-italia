#ifndef DATA_H
#define DATA_H

#include "common.h"
#include "signal.h"
#include "series.h"

#define WM_APP_DATA_READY (WM_APP + 42)

void data_init(void);
void data_shutdown(void);
void data_on_ready(void);
void data_tick(void);
void data_paint_lines(HDC dc, int x, int y, int w, int max_y);
void data_paint_footer(HDC dc, const RECT *rc);

const SigBus *data_bus(void);
const wchar_t *data_status(void);
double data_sig(const char *id);

BOOL data_series_snap(const char *id, DataSeries *out);
void data_store_read(void (*fn)(const SeriesStore *, void *), void *ctx);

void data_kick_intel(void);

#endif
