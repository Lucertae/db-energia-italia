#include "moon.h"
#include "astro.h"
#include "time.h"
#include <math.h>

#define SYNODIC 29.530588853

static MoonState g_moon;
int g_moon_open = 0;

static void sun_coords(double d, double *dec, double *ra) {
    double M = RAD * (357.5291 + 0.98560028 * d);
    double L = M + PI + RAD * (1.9148 * sin(M) + 0.02 * sin(2 * M) + 0.0003 * sin(3 * M) + 102.9372);
    double obl = RAD * 23.4397;
    *dec = asin(sin(L) * sin(obl));
    *ra = atan2(sin(L) * cos(obl), cos(L));
}

static void moon_coords(double d, double *dec, double *ra, double *dist_km) {
    double L = RAD * (218.316 + 13.176396 * d);
    double M = RAD * (134.963 + 13.064993 * d);
    double F = RAD * (93.272 + 13.229350 * d);
    double l = L + RAD * 6.289 * sin(M);
    double b = RAD * 5.128 * sin(F);
    double obl = RAD * 23.4397;
    *dec = asin(sin(b) * cos(obl) + cos(b) * sin(obl) * sin(l));
    *ra = atan2(sin(l) * cos(obl) - tan(b) * sin(obl), cos(l));
    *dist_km = 385001.0 - 20905.0 * cos(M);
}

static const wchar_t *phase_name(double p) {
    if (p < 0.03 || p > 0.97) return L"Nuova";
    if (p < 0.22) return L"Crescente";
    if (p < 0.28) return L"Primo quarto";
    if (p < 0.47) return L"Gibbosa crescente";
    if (p < 0.53) return L"Piena";
    if (p < 0.72) return L"Gibbosa calante";
    if (p < 0.78) return L"Ultimo quarto";
    return L"Crescente calante";
}

void moon_update(const SYSTEMTIME *utc) {
    double jd, d, s_dec, s_ra, m_dec, m_ra, m_dist, phi, inc, ang, p;
    MoonState *m = &g_moon;

    if (!astro_jd_from_utc(utc, &jd)) return;
    d = jd - 2451545.0;
    sun_coords(d, &s_dec, &s_ra);
    moon_coords(d, &m_dec, &m_ra, &m_dist);
    phi = acos(sin(s_dec) * sin(m_dec) + cos(s_dec) * cos(m_dec) * cos(s_ra - m_ra));
    inc = atan2(149598000.0 * sin(phi), m_dist * 1000.0 - 149598000.0 * cos(phi));
    ang = atan2(cos(s_dec) * sin(s_ra - m_ra),
        sin(s_dec) * cos(m_dec) - cos(s_dec) * sin(m_dec) * cos(s_ra - m_ra));

    m->illum = (1.0 + cos(inc)) / 2.0;
    p = 0.5 + 0.5 * inc * (ang < 0 ? -1.0 : 1.0) / PI;
    if (p < 0) p += 1.0;
    if (p >= 1.0) p -= 1.0;
    m->phase = p;
    m->age = p * SYNODIC;
    m->waxing = (BYTE)(p < 0.5);
    m->to_new = (1.0 - p) * SYNODIC;
    m->to_full = p < 0.5 ? (0.5 - p) * SYNODIC : (1.5 - p) * SYNODIC;
    lstrcpyW(m->name, phase_name(p));
    {
        wchar_t age_s[16], tf_s[16], tn_s[16];
        ui_fmt_wdouble(age_s, 16, m->age, 1);
        wsprintfW(m->cycle, L"ciclo %s / 29.5 d", age_s);
        wsprintfW(m->line1, L"illuminazione %d%%  %s",
            (int)(m->illum * 100.0 + 0.5), m->waxing ? L"crescente" : L"calante");
        ui_fmt_wdouble(tf_s, 16, m->to_full, 1);
        ui_fmt_wdouble(tn_s, 16, m->to_new, 1);
        wsprintfW(m->line2, L"piena in %sd   nuova in %sd", tf_s, tn_s);
        m->tidal_coef = 1.0 + 0.15 * fabs(cos(2.0 * PI * p));
        wsprintfW(m->tidal_note, L"marea coef %.2f", m->tidal_coef);
        lstrcpyW(m->solar_note, L"FV: zero di notte");
        lstrcpyW(m->wind_note, L"vento: no forcing lunare diretto");
        lstrcpyW(m->hydro_note, L"idro: stagionale");
        wsprintfW(m->tide_pwr_note, L"tidal power %+d%%", (int)((m->tidal_coef-1)*100));
    }
    InvalidateRect(g_hwnd, &g_d.moon_icon, FALSE);
    if (g_moon_open)
        InvalidateRect(g_hwnd, &g_d.moon_pop, FALSE);
}

const MoonState *moon_state(void) {
    return &g_moon;
}

#define MOON_ARC_STEPS 48
#define MOON_SS        2

/*
 * Lit-area boundary from sen-ltd moon-phase (SVG terminatorPath):
 * outer semicircle (limb) + inner semicircle on ellipse (terminator),
 * semi-minor axis = r * |cos(2pi * phase)|, sweep from waxing + cos sign.
 */
static int moon_arc_pts(POINT *pts, int n, int cx, int cy,
                        double rx, double ry, double a0, double a1,
                        int clockwise, int skip_first) {
    int i, steps = MOON_ARC_STEPS;
    int i0 = skip_first ? 1 : 0;
    double span;

    if (clockwise) {
        span = a1 - a0;
        if (span <= 0.0) span += 2.0 * PI;
        for (i = i0; i <= steps; i++) {
            double a = a0 + span * ((double)i / steps);
            pts[n].x = cx + (int)(rx * cos(a) + 0.5);
            pts[n].y = cy + (int)(ry * sin(a) + 0.5);
            n++;
        }
    } else {
        span = a0 - a1;
        if (span <= 0.0) span += 2.0 * PI;
        for (i = i0; i <= steps; i++) {
            double a = a0 - span * ((double)i / steps);
            pts[n].x = cx + (int)(rx * cos(a) + 0.5);
            pts[n].y = cy + (int)(ry * sin(a) + 0.5);
            n++;
        }
    }
    return n;
}

static int moon_lit_polygon(POINT *pts, int cx, int cy, int r, double phase) {
    double cos_p, minor;
    int waxing, outer_cw, inner_cw, n;

    cos_p = cos(2.0 * PI * phase);
    minor = fabs(cos_p) * (double)r;
    waxing = phase < 0.5;
    outer_cw = waxing;
    inner_cw = cos_p < 0.0;

    n = moon_arc_pts(pts, 0, cx, cy, (double)r, (double)r,
                     -PI / 2.0, PI / 2.0, outer_cw, 0);
    n = moon_arc_pts(pts, n, cx, cy, minor, (double)r,
                     PI / 2.0, -PI / 2.0, inner_cw, 1);
    return n;
}

static void moon_mare(HDC dc, int cx, int cy, int r, double phase) {
    static const struct { double x, y, w, h; } spots[] = {
        { -0.22, -0.08, 0.34, 0.28 },
        {  0.12,  0.18, 0.26, 0.22 },
        { -0.05,  0.30, 0.20, 0.16 },
    };
    int i, sx, sy, sw, sh;
    HRGN clip;

    if (phase < 0.08 || phase > 0.92) return;

    clip = CreateEllipticRgn(cx - r, cy - r, cx + r, cy + r);
    SelectClipRgn(dc, clip);
    SelectObject(dc, bMoonShade);
    for (i = 0; i < 3; i++) {
        sx = cx + (int)(spots[i].x * r);
        sy = cy + (int)(spots[i].y * r);
        sw = (int)(spots[i].w * r);
        sh = (int)(spots[i].h * r);
        if (sw < 2 || sh < 2) continue;
        Ellipse(dc, sx - sw / 2, sy - sh / 2, sx + sw / 2, sy + sh / 2);
    }
    SelectClipRgn(dc, NULL);
    DeleteObject(clip);
}

static void moon_disk(HDC dc, int cx, int cy, int r) {
    const MoonState *m = &g_moon;
    double p = m->phase;
    POINT pts[MOON_ARC_STEPS * 2 + 4];
    HDC mem;
    HBITMAP bm, old_bm;
    HRGN clip;
    int diam, bmp_sz, mcx, mcy, mr, n;
    RECT dst;

    diam = r * 2 + 4;
    bmp_sz = diam * MOON_SS;
    mcx = bmp_sz / 2;
    mcy = bmp_sz / 2;
    mr = r * MOON_SS;

    mem = CreateCompatibleDC(dc);
    bm = CreateCompatibleBitmap(dc, bmp_sz, bmp_sz);
    old_bm = (HBITMAP)SelectObject(mem, bm);

    clip = CreateEllipticRgn(mcx - mr, mcy - mr, mcx + mr, mcy + mr);
    SelectClipRgn(mem, clip);

    SelectObject(mem, bMoonShade);
    Ellipse(mem, mcx - mr, mcy - mr, mcx + mr, mcy + mr);

    if (p > 0.005 && p < 0.995) {
        n = moon_lit_polygon(pts, mcx, mcy, mr, p);
        if (n >= 3) {
            SelectObject(mem, bMoonLit);
            Polygon(mem, pts, n);
            moon_mare(mem, mcx, mcy, mr, p);
        }
    } else if (p >= 0.995 || m->illum > 0.5) {
        SelectObject(mem, bMoonLit);
        Ellipse(mem, mcx - mr, mcy - mr, mcx + mr, mcy + mr);
        moon_mare(mem, mcx, mcy, mr, p);
    }

    SelectClipRgn(mem, NULL);
    DeleteObject(clip);

    SelectObject(mem, pMoonRim);
    SelectObject(mem, GetStockObject(NULL_BRUSH));
    Ellipse(mem, mcx - mr, mcy - mr, mcx + mr, mcy + mr);

    dst = (RECT){ cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2 };
    SetStretchBltMode(dc, HALFTONE);
    SetBrushOrgEx(dc, 0, 0, NULL);
    StretchBlt(dc, dst.left, dst.top, diam, diam,
               mem, 0, 0, bmp_sz, bmp_sz, SRCCOPY);

    SelectObject(mem, old_bm);
    DeleteObject(bm);
    DeleteDC(mem);
}

static void moon_bar(HDC dc, int x, int y, int w) {
    const MoonState *m = &g_moon;
    RECT track = { x, y, x + w, y + 6 };
    RECT fill_rc;
    int fw;

    if (w < 8) return;
    SelectObject(dc, pLine);
    SelectObject(dc, GetStockObject(NULL_BRUSH));
    Rectangle(dc, track.left, track.top, track.right, track.bottom);
    fw = (int)((m->age / SYNODIC) * (w - 2));
    if (fw < 1) fw = 1;
    fill_rc = (RECT){ x + 1, y + 1, x + 1 + fw, y + 5 };
    ui_fill(dc, &fill_rc, bWhite);
}

void moon_paint_icon(HDC dc) {
    const RECT *rc = &g_d.moon_icon;
    int r = (rc->right - rc->left) / 2 - 2;
    int cx = (rc->left + rc->right) / 2;
    int cy = (rc->top + rc->bottom) / 2;

    if (r < 6) return;
    moon_disk(dc, cx, cy, r);
    if (g_moon_open) {
        SelectObject(dc, pLine);
        SelectObject(dc, GetStockObject(NULL_BRUSH));
        Rectangle(dc, rc->left - 3, rc->top - 3, rc->right + 3, rc->bottom + 3);
    }
}

void moon_paint_popup(HDC dc) {
    const MoonState *m = moon_state();
    RECT body, text_rc, icon_rc, line_rc;
    int disk_r, disk_cx, disk_cy, y;
    const int lh = 16;
    const int icon_w = 96;

    if (!g_moon_open) return;
    ui_frame(dc, &g_d.moon_pop, L"LUNAR / CICLO");
    body = ui_panel_body(&g_d.moon_pop);

    icon_rc = (RECT){ body.right - icon_w, body.top, body.right, body.bottom };
    text_rc = (RECT){ body.left, body.top, icon_rc.left - 8, body.bottom };

    y = text_rc.top;
    line_rc = (RECT){ text_rc.left, y, text_rc.right, y + 22 };
    ui_label_rect(dc, &line_rc, m->name, CLR_ACC, fBig);
    y += 24;
    line_rc.top = y; line_rc.bottom = y + lh;
    ui_label_rect(dc, &line_rc, m->cycle, CLR_TXT, fLbl);
    y += lh;
    line_rc.top = y; line_rc.bottom = y + lh;
    ui_label_rect(dc, &line_rc, m->line1, CLR_TXT, fLbl);
    y += lh;
    line_rc.top = y; line_rc.bottom = y + lh;
    ui_label_rect(dc, &line_rc, m->line2, CLR_DIM, fLbl);
    y += lh + 6;
    if (y + 8 <= text_rc.bottom)
        moon_bar(dc, text_rc.left, y, text_rc.right - text_rc.left);

    disk_r = (icon_rc.bottom - icon_rc.top) / 2 - 8;
    if (disk_r > 40) disk_r = 40;
    if (disk_r < 14) disk_r = 14;
    disk_cx = (icon_rc.left + icon_rc.right) / 2;
    disk_cy = (icon_rc.top + icon_rc.bottom) / 2;
    moon_disk(dc, disk_cx, disk_cy, disk_r);
}

static void moon_hub_row(HDC dc, int x, int y, int w, const Clock *c) {
    wchar_t line[80], irr[12];
    RECT rc = { x, y, x + w, y + 14 };

    if (!c) return;
    ui_fmt_wdouble(irr, 12, c->sun_s, 0);
    wsprintfW(line, L"%-4s  %s  irraggiamento %s%%  (lat reale)",
              c->abbr, c->day ? L"GIORNO" : L"NOTTE", irr);
    SetTextColor(dc, c->day ? CLR_UP : CLR_OFF);
    ui_label_rect(dc, &rc, line, c->day ? CLR_TXT : CLR_DIM, fSm);
}

void moon_paint_page(HDC dc, const RECT *rc) {
    const MoonState *m = moon_state();
    RECT body = *rc, left, right, lr;
    int disk_r, y;
    static const int HUBS[] = { I_LON, I_NYC, I_DXB, I_TYO };
    int i;

    if (!m) return;
    left = body;
    left.right = body.left + (body.right - body.left) * 48 / 100;
    right = body;
    right.left = left.right + 12;

    ui_subheading(dc, &(RECT){ left.left, left.top, left.right, left.top + 12 },
                  L"LUNA / CICLO");
    left.top += 14;
    y = left.top;
    lr = (RECT){ left.left, y, left.right, y + 22 };
    ui_label_rect(dc, &lr, m->name, CLR_ACC, fBig);
    y += 24;
    lr.top = y; lr.bottom = y + 14;
    ui_label_rect(dc, &lr, m->cycle, CLR_TXT, fLbl);
    y += 16;
    lr.top = y; lr.bottom = y + 14;
    ui_label_rect(dc, &lr, m->line1, CLR_TXT, fSm);
    y += 15;
    lr.top = y; lr.bottom = y + 14;
    ui_label_rect(dc, &lr, m->line2, CLR_DIM, fSm);
    y += 18;
    moon_bar(dc, left.left, y, left.right - left.left);
    y += 16;
    lr.top = y; lr.bottom = y + 14;
    ui_label_rect(dc, &lr, m->tidal_note, CLR_TXT, fSm);
    y += 15;
    lr.top = y; lr.bottom = y + 14;
    ui_label_rect(dc, &lr, m->tide_pwr_note, CLR_ACC, fSm);
    y += 15;
    lr.top = y; lr.bottom = y + 14;
    ui_label_rect(dc, &lr, m->solar_note, CLR_DIM, fSm);
    y += 15;
    lr.top = y; lr.bottom = y + 14;
    ui_label_rect(dc, &lr, m->wind_note, CLR_DIM, fSm);
    y += 15;
    lr.top = y; lr.bottom = y + 14;
    ui_label_rect(dc, &lr, m->hydro_note, CLR_DIM, fSm);

    disk_r = (left.bottom - y) / 2 - 4;
    if (disk_r > 48) disk_r = 48;
    if (disk_r < 16) disk_r = 16;
    moon_disk(dc, (left.left + left.right) / 2, (y + left.bottom) / 2, disk_r);

    ui_subheading(dc, &(RECT){ right.left, right.top, right.right, right.top + 12 },
                  L"EFFETTI PER HUB (sole reale + marea)");
    right.top += 14;
    y = right.top;
    for (i = 0; i < 4; i++) {
        Clock *c = time_get(HUBS[i]);
        if (!c) continue;
        moon_hub_row(dc, right.left, y, right.right - right.left, c);
        y += 15;
    }
    y += 8;
    lr = (RECT){ right.left, y, right.right, y + 14 };
    ui_label_rect(dc, &lr,
        L"Notte: domanda luce +0.3-0.8% a luna piena (illuminazione urbana)",
        CLR_OFF, fSm);
    y += 16;
    lr.top = y; lr.bottom = y + 14;
    {
        wchar_t tide[48];
        wsprintfW(tide, L"coef marea %.2f su impianti tidal EU/UK", m->tidal_coef);
        ui_label_rect(dc, &lr, tide, CLR_TXT, fSm);
    }
}
