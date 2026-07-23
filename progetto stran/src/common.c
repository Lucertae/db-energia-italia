#include "common.h"
#include "time.h"
#include <stdio.h>

HWND g_hwnd;
Desk g_d;
int g_sw, g_sh;
wchar_t g_res[32];

HFONT fLbl, fMono, fBig, fSm;
HBRUSH bBg, bPanel, bWhite, bGray, bBand, bMoonLit, bMoonShade;
HPEN pLine, pMoonRim;

static wchar_t g_desk_root[MAX_PATH];

void desk_chdir_exe(void) {
    wchar_t path[MAX_PATH];
    wchar_t *slash;

    if (!GetModuleFileNameW(NULL, path, MAX_PATH)) return;
    slash = wcsrchr(path, L'\\');
    if (slash) *slash = 0;
    lstrcpynW(g_desk_root, path, MAX_PATH);
    SetCurrentDirectoryW(g_desk_root);
}

BOOL desk_spawn_python(const wchar_t *rel_script) {
    wchar_t script[MAX_PATH];
    wchar_t cmd[900];
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;

    if (!rel_script || !rel_script[0] || !g_desk_root[0]) return FALSE;
    wsprintfW(script, L"%s\\%s", g_desk_root, rel_script);
    wsprintfW(cmd, L"cmd.exe /c python \"%s\"", script);
    memset(&si, 0, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    memset(&pi, 0, sizeof(pi));
    if (!CreateProcessW(NULL, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, g_desk_root, &si, &pi))
        return FALSE;
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return TRUE;
}

void ui_init(void) {
    fLbl  = CreateFontW(-15, 0, 0, 0, FW_NORMAL, 0, 0, 0, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Consolas");
    fMono = CreateFontW(-14, 0, 0, 0, FW_NORMAL, 0, 0, 0, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Consolas");
    fBig  = CreateFontW(-22, 0, 0, 0, FW_NORMAL, 0, 0, 0, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Consolas");
    fSm   = CreateFontW(-12, 0, 0, 0, FW_NORMAL, 0, 0, 0, DEFAULT_CHARSET, 0, 0, CLEARTYPE_QUALITY, 0, L"Consolas");
    bBg   = CreateSolidBrush(CLR_BG);
    bPanel= CreateSolidBrush(CLR_PANEL);
    bWhite= CreateSolidBrush(RGB(255, 255, 255));
    bGray = CreateSolidBrush(RGB(80, 80, 80));
    bBand = CreateSolidBrush(CLR_BAND);
    bMoonLit   = CreateSolidBrush(CLR_MOON_LIT);
    bMoonShade = CreateSolidBrush(CLR_MOON_SHADE);
    pLine = CreatePen(PS_SOLID, 1, CLR_LINE);
    pMoonRim = CreatePen(PS_SOLID, 1, CLR_MOON_RIM);
}

void ui_free(void) {
    DeleteObject(fLbl);
    DeleteObject(fMono);
    DeleteObject(fBig);
    DeleteObject(fSm);
    DeleteObject(bBg);
    DeleteObject(bPanel);
    DeleteObject(bWhite);
    DeleteObject(bGray);
    DeleteObject(bBand);
    DeleteObject(bMoonLit);
    DeleteObject(bMoonShade);
    DeleteObject(pLine);
    DeleteObject(pMoonRim);
}

void ui_fill(HDC dc, const RECT *rc, HBRUSH b) {
    FillRect(dc, rc, b);
}

void ui_frame(HDC dc, const RECT *rc, const wchar_t *lbl) {
    ui_fill(dc, rc, bPanel);
    SelectObject(dc, pLine);
    SelectObject(dc, GetStockObject(NULL_BRUSH));
    Rectangle(dc, rc->left, rc->top, rc->right - 1, rc->bottom - 1);
    SetTextColor(dc, CLR_DIM);
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fLbl);
    TextOutW(dc, rc->left + PAD + 4, rc->top + 4, lbl, lstrlenW(lbl));
}

void ui_label(HDC dc, int x, int y, const wchar_t *s, COLORREF c) {
    SetTextColor(dc, c);
    TextOutW(dc, x, y, s, lstrlenW(s));
}

int ui_text_w(HDC dc, HFONT font, const wchar_t *s) {
    SIZE sz;
    HFONT old = (HFONT)SelectObject(dc, font);
    GetTextExtentPoint32W(dc, s, lstrlenW(s), &sz);
    SelectObject(dc, old);
    return sz.cx;
}

void ui_label_rect(HDC dc, const RECT *rc, const wchar_t *s, COLORREF c, HFONT font) {
    RECT r = *rc;
    HFONT old = (HFONT)SelectObject(dc, font);
    SetTextColor(dc, c);
    SetBkMode(dc, TRANSPARENT);
    DrawTextW(dc, (wchar_t *)s, -1, &r, DT_LEFT | DT_SINGLELINE | DT_END_ELLIPSIS | DT_NOPREFIX);
    SelectObject(dc, old);
}

void ui_fmt_wdouble(wchar_t *out, int out_len, double v, int decimals) {
    char buf[48];
    const char *fmt;

    if (!out || out_len <= 0) return;
    switch (decimals) {
    case 0: fmt = "%.0f"; break;
    case 1: fmt = "%.1f"; break;
    case 3: fmt = "%.3f"; break;
    case 4: fmt = "%.4f"; break;
    default: fmt = "%.2f"; break;
    }
    sprintf(buf, fmt, v);
    MultiByteToWideChar(CP_UTF8, 0, buf, -1, out, out_len);
}

void ui_subheading(HDC dc, const RECT *rc, const wchar_t *title) {
    RECT r = *rc;
    SetTextColor(dc, CLR_DIM);
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    DrawTextW(dc, (wchar_t *)title, -1, &r, DT_LEFT | DT_SINGLELINE | DT_NOPREFIX);
}

void ui_hline(HDC dc, int x0, int y, int x1, COLORREF c) {
    HPEN pen = CreatePen(PS_SOLID, 1, c);
    HPEN old = (HPEN)SelectObject(dc, pen);
    MoveToEx(dc, x0, y, NULL);
    LineTo(dc, x1, y);
    SelectObject(dc, old);
    DeleteObject(pen);
}

RECT ui_panel_body(const RECT *p) {
    RECT b = {
        p->left + PAD,
        p->top + TITLE_H + PAD,
        p->right - PAD,
        p->bottom - PAD
    };
    return b;
}

COLORREF ui_stale_color(int age_h) {
    if (age_h < 0) return CLR_DIM;
    if (age_h < 1) return CLR_UP;
    if (age_h < 24) return RGB(255, 180, 80);
    return CLR_DN;
}

void ui_stale_dot(HDC dc, int x, int y, int age_h) {
    HBRUSH br = CreateSolidBrush(ui_stale_color(age_h));
    HBRUSH old = (HBRUSH)SelectObject(dc, br);
    Ellipse(dc, x, y, x + 6, y + 6);
    SelectObject(dc, old);
    DeleteObject(br);
}

void desk_layout(HWND w) {
    RECT r;
    int body_top, body_bot, body_h, solar_h, cx0, cx1;

    GetClientRect(w, &r);
    g_sw = r.right;
    g_sh = r.bottom;
    g_d.time_w = g_sw * 17 / 100;
    g_d.alt_w = g_sw * 19 / 100;
    cx0 = g_d.time_w + GAP;
    cx1 = g_sw - g_d.alt_w;

    g_d.hdr = (RECT){ 0, 0, g_sw, HDR_H };
    g_d.footer = (RECT){ 0, g_sh - FTR_H, g_sw, g_sh };
    body_top = HDR_H + GAP;
    body_bot = g_sh - FTR_H - GAP;
    body_h = body_bot - body_top;

    g_d.time = (RECT){ 0, body_top, g_d.time_w, body_bot };
    g_d.alerts = (RECT){ cx1 + GAP, body_top, g_sw, body_bot };

    solar_h = body_h * 28 / 100;
    if (solar_h < 130) solar_h = 130;

    g_d.solar = (RECT){ cx0, body_top, cx1, body_top + solar_h };
    g_d.data = (RECT){ cx0, g_d.solar.bottom + GAP, cx1, body_bot };

    g_d.moon_icon = (RECT){ g_sw - 188, (HDR_H - 30) / 2, g_sw - 158, (HDR_H - 30) / 2 + 30 };
    g_d.moon_pop = (RECT){ g_sw - MOON_POP_W - PAD, HDR_H + GAP,
                           g_sw - PAD, HDR_H + GAP + MOON_POP_H };

    time_layout_rows();
    wsprintfW(g_res, L"%d x %d  LIVE", g_sw, g_sh);
}
