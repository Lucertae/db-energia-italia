#include "market.h"
#include "chart.h"
#include "data.h"
#include "dcf.h"
#include "glossary.h"

typedef struct {
    HDC dc;
    RECT net;
} NetCtx;

static void paint_network_cb(const SeriesStore *st, void *ctx) {
    NetCtx *n = (NetCtx *)ctx;
    chart_fx_network(n->dc, &n->net, st);
}

static void paint_row3(HDC dc, int x0, int y, int w3, int h2,
                       const char *a, const char *b, const char *c) {
    RECT cell;
    DataSeries snap;
    const char *ids[3];
    int i;

    ids[0] = a;
    ids[1] = b;
    ids[2] = c;
    for (i = 0; i < 3; i++) {
        cell = (RECT){ x0 + i * w3 + (i ? 2 : 0), y, x0 + (i + 1) * w3 - 2, y + h2 };
        if (data_series_snap(ids[i], &snap))
            chart_series_cell(dc, &cell, &snap);
    }
}

void market_paint(HDC dc) {
    RECT body = ui_panel_body(&g_d.data);
    RECT net, dcf, tor, wf;
    int w3, row_h, x0, y, split;
    NetCtx nctx;

    ui_frame(dc, &g_d.data, L"MARKET / DCF FEED");
    if (body.bottom - body.top < 100) return;

    w3 = (body.right - body.left) / 3;
    row_h = 42;
    x0 = body.left;
    y = body.top;

    ui_subheading(dc, &(RECT){ body.left, y, body.right, y + 12 }, L"ENERGY");
    y += 12;
    paint_row3(dc, x0, y, w3, row_h, "BRT", "WTI", "HUB");
    y += row_h + 4;
    ui_subheading(dc, &(RECT){ body.left, y, body.right, y + 12 }, L"GAS / COAL / RATES");
    y += 12;
    paint_row3(dc, x0, y, w3, row_h, "TTF", "COA", "U10");
    y += row_h + 4;
    ui_subheading(dc, &(RECT){ body.left, y, body.right, y + 12 }, L"FX");
    y += 12;
    paint_row3(dc, x0, y, w3, row_h, "USD", "JPY", "BRL");
    y += row_h + 8;

    ui_hline(dc, body.left, y, body.right, CLR_GRID);
    y += 6;

    split = (body.right - body.left) / 2;
    net = (RECT){ body.left, y, body.left + split - 4, body.bottom };
    dcf = (RECT){ body.left + split + 4, y, body.right, body.bottom };
    ui_subheading(dc, &(RECT){ net.left, net.top, net.right, net.top + 12 }, L"FX NETWORK");
    net.top += 14;
    nctx.dc = dc;
    nctx.net = net;
    data_store_read(paint_network_cb, &nctx);

    ui_subheading(dc, &(RECT){ dcf.left, dcf.top, dcf.right, dcf.top + 12 },
                  L"52W RANGE / RV ann 30d (log)");
    dcf.top += 14;
    tor = dcf;
    tor.bottom = dcf.bottom - 50;   /* reserve heading + 2 lines for CIP block */
    if (tor.bottom < tor.top + 13) tor.bottom = tor.top + 13;
    wf.top = tor.bottom + 4;
    wf.left = dcf.left;
    wf.right = dcf.right;
    wf.bottom = dcf.bottom;

    {
        static const char *RIDS[6] = { "BRT", "WTI", "HUB", "TTF", "COA", "USD" };
        DataSeries snaps[6];
        const DataSeries *list[6];
        int k, nn = 0, fit;

        fit = (tor.bottom - tor.top) / 13;
        if (fit > 6) fit = 6;
        for (k = 0; k < 6 && nn < fit; k++) {
            if (data_series_snap(RIDS[k], &snaps[nn]) && snaps[nn].n >= 10) {
                list[nn] = &snaps[nn];
                nn++;
            }
        }
        if (nn > 0)
            chart_range_vol(dc, &tor, list, nn);
    }

    {
        DataSeries usd, sof, dfr;
        wchar_t s_s[16], f3_s[16], f1_s[16], rd_s[12], rf_s[12], line[96];
        RECT lr;
        ldf spot, r_us, r_eu, f3m, f1y;

        ui_subheading(dc, &(RECT){ wf.left, wf.top, wf.right, wf.top + 12 },
                      L"CIP FORWARD EUR/USD (SOFR vs ECB DFR)");
        wf.top += 14;
        if (data_series_snap("USD", &usd) && data_series_snap("SOF", &sof) &&
            data_series_snap("EDF", &dfr) && usd.n >= 2 && sof.n >= 2 && dfr.n >= 2) {
            spot = (ldf)series_last(&usd);
            r_us = (ldf)series_last(&sof) / 100.0L;
            r_eu = (ldf)series_last(&dfr) / 100.0L;
            f3m = dcf_cip_forward(spot, r_us, r_eu, 0.25L);
            f1y = dcf_cip_forward(spot, r_us, r_eu, 1.0L);

            ui_fmt_wdouble(s_s, 16, (double)spot, 4);
            ui_fmt_wdouble(f3_s, 16, (double)f3m, 4);
            ui_fmt_wdouble(f1_s, 16, (double)f1y, 4);
            ui_fmt_wdouble(rd_s, 12, (double)(r_us * 100.0L), 2);
            ui_fmt_wdouble(rf_s, 12, (double)(r_eu * 100.0L), 2);

            lr = (RECT){ wf.left, wf.top, wf.right, wf.top + 15 };
            wsprintfW(line, L"SPOT %s   SOFR %s%%   DFR %s%%", s_s, rd_s, rf_s);
            ui_label_rect(dc, &lr, line, CLR_TXT, fSm);
            lr.top += 16;
            lr.bottom += 16;
            wsprintfW(line, L"FWD 3M %s   FWD 1Y %s", f3_s, f1_s);
            ui_label_rect(dc, &lr, line, CLR_ACC, fSm);
        } else {
            lr = (RECT){ wf.left, wf.top, wf.right, wf.top + 15 };
            ui_label_rect(dc, &lr, L"attesa serie SOFR / ECB DFR...", CLR_OFF, fSm);
        }
    }
    gloss_paint_footer(dc, &(RECT){ body.left, body.bottom - 12, body.right, body.bottom },
                       PAGE_OPS);
}
