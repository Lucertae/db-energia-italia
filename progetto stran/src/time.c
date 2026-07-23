#include "time.h"
#include "astro.h"
#include <math.h>

typedef DWORD (WINAPI *EnumTzFn)(DWORD, PDYNAMIC_TIME_ZONE_INFORMATION);
typedef BOOL  (WINAPI *ToLocFn)(const DYNAMIC_TIME_ZONE_INFORMATION *, const SYSTEMTIME *, SYSTEMTIME *);

static EnumTzFn pEnumTz;
static ToLocFn pToLoc;
static DYNAMIC_TIME_ZONE_INFORMATION TZ[MAX_TZ];
static DWORD tz_n;
static wchar_t g_local_t[9];
static wchar_t g_local_lbl[20];

static Clock C[CLOCK_N] = {
    { L"UTC",          L"UTC", L"UTC",                            51.4778,    0.0 },
    { L"New York",     L"NYC",  L"Eastern Standard Time",          40.7128,  -74.0060 },
    { L"Chicago",      L"CHI",  L"Central Standard Time",          41.8781,  -87.6298 },
    { L"Los Angeles",  L"LAX",  L"Pacific Standard Time",          34.0522, -118.2437 },
    { L"Sao Paulo",    L"SAO",  L"E. South America Standard Time", -23.5505, -46.6333 },
    { L"London",       L"LON",  L"GMT Standard Time",              51.5074,   -0.1278 },
    { L"Paris",        L"PAR",  L"W. Europe Standard Time",        48.8566,    2.3522 },
    { L"Moscow",       L"MOW",  L"Russian Standard Time",        55.7558,   37.6173 },
    { L"Dubai",        L"DXB",  L"Arabian Standard Time",          25.2048,   55.2708 },
    { L"Johannesburg", L"JNB",  L"South Africa Standard Time",    -26.2041,   28.0473 },
    { L"Mumbai",       L"BOM",  L"India Standard Time",            19.0760,   72.8777 },
    { L"Singapore",    L"SIN",  L"Singapore Standard Time",         1.3521,  103.8198 },
    { L"Hong Kong",    L"HKG",  L"China Standard Time",            22.3193,  114.1694 },
    { L"Tokyo",        L"TYO",  L"Tokyo Standard Time",            35.6762,  139.6503 },
    { L"Sydney",       L"SYD",  L"AUS Eastern Standard Time",     -33.8688,  151.2093 },
};

static void fmt_hms(wchar_t *b, const SYSTEMTIME *s) {
    F2(b, 0, s->wHour); b[2] = L':';
    F2(b, 3, s->wMinute); b[5] = L':';
    F2(b, 6, s->wSecond); b[8] = 0;
}

static void refresh_local(void) {
    SYSTEMTIME st;
    DYNAMIC_TIME_ZONE_INFORMATION dtz;
    TIME_ZONE_INFORMATION tzi;
    DWORD tz_id;
    int bias, off;

    GetLocalTime(&st);
    fmt_hms(g_local_t, &st);
    GetDynamicTimeZoneInformation(&dtz);
    bias = dtz.Bias;
    tz_id = GetTimeZoneInformation(&tzi);
    if (tz_id == TIME_ZONE_ID_DAYLIGHT)
        bias += dtz.DaylightBias;
    off = -bias;
    if (off % 60 == 0)
        wsprintfW(g_local_lbl, L"LOCAL %+d", off / 60);
    else
        wsprintfW(g_local_lbl, L"LOCAL %+d:%02d", off / 60, abs(off % 60));
}

static void bind_tz(void) {
    while (tz_n < MAX_TZ && pEnumTz(tz_n, &TZ[tz_n]) == ERROR_SUCCESS) tz_n++;
    for (int i = 0; i < CLOCK_N; i++) {
        for (DWORD j = 0; j < tz_n; j++) {
            if (_wcsicmp(TZ[j].TimeZoneKeyName, C[i].tz_id) == 0) {
                C[i].tz = TZ[j];
                C[i].ok = 1;
                break;
            }
        }
    }
}

void time_calc_sun(Clock *c, const SYSTEMTIME *loc) {
    SYSTEMTIME noon = *loc, utc, ur, us;
    double jd, lw, phi, d, n, ds, M, L, dec, ca, w, Jn, Js;

    c->sun_s = 0;
    if (!c->ok) return;
    noon.wHour = 12;
    noon.wMinute = noon.wSecond = noon.wMilliseconds = 0;
    if (!TzSpecificLocalTimeToSystemTime((const TIME_ZONE_INFORMATION *)&c->tz, &noon, &utc)) return;
    if (!astro_jd_from_utc(&utc, &jd)) return;

    lw = RAD * (-c->lon);
    phi = RAD * c->lat;
    d = jd - 2451545.0 + 0.0008 - lw / (2.0 * PI);
    n = round(d - 0.0009);
    ds = 0.0009 + lw / (2.0 * PI) + n;
    M = RAD * (357.5291 + 0.98560028 * ds);
    L = M + PI + RAD * (1.9148 * sin(M) + 0.02 * sin(2 * M) + 0.0003 * sin(3 * M) + 102.9372);
    dec = asin(sin(L) * sin(RAD * 23.4397));
    ca = (sin(RAD * -0.833) - sin(phi) * sin(dec)) / (cos(phi) * cos(dec));
    if (ca > 1.0) { c->sun_s = 3; return; }
    if (ca < -1.0) { c->sun_s = 2; return; }
    w = acos(ca);
    Jn = 2451545.0 + ds + 0.0053 * sin(M) - 0.0069 * sin(2 * L);
    Js = 2451545.0 + 0.0009 + (w + lw) / (2.0 * PI) + n + 0.0053 * sin(M) - 0.0069 * sin(2 * L);
    if (!astro_utc_from_jd(Jn - (Js - Jn), &ur) || !astro_utc_from_jd(Js, &us)) return;
    if (!pToLoc(&c->tz, &ur, &c->rise) || !pToLoc(&c->tz, &us, &c->set)) return;
    c->sun_s = 1;
}

static BYTE is_day(const SYSTEMTIME *n, const Clock *c) {
    int t, r, s;

    if (!c->sun_s) return 0;
    if (c->sun_s == 2) return 1;
    if (c->sun_s == 3) return 0;
    t = n->wHour * 3600 + n->wMinute * 60 + n->wSecond;
    r = c->rise.wHour * 3600 + c->rise.wMinute * 60;
    s = c->set.wHour * 3600 + c->set.wMinute * 60;
    return (BYTE)(t >= r && t < s);
}

BOOL time_init(void) {
    pEnumTz = (EnumTzFn)GetProcAddress(LoadLibraryW(L"kernelbase.dll"), "EnumDynamicTimeZoneInformation");
    pToLoc = (ToLocFn)GetProcAddress(GetModuleHandleW(L"kernelbase.dll"), "SystemTimeToTzSpecificLocalTimeEx");
    if (!pEnumTz || !pToLoc) return FALSE;
    bind_tz();
    return TRUE;
}

void time_layout_rows(void) {
    int body_top = g_d.time.top;
    int body_bot = g_d.time.bottom;
    int usable = body_bot - body_top - TITLE_H - PAD * 2;
    int row_h = usable / CLOCK_N;
    int y0;

    if (row_h < 14) row_h = 14;
    y0 = body_top + TITLE_H + PAD;
    for (int i = 0; i < CLOCK_N; i++) {
        C[i].row.left = PAD + 2;
        C[i].row.top = y0 + i * row_h;
        C[i].row.right = g_d.time_w - PAD;
        C[i].row.bottom = y0 + (i + 1) * row_h - 2;
    }
}

void time_update(const SYSTEMTIME *utc) {
    refresh_local();
    for (int i = 0; i < CLOCK_N; i++) {
        Clock *c = &C[i];

        if (!c->ok || !pToLoc(&c->tz, utc, &c->loc)) {
            lstrcpyW(c->t, L"--:--:--");
            InvalidateRect(g_hwnd, &c->row, FALSE);
            continue;
        }
        fmt_hms(c->t, &c->loc);
        if (c->loc.wYear != c->dy || c->loc.wMonth != c->dm || c->loc.wDay != c->dd) {
            c->dy = c->loc.wYear;
            c->dm = c->loc.wMonth;
            c->dd = c->loc.wDay;
            time_calc_sun(c, &c->loc);
            InvalidateRect(g_hwnd, &g_d.solar, FALSE);
            InvalidateRect(g_hwnd, &g_d.footer, FALSE);
        }
        c->day = is_day(&c->loc, c);
        InvalidateRect(g_hwnd, &c->row, FALSE);
    }
}

Clock *time_get(int i) {
    return &C[i];
}

int time_region_days(int a, int b) {
    int d = 0;
    for (int i = a; i <= b; i++) if (C[i].day) d++;
    return d;
}

const wchar_t *time_utc_hms(void) {
    return C[I_UTC].t;
}

const wchar_t *time_local_hms(void) {
    return g_local_t;
}

const wchar_t *time_local_lbl(void) {
    return g_local_lbl;
}

void time_paint_header(HDC dc) {
    RECT live_rc;
    int x, tw, lw;

    ui_frame(dc, &g_d.hdr, L"OPS DESK");
    x = PAD + 8 + ui_text_w(dc, fLbl, L"OPS DESK") + 20;

    SelectObject(dc, fBig);
    ui_label(dc, x, 10, time_local_hms(), CLR_ACC);
    tw = ui_text_w(dc, fBig, time_local_hms());
    SelectObject(dc, fLbl);
    ui_label(dc, x + tw + 8, 14, time_local_lbl(), CLR_DIM);
    lw = ui_text_w(dc, fLbl, time_local_lbl());
    x += tw + lw + 28;

    SelectObject(dc, fBig);
    ui_label(dc, x, 10, time_utc_hms(), CLR_DIM);
    tw = ui_text_w(dc, fBig, time_utc_hms());
    SelectObject(dc, fLbl);
    ui_label(dc, x + tw + 8, 14, L"UTC", CLR_DIM);

    live_rc = (RECT){ x + tw + 48, 8, g_sw - PAD, HDR_H - 6 };
    ui_label_rect(dc, &live_rc, g_res, CLR_DIM, fLbl);
}

void time_paint_panel(HDC dc) {
    wchar_t line[24];
    RECT body = ui_panel_body(&g_d.time);
    RECT line_rc;

    ui_frame(dc, &g_d.time, L"TIME");
    SelectObject(dc, fMono);
    SetBkMode(dc, TRANSPARENT);
    for (int i = 0; i < CLOCK_N; i++) {
        const Clock *c = &C[i];
        if (c->row.top >= body.bottom) break;

        line_rc = c->row;
        if (line_rc.bottom > body.bottom) line_rc.bottom = body.bottom;
        SetTextColor(dc, c->day ? CLR_ON : CLR_DIM);
        TextOutW(dc, line_rc.left, line_rc.top + 1, c->day ? L"+" : L"-", 1);
        wsprintfW(line, L"%-3s %s", c->abbr, c->t);
        line_rc.left += 12;
        ui_label_rect(dc, &line_rc, line, CLR_TXT, fMono);
    }
}
