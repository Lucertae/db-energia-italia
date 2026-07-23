#include "solar.h"
#include "time.h"
#include "data.h"

int solar_days, solar_nights;
wchar_t solar_footer[96];
wchar_t solar_hub[3][48];

static void hub_line(int idx, wchar_t *buf) {
    Clock *c = time_get(idx);

    if (c->sun_s == 1) {
        wsprintfW(buf, L"%s  %02u:%02u-%02u:%02u",
            c->abbr, c->rise.wHour, c->rise.wMinute, c->set.wHour, c->set.wMinute);
    } else if (c->sun_s == 2) {
        wsprintfW(buf, L"%s  luce polare", c->abbr);
    } else if (c->sun_s == 3) {
        wsprintfW(buf, L"%s  buio polare", c->abbr);
    } else {
        wsprintfW(buf, L"%s  solare n/d", c->abbr);
    }
}

static void build_footer(void) {
    int best = 0, bestd = 100000, now, d, r, s;
    Clock *c;

    for (int i = 0; i < CLOCK_N; i++) {
        if (time_get(i)->sun_s != 1) continue;
        c = time_get(i);
        now = c->loc.wHour * 3600 + c->loc.wMinute * 60 + c->loc.wSecond;
        r = c->rise.wHour * 3600 + c->rise.wMinute * 60;
        s = c->set.wHour * 3600 + c->set.wMinute * 60;
        d = c->day ? (s - now) : (r - now);
        if (d <= 0) d += 86400;
        if (d < bestd) { bestd = d; best = i; }
    }
    c = time_get(best);
    if (c->sun_s == 1) {
        wsprintfW(solar_footer, L"NEXT %s %s in %02u:%02u",
            c->abbr, c->day ? L"TRAMONTO" : L"ALBA", bestd / 3600, (bestd % 3600) / 60);
    } else {
        lstrcpyW(solar_footer, L"NEXT solar event: n/d");
    }
}

void solar_update(void) {
    int d = 0, n = 0;
    static int last_days, last_nights;
    static WORD last_utc_day;

    for (int i = 0; i < CLOCK_N; i++) {
        if (time_get(i)->day) d++; else n++;
    }
    solar_days = d;
    solar_nights = n;
    hub_line(I_LON, solar_hub[0]);
    hub_line(I_NYC, solar_hub[1]);
    hub_line(I_TYO, solar_hub[2]);
    build_footer();

    if (d != last_days || n != last_nights ||
        time_get(I_UTC)->loc.wDay != last_utc_day) {
        last_days = d;
        last_nights = n;
        last_utc_day = time_get(I_UTC)->loc.wDay;
        InvalidateRect(g_hwnd, &g_d.solar, FALSE);
        InvalidateRect(g_hwnd, &g_d.footer, FALSE);
    }
}

void solar_paint(HDC dc) {
    RECT body = ui_panel_body(&g_d.solar);
    RECT line_rc;
    int y = body.top;
    wchar_t buf[64];
    const int lh = 15;

    ui_frame(dc, &g_d.solar, L"DAYLIGHT / SOLAR");
    SelectObject(dc, fLbl);
    line_rc = (RECT){ body.left, y, body.right, y + lh };
    wsprintfW(buf, L"AMERICAS  %d/5 day", time_region_days(1, 4));
    if (y + lh <= body.bottom) {
        ui_label_rect(dc, &line_rc, buf, CLR_TXT, fLbl);
    }
    y += lh;
    if (y + lh <= body.bottom) {
        line_rc.top = y; line_rc.bottom = y + lh;
        wsprintfW(buf, L"EU / MEA  %d/5 day", time_region_days(5, 9));
        ui_label_rect(dc, &line_rc, buf, CLR_TXT, fLbl);
    }
    y += lh;
    if (y + lh <= body.bottom) {
        line_rc.top = y; line_rc.bottom = y + lh;
        wsprintfW(buf, L"APAC      %d/5 day", time_region_days(10, 14));
        ui_label_rect(dc, &line_rc, buf, CLR_TXT, fLbl);
    }
    y += lh + 4;
    if (y + lh <= body.bottom) {
        line_rc.top = y; line_rc.bottom = y + lh;
        ui_label_rect(dc, &line_rc, L"HUB SOLAR", CLR_DIM, fLbl);
    }
    y += lh;
    for (int i = 0; i < 3; i++) {
        if (y + lh > body.bottom) break;
        line_rc.top = y; line_rc.bottom = y + lh;
        ui_label_rect(dc, &line_rc, solar_hub[i], CLR_ACC, fLbl);
        y += lh;
    }
    if (y + lh <= body.bottom) {
        line_rc.top = y; line_rc.bottom = y + lh;
        wsprintfW(buf, L"GLOBAL  %d day / %d night", solar_days, solar_nights);
        ui_label_rect(dc, &line_rc, buf, CLR_DIM, fLbl);
        y += lh;
    }
    if (y + lh + 4 <= body.bottom) {
        y += 4;
        data_paint_lines(dc, body.left, y, body.right - body.left, body.bottom);
    }
}

void solar_paint_footer(HDC dc) {
    RECT left, right;

    ui_frame(dc, &g_d.footer, L"TELEMETRY");
    left = (RECT){
        g_d.footer.left + PAD + 8, g_d.footer.top + 10,
        (g_d.footer.left + g_d.footer.right) / 2 - 8, g_d.footer.bottom - 4
    };
    right = (RECT){
        left.right + 8, left.top,
        g_d.footer.right - PAD, g_d.footer.bottom - 4
    };
    ui_label_rect(dc, &left, solar_footer, CLR_ACC, fMono);
    data_paint_footer(dc, &right);
}
