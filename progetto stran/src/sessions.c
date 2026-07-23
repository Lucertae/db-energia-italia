#include "sessions.h"
#include "time.h"
#include "overnight.h"
#include "spine.h"

BYTE sess_asia, sess_eu, sess_us;

static BYTE mkt_open(const SYSTEMTIME *l, int h0, int m0, int h1, int m1) {
    int t = l->wHour * 60 + l->wMinute;
    int a = h0 * 60 + m0;
    int b = h1 * 60 + m1;
    return (BYTE)(t >= a && t < b);
}

void sessions_update(void) {
    BYTE a, e, u;
    BYTE ap = sess_asia, ep = sess_eu, up = sess_us;

    a = mkt_open(&time_get(I_TYO)->loc, 9, 0, 15, 0);
    e = mkt_open(&time_get(I_LON)->loc, 8, 0, 16, 30);
    u = mkt_open(&time_get(I_NYC)->loc, 9, 30, 16, 0);
    sess_asia = a;
    sess_eu = e;
    sess_us = u;
    if (a != ap || e != ep || u != up)
        InvalidateRect(g_hwnd, &g_d.alerts, FALSE);
    overnight_update();
}

void sessions_paint(HDC dc) {
    RECT body = ui_panel_body(&g_d.alerts);
    RECT line_rc;
    wchar_t buf[32];
    int y = body.top;
    const int lh = 15;

    ui_frame(dc, &g_d.alerts, L"OPS / OVERNIGHT");
    if (y + lh * 3 <= body.bottom) {
        overnight_paint(dc, body.left, y, body.right - body.left);
        y += lh * 3 + 6;
    }
    spine_paint_ops(dc, &body, &y);
    if (y + lh <= body.bottom) {
        line_rc = (RECT){ body.left, y, body.right, y + lh };
        ui_label_rect(dc, &line_rc, L"CASH SESSIONS", CLR_DIM, fLbl);
        y += lh;
    }
    if (y + lh <= body.bottom) {
        line_rc = (RECT){ body.left, y, body.right, y + lh };
        wsprintfW(buf, L"%s  ASIA", sess_asia ? L"+ OPEN" : L"- CLOSED");
        ui_label_rect(dc, &line_rc, buf, sess_asia ? CLR_ON : CLR_OFF, fLbl);
        y += lh;
    }
    if (y + lh <= body.bottom) {
        line_rc.top = y; line_rc.bottom = y + lh;
        wsprintfW(buf, L"%s  EUROPE", sess_eu ? L"+ OPEN" : L"- CLOSED");
        ui_label_rect(dc, &line_rc, buf, sess_eu ? CLR_ON : CLR_OFF, fLbl);
        y += lh;
    }
    if (y + lh <= body.bottom) {
        line_rc.top = y; line_rc.bottom = y + lh;
        wsprintfW(buf, L"%s  US", sess_us ? L"+ OPEN" : L"- CLOSED");
        ui_label_rect(dc, &line_rc, buf, sess_us ? CLR_ON : CLR_OFF, fLbl);
        y += lh;
    }
    if (y + lh <= body.bottom) {
        line_rc.top = y; line_rc.bottom = y + lh;
        ui_label_rect(dc, &line_rc, L"TYO 09-15  LON 08-16:30  NYC 09:30-16", CLR_DIM, fLbl);
    }
}
