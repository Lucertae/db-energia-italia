#ifndef CHART_H
#define CHART_H

#include "series.h"
#include "dcf.h"

void chart_sparkline(HDC dc, const RECT *rc, const DataSeries *s, COLORREF line, COLORREF live);
/* label band + delta badge + sparkline, one data card */
void chart_series_cell(HDC dc, const RECT *rc, const DataSeries *s);
void chart_football(HDC dc, const RECT *rc, const DataSeries *s, const wchar_t *title);
void chart_fx_network(HDC dc, const RECT *rc, const SeriesStore *st);
extern char g_fx_hub[4];
int chart_fx_network_hit(POINT pt, char *out_id);
void chart_energy_network(HDC dc, const RECT *rc, const SeriesStore *st);
extern char g_en_hub[4];
void chart_range_vol(HDC dc, const RECT *rc, const DataSeries **list, int n);
void chart_corr_matrix(HDC dc, const RECT *rc, const SeriesStore *st,
                       const char ids[][4], int n_ids);
/* Matrice rho90 + striscia delta rho30-90 sotto */
void chart_corr_matrix_delta(HDC dc, const RECT *rc, const SeriesStore *st,
                             const char ids[][4], int n_ids);
void chart_crypto_network(HDC dc, const RECT *rc, const SeriesStore *st);
extern char g_crypto_hub[4];
int chart_crypto_network_hit(POINT pt, char *out_id);
void chart_transition_network(HDC dc, const RECT *rc, const SeriesStore *st);
extern char g_trans_hub[4];

/* Curva tassi US: U2/U5/U10/U30 */
void chart_yield_curve(HDC dc, const RECT *rc, const SeriesStore *st);

/* Serie spread allineata (mode 0=diff, 1=ratio) */
void chart_spread_ts(HDC dc, const RECT *rc, const DataSeries *a, const DataSeries *b,
                     int mode, const wchar_t *title);

/* Barre orizzontali valori last */
void chart_bar_last(HDC dc, const RECT *rc, const SeriesStore *st,
                    const char *ids[], const wchar_t *labels[], int n,
                    const wchar_t *unit);

#include "production.h"
void chart_fuel_stack(HDC dc, const RECT *rc, const ProdCountry *p);

/* Horizon: serie compressa in banda (4-6 righe), intensita = magnitudo */
void chart_horizon(HDC dc, const RECT *rc, const DataSeries *s, const wchar_t *label,
                   COLORREF line, int rows);

/* Heatmap ora x giorno (rows=ore, cols=giorni) */
void chart_calendar_heatmap(HDC dc, const RECT *rc, const float *vals, int rows, int cols,
                            float vmin, float vmax, const wchar_t *title);

/* Gauge orizzontale con soglie */
void chart_gauge(HDC dc, const RECT *rc, float val, float lo, float mid, float hi,
                 const wchar_t *label, const wchar_t *unit);

/* Barre divergenti orizzontali (valori +/-) */
void chart_bar_divergent(HDC dc, const RECT *rc, const wchar_t *labels[], const float *vals,
                         int n, float vmax);

/* Due serie sovrapposte nello stesso plot (es. D vs D-1) */
void chart_dual_spark(HDC dc, const RECT *rc, const DataSeries *a, const DataSeries *b,
                      COLORREF col_a, COLORREF col_b, const wchar_t *leg_a, const wchar_t *leg_b);

/* Barra regime continua 0..100 */
void chart_regime_bar(HDC dc, const RECT *rc, float score, const wchar_t *label);

#endif
