#include "ops.h"
#include "chart.h"
#include "spine.h"
#include "modules.h"
#include "chokepoints.h"
#include "intel.h"
#include "time.h"

static void paint_alert_band(HDC dc, RECT *r) {
    int i, y = r->top, lh = 13;
    ui_subheading(dc, &(RECT){ r->left, y, r->right, y + 12 }, L"ALERT attivi");
    y += 14;
    if (spine_live_count() == 0) {
        SetTextColor(dc, CLR_OFF);
        SelectObject(dc, fSm);
        TextOutW(dc, r->left, y, L"(nessun alert live — monitor MET wind-delta e gate ENTSO-E)", -1);
        y += lh;
    } else {
        for (i = 0; i < spine_live_count() && y + lh <= r->bottom; i++) {
            const SpineLive *lv = spine_live_get(i);
            wchar_t msgw[120], line[200];
            MultiByteToWideChar(CP_UTF8, 0, lv->msg, -1, msgw, 120);
            wsprintfW(line, L"%hs | %ls | live | drill:MET/LAB", lv->id, msgw);
            SetTextColor(dc, lv->alert ? CLR_DN : CLR_DIM);
            SelectObject(dc, fSm);
            TextOutW(dc, r->left, y, line, lstrlenW(line));
            y += lh;
        }
    }
    r->top = y + 4;
}

static void paint_spine_tail(HDC dc, RECT *r) {
    int i, y = r->top, lh = 13;
    const char *brief = modules_brief();

    if (brief && brief[0]) {
        wchar_t bw[120];
        ui_subheading(dc, &(RECT){ r->left, y, r->right, y + 12 }, L"SPINE brief");
        y += 14;
        MultiByteToWideChar(CP_UTF8, 0, brief, -1, bw, 120);
        SetTextColor(dc, CLR_DIM);
        SelectObject(dc, fSm);
        TextOutW(dc, r->left, y, bw, lstrlenW(bw));
        y += lh + 4;
    }

    if (spine_signal_count() > 0) {
        ui_subheading(dc, &(RECT){ r->left, y, r->right, y + 12 }, L"SEGNALI spine");
        y += 14;
        for (i = 0; i < spine_signal_count() && y + lh <= r->bottom; i++) {
            const SpineSignal *s = spine_signal_get(i);
            wchar_t line[160], titlew[100];
            MultiByteToWideChar(CP_UTF8, 0, s->title, -1, titlew, 100);
            wsprintfW(line, L"%hs [%hs] %.55ls", s->id, s->status, titlew);
            SetTextColor(dc, lstrcmpiA(s->status, "active") == 0 ? CLR_ACC : CLR_OFF);
            SelectObject(dc, fSm);
            TextOutW(dc, r->left, y, line, lstrlenW(line));
            y += lh;
        }
    }
    r->top = y;
}

static void paint_horizon_flash(HDC dc, RECT *r, const SeriesStore *st) {
    static const struct { const char *id; const wchar_t *lbl; } HS[] = {
        { "BRT", L"BRT" }, { "TTF", L"TTF" }, { "NGF", L"PWR DE" },
        { "EUA", L"EUA" }, { "EUF", L"EUR/USD" }, { "DXY", L"DXY" },
        { "VIX", L"VIX" }, { "BTC", L"BTC" }
    };
    int i, cols = 2, cw, ch, y0 = r->top;
    ui_subheading(dc, &(RECT){ r->left, y0, r->right, y0 + 12 }, L"MERCATO flash (horizon)");
    y0 += 14;
    cw = (r->right - r->left) / cols;
    ch = (r->bottom - y0) / 4;
    for (i = 0; i < 8; i++) {
        RECT cell;
        const DataSeries *s = series_get((SeriesStore *)st, HS[i].id);
        cell.left = r->left + (i % cols) * cw;
        cell.right = cell.left + cw - 4;
        cell.top = y0 + (i / cols) * ch;
        cell.bottom = cell.top + ch - 2;
        if (s && s->n >= 2)
            chart_horizon(dc, &cell, s, HS[i].lbl, CLR_LINE, 5);
        else
            ui_label_rect(dc, &cell, HS[i].lbl, CLR_OFF, fSm);
    }
}

static void paint_sessions_compact(HDC dc, RECT *r) {
    static const int HUBS[] = { 0, 5, 1, 13, 8, 6, 12, 14 };
    int i, y = r->top, lh = 13;
    ui_subheading(dc, &(RECT){ r->left, y, r->right, y + 12 }, L"SESSIONI 8 hub");
    y += 14;
    for (i = 0; i < 8 && y + lh <= r->bottom; i++) {
        const Clock *c = time_get(HUBS[i]);
        wchar_t line[40];
        if (!c) continue;
        wsprintfW(line, L"%s %s  %s", c->abbr, c->t, c->sun_s ? L"OPEN" : L"closed");
        SetTextColor(dc, c->sun_s ? CLR_ON : CLR_DIM);
        SelectObject(dc, fSm);
        TextOutW(dc, r->left, y, line, lstrlenW(line));
        y += lh;
    }
}

static void paint_brief(HDC dc, RECT *r) {
    wchar_t line[200], cp[140];
    int y = r->top, lh = 13;
    SYSTEMTIME utc, cet;
    int mins_gate;
    RECT tick;

    ui_subheading(dc, &(RECT){ r->left, y, r->right, y + 12 }, L"BRIEF operativo");
    y += 14;
    chokepoints_brief(cp, 140);
    if (cp[0]) {
        SetTextColor(dc, CLR_ACC);
        SelectObject(dc, fSm);
        TextOutW(dc, r->left, y, cp, lstrlenW(cp));
        y += lh;
    }
    GetSystemTime(&utc);
    cet = utc;
    {
        FILETIME ft;
        ULARGE_INTEGER uli;
        SystemTimeToFileTime(&utc, &ft);
        uli.LowPart = ft.dwLowDateTime;
        uli.HighPart = ft.dwHighDateTime;
        uli.QuadPart += (ULONGLONG)2 * 3600 * 10000000ULL;
        ft.dwLowDateTime = uli.LowPart;
        ft.dwHighDateTime = uli.HighPart;
        FileTimeToSystemTime(&ft, &cet);
    }
    mins_gate = (12 - cet.wHour) * 60 - cet.wMinute;
    if (mins_gate < 0) mins_gate += 24 * 60;
    wsprintfW(line, L"ENTSO-E DA gate D-1 12:00 CET  T-%02d:%02d  (riga ops power desk)",
              mins_gate / 60, mins_gate % 60);
    SetTextColor(dc, mins_gate < 120 ? CLR_DN : CLR_TXT);
    TextOutW(dc, r->left, y, line, lstrlenW(line));
    y += lh;
    {
        int ok, st, miss;
        spine_get_summary(&ok, &st, &miss);
        wsprintfW(line, L"SPINE ok %d stale %d miss %d", ok, st, miss);
        SetTextColor(dc, st || miss ? RGB(255, 180, 80) : CLR_UP);
        TextOutW(dc, r->left, y, line, lstrlenW(line));
        y += lh;
    }
    SetTextColor(dc, CLR_DIM);
    TextOutW(dc, r->left, y,
             L"POV: apri NRG se gate<2h, MET se wind-delta alert, LAB per verdict PWR-01",
             -1);
    y += lh;
    {
        const EnsoSnap *e = modules_enso();
        if (e && e->phase[0]) {
            wsprintfW(line, L"Macro meteo: ONI=%.2f %hs (FRED/ENSO bridge)", e->oni, e->phase);
            SetTextColor(dc, CLR_OFF);
            TextOutW(dc, r->left, y, line, lstrlenW(line));
            y += lh;
        }
    }
    if (y + 14 < r->bottom) {
        tick = *r;
        tick.top = y + 4;
        ui_subheading(dc, &tick, L"NRG/SEA headlines");
        tick.top += 14;
        intel_paint_ticker(dc, &tick, "ENERGY", 3);
    }
}

static void paint_live_events(HDC dc, RECT *r) {
    if (r->bottom <= r->top + 20) return;
    ui_subheading(dc, &(RECT){ r->left, r->top, r->right, r->top + 12 }, L"LIVE quake/disaster/met");
    r->top += 14;
    intel_paint_events(dc, r, 3);
    r->top += 4;
}

void ops_paint(HDC dc, const RECT *rc, const SeriesStore *st) {
    RECT r = *rc, alert, left, mid, right, sess, brief, spine_top, spine_bot;
    int w = r.right - r.left;
    int mod_n = modules_count();

    (void)mod_n;

    alert = r;
    alert.bottom = r.top + 68;
    paint_alert_band(dc, &alert);

    left = r;
    left.top = alert.bottom;
    left.right = r.left + w * 28 / 100;
    mid = r;
    mid.top = alert.bottom;
    mid.left = left.right + 8;
    mid.right = r.right - w * 26 / 100;
    right = r;
    right.top = alert.bottom;
    right.left = mid.right + 8;

    sess = right;
    sess.bottom = right.top + (right.bottom - right.top) * 42 / 100;
    brief = right;
    brief.top = sess.bottom + 6;

    spine_top = left;
    spine_top.bottom = left.top + (left.bottom - left.top) * 52 / 100;
    spine_bot = left;
    spine_bot.top = spine_top.bottom + 4;

    modules_paint_spine_grid(dc, &spine_top);
    paint_spine_tail(dc, &spine_bot);
    paint_live_events(dc, &spine_bot);
    paint_horizon_flash(dc, &mid, st);
    paint_sessions_compact(dc, &sess);
    paint_brief(dc, &brief);
}
