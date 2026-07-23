#ifndef COMMON_H
#define COMMON_H

#define WIN32_LEAN_AND_MEAN
#ifndef _WIN32_WINNT
#define _WIN32_WINNT 0x0602
#endif
#ifndef WINVER
#define WINVER 0x0602
#endif

#include <windows.h>

#define PAD     8
#define HDR_H   44
#define FTR_H   40
#define GAP     3
#define TITLE_H  22
#define MOON_POP_W 380
#define MOON_POP_H 158

#define CLR_MOON_LIT   RGB(236, 234, 220)
#define CLR_MOON_SHADE RGB(38, 40, 48)
#define CLR_MOON_RIM   RGB(148, 150, 145)

#define CLR_BG    RGB(0, 0, 0)
#define CLR_PANEL RGB(0, 0, 0)
#define CLR_TXT   RGB(255, 255, 255)
#define CLR_DIM   RGB(140, 140, 140)
#define CLR_ACC   RGB(255, 255, 255)
#define CLR_ON    RGB(255, 255, 255)
#define CLR_OFF   RGB(90, 90, 90)
#define CLR_LINE  RGB(255, 255, 255)
#define CLR_GRID  RGB(42, 42, 42)
#define CLR_UP    RGB(140, 210, 140)
#define CLR_DN    RGB(210, 140, 140)
#define CLR_BAND  RGB(18, 18, 18)

#define F2(b,o,v) ((b)[o]=L'0'+(v)/10,(b)[o+1]=L'0'+(v)%10)

typedef struct {
    RECT hdr, time, solar, data, alerts, footer;
    RECT moon_icon, moon_pop;
    int time_w, alt_w;
} Desk;

extern HWND g_hwnd;
extern Desk g_d;
extern int g_sw, g_sh;
extern wchar_t g_res[32];

extern HFONT fLbl, fMono, fBig, fSm;
extern HBRUSH bBg, bPanel, bWhite, bGray, bBand, bMoonLit, bMoonShade;
extern HPEN pLine, pMoonRim;

void ui_init(void);
void ui_free(void);
void ui_fill(HDC dc, const RECT *rc, HBRUSH b);
void ui_frame(HDC dc, const RECT *rc, const wchar_t *lbl);
void ui_label(HDC dc, int x, int y, const wchar_t *s, COLORREF c);
void ui_label_rect(HDC dc, const RECT *rc, const wchar_t *s, COLORREF c, HFONT font);
void ui_fmt_wdouble(wchar_t *out, int out_len, double v, int decimals);
void ui_subheading(HDC dc, const RECT *rc, const wchar_t *title);
void ui_hline(HDC dc, int x0, int y, int x1, COLORREF c);
void ui_stale_dot(HDC dc, int x, int y, int age_h);
COLORREF ui_stale_color(int age_h);
int  ui_text_w(HDC dc, HFONT font, const wchar_t *s);
RECT ui_panel_body(const RECT *p);
void desk_layout(HWND w);
void desk_chdir_exe(void);
BOOL desk_spawn_python(const wchar_t *rel_script);

#endif
