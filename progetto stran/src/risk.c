#include "risk.h"
#include "systemic.h"
#include "chart.h"
#include "corr.h"
#include "data.h"
#include "fin.h"
#include "glossary.h"
#include "intel.h"

static void paint_grn_dir(HDC dc, RECT *row, const SeriesStore *st) {
    DataSeries *g = series_get((SeriesStore *)st, "GRN");
    DataSeries *d = series_get((SeriesStore *)st, "DIR");
    wchar_t line[96], v[16], c[16], r[16];
    float ratio, chg, rp, rt;
    CorrPair cp;

    if (!g || !d || g->n < 2 || d->n < 2 || series_last(d) <= 0.0f) return;
    ratio = series_last(g) / series_last(d);
    rt = ratio;
    rp = g->val[g->n - 2] / d->val[d->n - 2];
    chg = rp > 0.0f ? (rt - rp) / rp : 0.0f;
    ui_fmt_wdouble(v, 16, ratio, 3);
    ui_fmt_wdouble(c, 16, chg * 100.0f, 2);
    wsprintfW(line, L"GRN/DIR clean/dirty  %s  d %s%%", v, c);
    ui_label_rect(dc, row, line, CLR_ACC, fSm);
    corr_pair_compute(g, d, &cp);
    if (cp.ok) {
        row->top += 15;
        row->bottom += 15;
        ui_fmt_wdouble(r, 16, cp.rho90, 2);
        wsprintfW(line, L"  \x03C1 90d = %s  [MPRA clean vs dirty]", r);
        ui_label_rect(dc, row, line, CLR_DIM, fSm);
    }
    row->top += 15;
    row->bottom += 15;
}

static void paint_var_row(HDC dc, RECT *row, const SeriesStore *st) {
    static const char *IDS[4] = { "BRT", "BTC", "EUA", "GPR" };
    wchar_t line[160], seg[32], v[12];
    int i, pos = 0;

    line[0] = 0;
    lstrcatW(line, L"VaR95 252d  ");
    for (i = 0; i < 4; i++) {
        const DataSeries *s = series_get((SeriesStore *)st, IDS[i]);
        float var;
        if (!s || s->n < 60) continue;
        var = fin_var95_pct(s, 252);
        ui_fmt_wdouble(v, 12, var, 2);
        wsprintfW(seg, L"%hs %s%%  ", IDS[i], v);
        if (pos + lstrlenW(seg) < 150) {
            lstrcatW(line, seg);
            pos += lstrlenW(seg);
        }
    }
    ui_label_rect(dc, row, line, CLR_DIM, fSm);
    row->top += 15;
    row->bottom += 15;
}

void risk_paint_page(HDC dc, const RECT *rc, const SeriesStore *st) {
    RECT r = *rc, banner, top, bot, left, right, row, cell, fb;
    static const char *IDS[6] = { "GPR", "CPU", "CVI", "EUA", "GRN", "DIR" };
    const DataSeries *rv[4];
    DataSeries snap, *s;
    int i, w3, h, fh = 30;

    if (!st) return;
    h = r.bottom - r.top;

    banner = r;
    banner.bottom = r.top + h * 12 / 100;
    systemic_paint_banner(dc, &banner, st);

    top = r;
    top.top = banner.bottom + 6;
    top.bottom = top.top + h * 42 / 100;
    left = top;
    left.right = top.left + (top.right - top.left) * 55 / 100;
    right = top;
    right.left = left.right + 8;

    ui_subheading(dc, &(RECT){ left.left, left.top, left.right, left.top + 12 },
                  L"TRANSITION NETWORK");
    left.top += 14;
  {
        RECT net = left;
        net.bottom = left.bottom - 4;
        chart_transition_network(dc, &net, st);
    }

    ui_subheading(dc, &(RECT){ right.left, right.top, right.right, right.top + 12 },
                  L"52w FOOTBALL  risk indices");
    right.top += 14;
    fb = right;
    for (i = 0; i < 4; i++) {
        static const char *FB[4] = { "GPR", "CPU", "CVI", "VIX" };
        static const wchar_t *FT[4] = {
            L"GPR geopolitical", L"CPU climate policy", L"CVI crypto vol", L"VIX fear"
        };
        fb.top = right.top + i * fh;
        fb.bottom = fb.top + fh - 4;
        s = series_get((SeriesStore *)st, FB[i]);
        if (s && s->n >= 10)
            chart_football(dc, &fb, s, FT[i]);
    }

    bot = r;
    bot.top = top.bottom + 8;
    row = bot;
    row.bottom = row.top + 14;
    ui_subheading(dc, &(RECT){ bot.left, row.top, bot.right, row.top + 12 },
                  L"TRANSITION SPREADS");
    row.top += 14;
    row.bottom = row.top + 14;
    paint_grn_dir(dc, &row, st);
    paint_var_row(dc, &row, st);
  {
        DataSeries *eua = series_get((SeriesStore *)st, "EUA");
        DataSeries *brt = series_get((SeriesStore *)st, "BRT");
        CorrPair cp;
        wchar_t line[80], v[16];
        if (eua && brt) {
            corr_pair_compute(eua, brt, &cp);
            if (cp.ok) {
                ui_fmt_wdouble(v, 16, cp.rho90, 2);
                wsprintfW(line, L"EUA-BRT carbon vs oil  \x03C1=%s", v);
                ui_label_rect(dc, &row, line, CLR_OFF, fSm);
                row.top += 15;
                row.bottom += 15;
            }
        }
    }
  {
        RECT rv_rc = bot;
        rv_rc.top = row.top;
        rv_rc.bottom = rv_rc.top + 56;
        rv[0] = series_get((SeriesStore *)st, "GPR");
        rv[1] = series_get((SeriesStore *)st, "CPU");
        rv[2] = series_get((SeriesStore *)st, "CVI");
        rv[3] = series_get((SeriesStore *)st, "EUA");
        chart_range_vol(dc, &rv_rc, rv, 4);
        row.top = rv_rc.bottom + 4;
    }

    ui_subheading(dc, &(RECT){ bot.left, row.top, bot.right, row.top + 12 },
                  L"RISK + TRANSITION SERIES");
    row.top += 14;
    w3 = (bot.right - bot.left) / 3;
    for (i = 0; i < 6; i++) {
        cell.left = bot.left + (i % 3) * w3;
        cell.right = bot.left + (i % 3 + 1) * w3 - 4;
        cell.top = row.top + (i / 3) * 44;
        cell.bottom = cell.top + 40;
        if (cell.bottom > r.bottom - 14) break;
        if (data_series_snap(IDS[i], &snap))
            chart_series_cell(dc, &cell, &snap);
    }

    SetTextColor(dc, CLR_OFF);
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    {
        RECT fin;
        fin.left = r.left;
        fin.right = r.right;
        fin.top = r.bottom - 54;
        fin.bottom = r.bottom - 28;
        ui_subheading(dc, &fin, L"FINANCE headlines");
        fin.top += 14;
        intel_paint_ticker(dc, &fin, "FINANCE", 3);
    }
    gloss_paint_footer(dc, &(RECT){ r.left, r.bottom - 26, r.right, r.bottom - 12 },
                       PAGE_RISK);
}
