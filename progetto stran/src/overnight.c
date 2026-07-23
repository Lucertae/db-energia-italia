#include "overnight.h"
#include "sessions.h"
#include "time.h"

OvernightState g_ovn;

static int mins_to_open(const SYSTEMTIME *loc, int h0, int m0, int h1, int m1) {
    int now = loc->wHour * 60 + loc->wMinute;
    int open = h0 * 60 + m0;
    int close = h1 * 60 + m1;

    if (now >= open && now < close) return 0;
    if (now < open) return open - now;
    return 24 * 60 - now + open;
}

void overnight_update(void) {
    OvernightState *o = &g_ovn;
    Clock *tyo = time_get(I_TYO);
    Clock *lon = time_get(I_LON);
    Clock *nyc = time_get(I_NYC);
    int d_tyo, d_lon, d_nyc, best;
    const wchar_t *best_hub;
    static wchar_t last_phase[40];

    o->asia_open = sess_asia;
    o->eu_open = sess_eu;
    o->us_open = sess_us;
    o->us_overnight = (BYTE)(!sess_us);

    if (sess_us)
        lstrcpyW(o->phase, L"US RTH");
    else if (sess_asia && !sess_eu && !sess_us)
        lstrcpyW(o->phase, L"ASIA CASH");
    else if (sess_eu && !sess_us)
        lstrcpyW(o->phase, L"EU CASH");
    else if (!sess_us && !sess_asia && !sess_eu)
        lstrcpyW(o->phase, L"US OVERNIGHT drift");
    else
        lstrcpyW(o->phase, L"MIXED / handoff");

    d_tyo = mins_to_open(&tyo->loc, 9, 0, 15, 0);
    d_lon = mins_to_open(&lon->loc, 8, 0, 16, 30);
    d_nyc = mins_to_open(&nyc->loc, 9, 30, 16, 0);
    best = d_tyo;
    best_hub = L"TYO";
    if (d_lon > 0 && (best == 0 || d_lon < best)) { best = d_lon; best_hub = L"LON"; }
    if (d_nyc > 0 && (best == 0 || d_nyc < best)) { best = d_nyc; best_hub = L"NYC"; }

    if (best > 0)
        wsprintfW(o->next_open, L"NEXT %s open %uh%02u", best_hub, best / 60, best % 60);
    else
        lstrcpyW(o->next_open, L"ALL MAJOR CASH OPEN");

    if (o->us_overnight && !sess_asia && !sess_eu)
        lstrcpyW(o->pricer, L"PRICING: US futures / FX");
    else if (o->us_overnight && sess_asia)
        lstrcpyW(o->pricer, L"PRICING: Asia cash + US fut");
    else if (sess_eu && !sess_us)
        lstrcpyW(o->pricer, L"PRICING: EU cash + US fut");
    else if (sess_us)
        lstrcpyW(o->pricer, L"PRICING: US cash RTH");
    else
        lstrcpyW(o->pricer, L"PRICING: global handoff");

    if (lstrcmpW(o->phase, last_phase) != 0) {
        lstrcpyW(last_phase, o->phase);
        InvalidateRect(g_hwnd, &g_d.alerts, FALSE);
    }
}

void overnight_paint(HDC dc, int x, int y, int w) {
    RECT rc;
    const int lh = 15;

    rc = (RECT){ x, y, x + w, y + lh };
    ui_label_rect(dc, &rc, g_ovn.phase, g_ovn.us_overnight ? CLR_ACC : CLR_TXT, fLbl);
    y += lh;
    rc.top = y; rc.bottom = y + lh;
    ui_label_rect(dc, &rc, g_ovn.next_open, CLR_DIM, fLbl);
    y += lh;
    rc.top = y; rc.bottom = y + lh;
    ui_label_rect(dc, &rc, g_ovn.pricer, CLR_DIM, fLbl);
}
