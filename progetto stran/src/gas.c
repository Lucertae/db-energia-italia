#include "gas.h"
#include "chart.h"
#include "energy.h"
#include "intel.h"
#include "chokepoints.h"
#include "ships.h"
#include "data.h"
#include "fin.h"
#include <math.h>

void gas_paint(HDC dc, const RECT *rc, const SeriesStore *st) {
    RECT r = *rc, left, mid, right, rtop, rbot;
    int w = r.right - r.left, h = r.bottom - r.top;
    DataSeries snap;
    wchar_t line[160], v[16], pctl[16];
    float ratio, chg;
    int lng7 = 0, dlng = 0;

    left = r;
    left.right = r.left + w * 32 / 100;
    mid = r;
    mid.left = left.right + 8;
    mid.right = r.right - w * 28 / 100;
    right = r;
    right.left = mid.right + 8;
    rtop = right;
    rtop.bottom = right.top + (right.bottom - right.top) * 48 / 100;
    rbot = right;
    rbot.top = rtop.bottom + 6;

    ui_frame(dc, &left, L"STORAGE EU  AGSI+ proxy");
    {
        RECT inner = ui_panel_body(&left);
        RECT hz = inner;
        RECT tbl = inner;
        int y;
        DataSeries *ttf = series_get((SeriesStore *)st, "TTF");
        DataSeries *ngs = series_get((SeriesStore *)st, "NGS");
        hz.bottom = inner.top + (inner.bottom - inner.top) * 62 / 100;
        if (ttf && ttf->n >= 5) {
            ui_fmt_wdouble(pctl, 16, fin_percentile_rank(ttf, 252) * 100.0f, 0);
            wsprintfW(line, L"TTF fill proxy  pct1y %s%%", pctl);
            SetTextColor(dc, CLR_DIM);
            SelectObject(dc, fSm);
            TextOutW(dc, inner.left, inner.top, line, lstrlenW(line));
            hz.top += 14;
            chart_horizon(dc, &hz, ttf, L"AGSI+ banda 5y (TTF proxy)", CLR_LINE, 6);
        }
        tbl.top = hz.bottom + 6;
        y = tbl.top;
        ui_subheading(dc, &(RECT){ tbl.left, y, tbl.right, y + 12 }, L"per paese (livello proxy)");
        y += 14;
        if (ngs && ngs->n >= 2) {
            ui_fmt_wdouble(v, 16, series_last(ngs), 1);
            wsprintfW(line, L"DE stor %s Bcf-eq", v);
            TextOutW(dc, tbl.left, y, line, lstrlenW(line));
            y += 13;
        }
        if (ttf && ttf->n >= 2) {
            ui_fmt_wdouble(v, 16, series_last(ttf), 1);
            wsprintfW(line, L"EU hub TTF %s EUR/MWh", v);
            TextOutW(dc, tbl.left, y, line, lstrlenW(line));
        }
    }

    ui_frame(dc, &mid, L"HUB SPREAD  TTF / HH / JKM");
    {
        RECT inner = ui_panel_body(&mid);
        int sh = (inner.bottom - inner.top) / 3;
        int i;
        static const struct { const char *id; const wchar_t *lbl; } HUBS[] = {
            { "TTF", L"TTF" }, { "HUB", L"HH" }, { "JKM", L"JKM" }
        };
        energy_spread_ttf_hh(st, &ratio, &chg);
        ui_fmt_wdouble(v, 16, ratio, 2);
        wsprintfW(line, L"TTF/HH %s  d %+.1f%%  (soglia GAS-X se >2.5x)", v, chg * 100.0f);
        SetTextColor(dc, ratio > 2.5f ? CLR_DN : CLR_TXT);
        SelectObject(dc, fSm);
        TextOutW(dc, inner.left, inner.top, line, lstrlenW(line));
        for (i = 0; i < 3; i++) {
            RECT cell = inner;
            const DataSeries *s = series_get((SeriesStore *)st, HUBS[i].id);
            cell.top = inner.top + 16 + i * sh;
            cell.bottom = cell.top + sh - 4;
            if (s && s->n >= 3)
                chart_horizon(dc, &cell, s, HUBS[i].lbl, CLR_LINE, 5);
        }
    }

    ui_frame(dc, &rtop, L"FLUSSI  LNG verso EU");
    {
        RECT inner = ui_panel_body(&rtop);
        int y = inner.top, lh = 13, ais_eu;
        chokepoints_lng_eu_stats(&lng7, &dlng);
        ais_eu = ships_count_in_bbox(35.0f, 62.0f, -12.0f, 28.0f);
        wsprintfW(line, L"tanker chokepoint 7d: %d  (%+d vs 7d prec)", lng7, dlng);
        SetTextColor(dc, dlng >= 0 ? CLR_UP : CLR_DN);
        SelectObject(dc, fSm);
        TextOutW(dc, inner.left, y, line, lstrlenW(line));
        y += lh;
        wsprintfW(line, L"AIS live EU waters: %d navi", ais_eu);
        SetTextColor(dc, CLR_TXT);
        TextOutW(dc, inner.left, y, line, lstrlenW(line));
        y += lh + 2;
        ui_subheading(dc, &(RECT){ inner.left, y, inner.right, y + 12 }, L"MARITIME feed");
        y += 14;
        {
            RECT tick;
            tick.left = inner.left;
            tick.right = inner.right;
            tick.top = y;
            tick.bottom = inner.bottom;
            intel_paint_ticker(dc, &tick, "MARITIME", 5);
        }
    }

    ui_frame(dc, &rbot, L"US  EIA storage + HH");
    {
        RECT inner = ui_panel_body(&rbot);
        DataSeries *hub = series_get((SeriesStore *)st, "HUB");
        DataSeries *ngs = series_get((SeriesStore *)st, "NGS");
        RECT hz = inner;
        int y = inner.top;
        if (ngs && ngs->n >= 3) {
            ui_fmt_wdouble(pctl, 16, fin_percentile_rank(ngs, 252) * 100.0f, 0);
            wsprintfW(line, L"US stor pct 1y %s%%", pctl);
            SetTextColor(dc, CLR_DIM);
            SelectObject(dc, fSm);
            TextOutW(dc, inner.left, y, line, lstrlenW(line));
            y += 13;
            hz.top = y;
            hz.bottom = inner.bottom;
            chart_horizon(dc, &hz, ngs, L"EIA working gas", CLR_ACC, 5);
        } else if (hub && hub->n >= 3) {
            hz.top = y;
            chart_horizon(dc, &hz, hub, L"HH", CLR_LINE, 5);
        }
    }
    (void)h;
}
