#include "energy.h"
#include "corr.h"
#include "chart.h"
#include "data.h"
#include "fin.h"
#include "glossary.h"
#include "moon.h"
#include "pages.h"
#include "intel.h"
#include <math.h>

static float series_chg(const DataSeries *s) {
    float last, prev;
    if (!s || s->n < 2) return 0.0f;
    last = series_last(s);
    prev = s->val[s->n - 2];
    if (prev <= 0.0f) return 0.0f;
    return (last - prev) / prev;
}

void energy_spread_brt_wti(const SeriesStore *st, float *spread, float *chg) {
    DataSeries *b = series_get((SeriesStore *)st, "BRT");
    DataSeries *w = series_get((SeriesStore *)st, "WTI");
    if (!b || !w || b->n < 2 || w->n < 2) {
        if (spread) *spread = 0.0f;
        if (chg) *chg = 0.0f;
        return;
    }
    if (spread) *spread = series_last(b) - series_last(w);
    if (chg) *chg = series_chg(b) - series_chg(w);
}

void energy_spread_ttf_hh(const SeriesStore *st, float *ratio, float *chg) {
    DataSeries *t = series_get((SeriesStore *)st, "TTF");
    DataSeries *h = series_get((SeriesStore *)st, "HUB");
    if (!t || !h || t->n < 2 || h->n < 2 || series_last(h) <= 0.0f) {
        if (ratio) *ratio = 0.0f;
        if (chg) *chg = 0.0f;
        return;
    }
    if (ratio) *ratio = series_last(t) / series_last(h);
    if (chg) {
        float rt = series_last(t) / series_last(h);
        float rp = t->val[t->n - 2] / h->val[h->n - 2];
        *chg = rp > 0.0f ? (rt - rp) / rp : 0.0f;
    }
}

void energy_spread_dark(const SeriesStore *st, float *ratio, float *chg) {
    DataSeries *c = series_get((SeriesStore *)st, "COA");
    DataSeries *t = series_get((SeriesStore *)st, "TTF");
    if (!c || !t || c->n < 2 || t->n < 2 || series_last(t) <= 0.0f) {
        if (ratio) *ratio = 0.0f;
        if (chg) *chg = 0.0f;
        return;
    }
    if (ratio) *ratio = series_last(c) / series_last(t);
    if (chg) {
        float rt = series_last(c) / series_last(t);
        float rp = c->val[c->n - 2] / t->val[t->n - 2];
        *chg = rp > 0.0f ? (rt - rp) / rp : 0.0f;
    }
}

void energy_spread_spark(const SeriesStore *st, float *ratio, float *chg, float *rho90) {
    DataSeries *g = series_get((SeriesStore *)st, "TTF");
    DataSeries *p = series_get((SeriesStore *)st, "PDE");
    CorrPair cp;
    if (rho90) *rho90 = 0.0f;
    if (!g || !p || g->n < 2 || p->n < 2 || series_last(p) <= 0.0f) {
        if (ratio) *ratio = 0.0f;
        if (chg) *chg = 0.0f;
        return;
    }
    if (ratio) *ratio = series_last(g) / series_last(p);
    if (chg) {
        float rt = series_last(g) / series_last(p);
        float rp = g->val[g->n - 2] / p->val[p->n - 2];
        *chg = rp > 0.0f ? (rt - rp) / rp : 0.0f;
    }
    if (rho90) {
        corr_pair_compute(g, p, &cp);
        if (cp.ok) *rho90 = cp.rho90;
    }
}

static void paint_spread_charts(HDC dc, RECT left, const SeriesStore *st) {
    static const struct { const char *a, *b; int mode; const wchar_t *title; } SP[] = {
        { "BRT", "WTI", 0, L"BRT-WTI ($)" },
        { "TTF", "HUB", 1, L"TTF/HH (x)" },
        { "COA", "TTF", 1, L"COAL/TTF (x)" },
        { "TTF", "PDE", 1, L"TTF/PDE spark" }
    };
    int i, gh = (left.bottom - left.top) / 2;

    for (i = 0; i < 4; i++) {
        RECT cell = left;
        DataSeries *sa = series_get((SeriesStore *)st, SP[i].a);
        DataSeries *sb = series_get((SeriesStore *)st, SP[i].b);
        cell.left += (i % 2) * ((left.right - left.left) / 2);
        cell.right = cell.left + (left.right - left.left) / 2 - 4;
        cell.top += (i / 2) * gh;
        cell.bottom = cell.top + gh - 4;
        if (sa && sb && sa->n >= 5 && sb->n >= 5)
            chart_spread_ts(dc, &cell, sa, sb, SP[i].mode, SP[i].title);
    }
}

void energy_paint_page(HDC dc, const RECT *rc, const SeriesStore *st) {
    RECT r = *rc, net, mid, left, right, bot, cell, gloss;
    static const char *IDS1[6] = { "BRT", "WTI", "HUB", "TTF", "COA", "JKM" };
    static const char *IDS2[6] = { "EUA", "NGF", "GRN", "CBE", "GPR", "CVI" };
    int i, w3, h;
    DataSeries snap;
    wchar_t line[96], v[16];

    if (!st) return;
    h = r.bottom - r.top;

    gloss = r;
    gloss.left = gloss.right - 228;
    r.right = gloss.left - 8;
    gloss_paint_panel(dc, &gloss, PAGE_NRG);

    ui_subheading(dc, &(RECT){ r.left, r.top, r.right, r.top + 12 }, L"ENERGY NETWORK");
    r.top += 14;
    net = r;
    net.bottom = r.top + h * 30 / 100;
    chart_energy_network(dc, &net, st);

    mid = r;
    mid.top = net.bottom + 6;
    mid.bottom = r.top + h * 70 / 100;
    left = mid;
    left.right = mid.left + (mid.right - mid.left) * 50 / 100;
    right = mid;
    right.left = left.right + 8;

    ui_subheading(dc, &(RECT){ left.left, left.top, left.right, left.top + 12 },
                  L"SPREADS 90gg");
    left.top += 14;
    paint_spread_charts(dc, left, st);

    w3 = (right.right - right.left) / 3;
    for (i = 0; i < 6; i++) {
        cell.left = right.left + (i % 3) * w3;
        cell.right = right.left + (i % 3 + 1) * w3 - 4;
        cell.top = right.top + (i / 3) * 44;
        cell.bottom = cell.top + 40;
        if (data_series_snap(IDS1[i], &snap))
            chart_series_cell(dc, &cell, &snap);
    }

    bot = r;
    bot.top = mid.bottom + 6;
    ui_subheading(dc, &(RECT){ bot.left, bot.top, bot.right, bot.top + 12 },
                  L"TRANSITION + RISK");
    bot.top += 14;
    w3 = (bot.right - bot.left) / 3;
    for (i = 0; i < 6; i++) {
        cell.left = bot.left + (i % 3) * w3;
        cell.right = bot.left + (i % 3 + 1) * w3 - 4;
        cell.top = bot.top + (i / 3) * 44;
        cell.bottom = cell.top + 40;
        if (cell.bottom > r.bottom - 18) break;
        if (data_series_snap(IDS2[i], &snap))
            chart_series_cell(dc, &cell, &snap);
    }

    {
        DataSeries *btc = series_get((SeriesStore *)st, "BTC");
        DataSeries *cbe = series_get((SeriesStore *)st, "CBE");
        CorrPair cp;
        if (btc && cbe) {
            corr_pair_compute(btc, cbe, &cp);
            if (cp.ok) {
                ui_fmt_wdouble(v, 16, cp.rho90, 2);
                wsprintfW(line, L"BTC-CBE \x03C1 90d=%s  [NARDL mining power]", v);
                SetTextColor(dc, CLR_ACC);
                SelectObject(dc, fSm);
                TextOutW(dc, bot.left, r.bottom - 28, line, lstrlenW(line));
            }
        }
    }
    gloss_paint_footer(dc, &(RECT){ r.left, r.bottom - 14, r.right, r.bottom }, PAGE_NRG);
}

void energy_paint_desk(HDC dc, const RECT *rc, const SeriesStore *st) {
    static const struct { const char *id; const wchar_t *z; } ZONES[] = {
        { "PDE", L"DE" }, { "PFR", L"FR" }, { "PIT", L"IT" }, { "PNL", L"NL" },
        { "PAT", L"AT" }, { "PPL", L"PL" }, { "PNO", L"NO" }
    };
    RECT r = *rc, map, curves, spreads, heat, foot;
    float heatbuf[30];
    int w = r.right - r.left, i, hi, nd;
    const MoonState *ms = moon_state();
    DataSeries snap_a, snap_b;

    map = r;
    map.bottom = r.top + (r.bottom - r.top) * 24 / 100;
    curves = r;
    curves.top = map.bottom + 6;
    curves.bottom = r.top + (r.bottom - r.top) * 46 / 100;
    spreads = r;
    spreads.top = curves.bottom + 6;
    spreads.bottom = r.top + (r.bottom - r.top) * 78 / 100;
    spreads.right = r.left + (r.right - r.left) * 52 / 100;
    heat = r;
    heat.left = spreads.right + 8;
    heat.top = spreads.top;
    heat.bottom = spreads.bottom;
    foot = r;
    foot.top = spreads.bottom + 6;

    ui_subheading(dc, &(RECT){ map.left, map.top, map.right, map.top + 12 },
                  L"ZONE DA  EUR/MWh  (ENTSO-E day-ahead)");
    {
        int tw = (map.right - map.left) / 7;
        int y0 = map.top + 14;
        float scale_max = 50.0f;
        for (i = 0; i < 7; i++) {
            const DataSeries *s = series_get((SeriesStore *)st, ZONES[i].id);
            if (s && s->max_h > scale_max) scale_max = s->max_h;
        }
        if (scale_max < 80.0f) scale_max = 80.0f;
        for (i = 0; i < 7; i++) {
            RECT tile;
            const DataSeries *s = series_get((SeriesStore *)st, ZONES[i].id);
            float v = s && s->n > 0 ? series_last(s) : 0.0f;
            float d1 = 0.0f;
            float t = scale_max > 0.0f ? v / scale_max : 0.0f;
            HBRUSH br;
            wchar_t cap[28];
            if (s && s->n >= 2 && s->val[s->n - 2] > 0.0f)
                d1 = (v - s->val[s->n - 2]) / s->val[s->n - 2] * 100.0f;
            if (t < 0.0f) t = 0.0f;
            if (t > 1.0f) t = 1.0f;
            tile.left = map.left + i * tw;
            tile.right = tile.left + tw - 2;
            tile.top = y0;
            tile.bottom = map.bottom - 4;
            br = CreateSolidBrush(RGB((int)(40 + t * 200), (int)(40 + (1.0f - t) * 80), 40));
            if (br) {
                FillRect(dc, &tile, br);
                DeleteObject(br);
            }
            wsprintfW(cap, L"%s\n%.1f\n%+.1f%%", ZONES[i].z, v, d1);
            SetTextColor(dc, CLR_TXT);
            SelectObject(dc, fSm);
            DrawTextW(dc, cap, -1, &tile, DT_CENTER | DT_VCENTER | DT_NOPREFIX);
        }
    }

    ui_frame(dc, &curves, L"PDE DA 30g spark  D vs D-1");
    {
        RECT inner = ui_panel_body(&curves);
        DataSeries *pde = series_get((SeriesStore *)st, "PDE");
        RECT plot = inner;
        wchar_t note[120], pctl[16];
        plot.top += 12;
        if (pde && pde->n >= 4 && pde->n <= SER_POINTS) {
            int n = (int)pde->n;
            int back = n > 30 ? 30 : n - 1;
            int j;
            float mn, mx;

            if (back >= 2) {
                snap_a.n = (uint16_t)back;
                snap_b.n = (uint16_t)back;
                snap_a.live = snap_b.live = 0.0f;
                for (j = 0; j < back; j++) {
                    snap_a.val[j] = pde->val[n - back + j];
                    if (n - back - 1 + j >= 0)
                        snap_b.val[j] = pde->val[n - back - 1 + j];
                    else
                        snap_b.val[j] = pde->val[j];
                }
                mn = mx = snap_a.val[0];
                for (j = 1; j < back; j++) {
                    if (snap_a.val[j] < mn) mn = snap_a.val[j];
                    if (snap_a.val[j] > mx) mx = snap_a.val[j];
                    if (snap_b.val[j] < mn) mn = snap_b.val[j];
                    if (snap_b.val[j] > mx) mx = snap_b.val[j];
                }
                snap_a.min_h = snap_b.min_h = mn;
                snap_a.max_h = snap_b.max_h = mx;
                chart_dual_spark(dc, &plot, &snap_a, &snap_b, CLR_LINE, CLR_ACC,
                                 L"D", L"D-1");
            }
            ui_fmt_wdouble(pctl, 16, fin_percentile_rank(pde, 252) * 100.0f, 0);
            wsprintfW(note, L"serie giornaliera PDE  |  pct1y %s%%", pctl);
            SetTextColor(dc, CLR_DIM);
            SelectObject(dc, fSm);
            TextOutW(dc, inner.left, inner.bottom - 12, note, lstrlenW(note));
        } else {
            ui_label_rect(dc, &plot, L"attesa serie PDE (day-ahead)", CLR_OFF, fSm);
        }
    }

    ui_frame(dc, &spreads, L"SPREAD ENGINE  horizon + pct 1y");
    {
        static const struct { const char *a, *b; const wchar_t *t; } SP[] = {
            { "TTF", "NGF", L"TTF/DE" }, { "COA", "TTF", L"COAL/TTF" },
            { "TTF", "HUB", L"TTF/HH" }, { "TTF", "JKM", L"TTF/JKM" }
        };
        RECT inner = ui_panel_body(&spreads);
        int sh = (inner.bottom - inner.top) / 4;
        wchar_t cap[64], pctl[12];
        for (i = 0; i < 4; i++) {
            RECT cell;
            DataSeries *sa = series_get((SeriesStore *)st, SP[i].a);
            DataSeries *sb = series_get((SeriesStore *)st, SP[i].b);
            cell = inner;
            cell.top = inner.top + i * sh;
            cell.bottom = cell.top + sh - 2;
            if (sa && sb && sa->n >= 5 && sb->n >= 5) {
                ui_fmt_wdouble(pctl, 12, fin_percentile_rank(sa, 252) * 100.0f, 0);
                wsprintfW(cap, L"%s pct1y %s%%", SP[i].t, pctl);
                SetTextColor(dc, CLR_OFF);
                SelectObject(dc, fSm);
                TextOutW(dc, cell.left, cell.top, cap, lstrlenW(cap));
                cell.top += 11;
                chart_spread_ts(dc, &cell, sa, sb, 1, SP[i].t);
            }
        }
    }

    ui_frame(dc, &heat, L"HEATMAP  PDE DA daily 30g");
    {
        DataSeries *s = series_get((SeriesStore *)st, "PDE");
        float mn = 0.0f, mx = 1.0f;
        RECT inner = ui_panel_body(&heat);
        memset(heatbuf, 0, sizeof(heatbuf));
        nd = 0;
        if (s && s->n > 0) {
            mn = s->min_h;
            mx = s->max_h;
            nd = s->n > 30 ? 30 : (int)s->n;
            for (hi = 0; hi < nd; hi++)
                heatbuf[hi] = s->val[s->n - nd + hi];
        }
        if (nd > 0)
            chart_calendar_heatmap(dc, &inner, heatbuf, 1, nd, mn, mx, NULL);
        else
            ui_label_rect(dc, &inner, L"serie PDE non disponibile", CLR_OFF, fSm);
    }
    ui_frame(dc, &foot, L"TIDAL + NRG headlines");
    {
        RECT fin = ui_panel_body(&foot);
        RECT news;
        if (ms && ms->tide_pwr_note[0]) {
            wchar_t line[80];
            wsprintfW(line, L"coef %.2f", ms->tidal_coef);
            ui_label_rect(dc, &fin, line, CLR_DIM, fSm);
            fin.top += 14;
            ui_label_rect(dc, &fin, ms->tide_pwr_note, CLR_DIM, fSm);
            fin.top += 14;
        } else {
            ui_label_rect(dc, &fin, L"marea: moon state pending", CLR_OFF, fSm);
            fin.top += 14;
        }
        news = fin;
        news.top = fin.top + 2;
        intel_paint_ticker(dc, &news, "ENERGY", 4);
    }
    (void)w;
    (void)ms;
}
