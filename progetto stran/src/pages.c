#include "pages.h"
#include "systemic.h"
#include "chart.h"
#include "data.h"
#include "dcf.h"
#include "fin.h"
#include "energy.h"
#include "companies.h"
#include "production.h"
#include "corr.h"
#include "risk.h"
#include "countries.h"
#include "ships.h"
#include "catalog.h"
#include "weather.h"
#include "glossary.h"
#include "modules.h"
#include "ops.h"
#include "lab.h"
#include "sig.h"
#include "gas.h"
#include "forcing.h"
#include "qa.h"
#include "intel.h"
#include "desk_panels.h"
#include "ingest_view.h"
#include "globe_view.h"
#include "weather.h"
#include <math.h>
#include <stdlib.h>

int g_page = PAGE_OPS;
int g_geo_tab = 0;
int g_nrg_tab = 0;
int g_data_only = 0;

void pages_set_data_only(int on) {
    g_data_only = on ? 1 : 0;
    if (g_data_only)
        g_page = PAGE_INGEST;
}

int pages_can_switch(int page) {
    if (!g_data_only) return 1;
    return (page == PAGE_INGEST || page == PAGE_GLOBE) ? 1 : 0;
}

static RECT g_subtab_rc;
static int  g_subtab_page = -1;
static int  g_subtab_count = 0;

static RECT page_body(void) {
    RECT r = { PAD, 0, 0, 0 };

    r.top = g_d.hdr.bottom + GAP;
    r.right = g_sw - PAD;
    r.bottom = g_d.footer.top - GAP;
    return r;
}

const wchar_t *pages_name(int page) {
    static const wchar_t *N[PAGE_COUNT] = {
        L"OPS", L"MKT", L"FX", L"NRG", L"GAS", L"MET", L"ASTRO",
        L"LAB", L"SIG", L"RISK", L"GEO", L"AIS", L"NEWS", L"CAT", L"ING", L"GLB"
    };
    if (page < 0 || page >= PAGE_COUNT) return L"?";
    return N[page];
}

const wchar_t *pages_hotkey(int page) {
    static const wchar_t *K[PAGE_COUNT] = {
        L"1/O", L"2/M", L"3/F", L"4/R", L"5/G", L"6/W", L"7/A",
        L"8/L", L"9/S", L"0/K", L"E", L"I", L"N", L"C", L"X", L"U"
    };
    if (page < 0 || page >= PAGE_COUNT) return L"?";
    return K[page];
}

/* Global navigation: digits 1-9,0 and letter mnemonics → page index */
int pages_from_vkey(int vk) {
    int page = -1;

    if (vk >= '1' && vk <= '9')
        page = vk - '1';
    else if (vk == '0')
        page = PAGE_RISK;
    else {
        switch (vk) {
        case 'o': case 'O': page = PAGE_OPS; break;
        case 'm': case 'M': page = PAGE_MKT; break;
        case 'f': case 'F': page = PAGE_FX; break;
        case 'r': case 'R': page = PAGE_NRG; break;
        case 'g': case 'G': page = PAGE_GAS; break;
        case 'w': case 'W': page = PAGE_MET; break;
        case 'a': case 'A': page = PAGE_ASTRO; break;
        case 'l': case 'L': page = PAGE_LAB; break;
        case 's': case 'S': page = PAGE_SIG; break;
        case 'k': case 'K': page = PAGE_RISK; break;
        case 'e': case 'E': page = PAGE_GEO; break;
        case 'i': case 'I': page = PAGE_AIS; break;
        case 'n': case 'N': page = PAGE_NEWS; break;
        case 'c': case 'C': page = PAGE_CAT; break;
        case 'x': case 'X': page = PAGE_INGEST; break;
        case 'u': case 'U': page = PAGE_GLOBE; break;
        default: return -1;
        }
    }
    if (page >= 0 && !pages_can_switch(page))
        return -1;
    return page;
}

void pages_hint(HDC dc) {
    RECT r = g_d.hdr;
    wchar_t buf[140];

    r.right -= 12;
    if (g_data_only) {
        lstrcpyW(buf, L"DATI  ·  X ING  U GLB  ·  Enter API  digita filtro");
    } else {
        wsprintfW(buf, L"%s %s   [%d/%d]  Tab next",
                  pages_hotkey(g_page), pages_name(g_page), g_page + 1, PAGE_COUNT);
        if (g_page == PAGE_GEO || g_page == PAGE_NRG)
            lstrcatW(buf, L"  , . sub-tab");
        if (g_page == PAGE_INGEST)
            lstrcatW(buf, L"  , . tab  type filtro");
    }
    SetBkMode(dc, TRANSPARENT);
    SetTextColor(dc, CLR_OFF);
    SelectObject(dc, fSm);
    DrawTextW(dc, buf, -1, &r, DT_RIGHT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX);
}

static void paint_tabs(HDC dc, RECT *body) {
    static const wchar_t *TABS[PAGE_COUNT] = {
        L"1 OPS", L"2 MKT", L"3 FX", L"4 NRG", L"5 GAS", L"6 MET",
        L"7 AST", L"8 LAB", L"9 SIG", L"0 RSK", L"E GEO", L"I AIS",
        L"N NEWS", L"C CAT", L"X ING", L"U GLB"
    };
    int i, x = body->left, avail = body->right - body->left;
    int tab_w;

    if (g_data_only) {
        static const int DATA_PAGES[2] = { PAGE_INGEST, PAGE_GLOBE };
        static const wchar_t *DATA_TABS[2] = { L"X ING", L"U GLB" };
        g_subtab_page = -1;
        tab_w = 72;
        for (i = 0; i < 2; i++) {
            RECT cell = { x, body->top, x + tab_w, body->top + 18 };
            if (DATA_PAGES[i] == g_page) {
                FillRect(dc, &cell, bWhite);
                SetTextColor(dc, CLR_BG);
            } else {
                FillRect(dc, &cell, bBand);
                SetTextColor(dc, CLR_DIM);
            }
            SetBkMode(dc, TRANSPARENT);
            SelectObject(dc, fSm);
            DrawTextW(dc, (wchar_t *)DATA_TABS[i], -1, &cell,
                      DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX);
            x += tab_w + 2;
        }
        body->top += 22;
        return;
    }

    tab_w = avail / PAGE_COUNT - 2;
    if (tab_w < 36) tab_w = 36;
    if (tab_w > 56) tab_w = 56;

    g_subtab_page = -1;
    for (i = 0; i < PAGE_COUNT; i++) {
        RECT cell = { x, body->top, x + tab_w, body->top + 18 };

        if (i == g_page) {
            FillRect(dc, &cell, bWhite);
            SetTextColor(dc, CLR_BG);
        } else {
            FillRect(dc, &cell, bBand);
            SetTextColor(dc, CLR_DIM);
        }
        SetBkMode(dc, TRANSPARENT);
        SelectObject(dc, fSm);
        DrawTextW(dc, (wchar_t *)TABS[i], -1, &cell,
                  DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX |
                  DT_END_ELLIPSIS);
        x += tab_w + 2;
    }
    body->top += 18 + 4;
}

static void paint_subtabs(HDC dc, RECT *body, int page) {
    static const wchar_t *GEO_TABS[GEO_TAB_COUNT] = {
        L"PAESI", L"PROD", L"AZIENDE", L"CAPACITA", L"VENTO", L"RISK", L"HEAD"
    };
    static const wchar_t *NRG_TABS[NRG_TAB_COUNT] = {
        L"DESK", L"NETWORK", L"VENTO", L"ORARIA"
    };
    const wchar_t **tabs;
    int n, i, x, tab_w, active;

    if (page == PAGE_GEO) {
        tabs = GEO_TABS;
        n = GEO_TAB_COUNT;
        active = g_geo_tab;
    } else if (page == PAGE_NRG) {
        tabs = NRG_TABS;
        n = NRG_TAB_COUNT;
        active = g_nrg_tab;
    } else {
        return;
    }

    g_subtab_page = page;
    g_subtab_count = n;
    g_subtab_rc.left = body->left;
    g_subtab_rc.top = body->top;
    g_subtab_rc.right = body->right;
    g_subtab_rc.bottom = body->top + 16;

    tab_w = (body->right - body->left) / n - 2;
    if (tab_w < 48) tab_w = 48;
    x = body->left;
    for (i = 0; i < n; i++) {
        RECT cell = { x, body->top, x + tab_w, body->top + 16 };
        if (i == active) {
            FillRect(dc, &cell, bWhite);
            SetTextColor(dc, CLR_BG);
        } else {
            FrameRect(dc, &cell, GetStockObject(WHITE_BRUSH));
            SetTextColor(dc, CLR_DIM);
        }
        SetBkMode(dc, TRANSPARENT);
        SelectObject(dc, fSm);
        DrawTextW(dc, (wchar_t *)tabs[i], -1, &cell,
                  DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX);
        x += tab_w + 2;
    }
    body->top += 16 + 6;
}

void pages_geo_tab_next(int dir) {
    g_geo_tab += dir;
    if (g_geo_tab < 0) g_geo_tab = GEO_TAB_COUNT - 1;
    if (g_geo_tab >= GEO_TAB_COUNT) g_geo_tab = 0;
}

void pages_nrg_tab_next(int dir) {
    g_nrg_tab += dir;
    if (g_nrg_tab < 0) g_nrg_tab = NRG_TAB_COUNT - 1;
    if (g_nrg_tab >= NRG_TAB_COUNT) g_nrg_tab = 0;
}

int pages_subtab_hit(POINT pt) {
    int tab_w, i, x;

    if (g_subtab_page < 0 || g_subtab_count <= 0) return -1;
    if (!PtInRect(&g_subtab_rc, pt)) return -1;
    tab_w = (g_subtab_rc.right - g_subtab_rc.left) / g_subtab_count - 2;
    if (tab_w < 48) tab_w = 48;
    x = g_subtab_rc.left;
    for (i = 0; i < g_subtab_count; i++) {
        RECT cell = { x, g_subtab_rc.top, x + tab_w, g_subtab_rc.bottom };
        if (PtInRect(&cell, pt)) return i;
        x += tab_w + 2;
    }
    return -1;
}

/* -1 se il punto non cade su nessuna tab */
int pages_tab_hit(POINT pt) {
    RECT body = page_body();
    int i, x = body.left, tab_w = 48;

    if (g_data_only) {
        static const int DATA_PAGES[2] = { PAGE_INGEST, PAGE_GLOBE };
        tab_w = 72;
        for (i = 0; i < 2; i++) {
            RECT cell = { x, body.top, x + tab_w, body.top + 18 };
            if (PtInRect(&cell, pt)) return DATA_PAGES[i];
            x += tab_w + 2;
        }
        return -1;
    }

    tab_w = (body.right - body.left) / PAGE_COUNT - 2;
    if (tab_w < 36) tab_w = 36;
    if (tab_w > 56) tab_w = 56;
    for (i = 0; i < PAGE_COUNT; i++) {
        RECT cell = { x, body.top, x + tab_w, body.top + 18 };

        if (PtInRect(&cell, pt)) return i;
        x += tab_w + 2;
    }
    return -1;
}

/* ---------- scheda 2: MARKETS grid, tutte le serie in store ---------- */

typedef struct {
    HDC dc;
    RECT area;
} GridCtx;

typedef struct {
    const wchar_t *lbl;
    float z;
} MoverRow;

static int mover_cmp(const void *a, const void *b) {
    const MoverRow *x = (const MoverRow *)a;
    const MoverRow *y = (const MoverRow *)b;
    float ax = x->z < 0.0f ? -x->z : x->z;
    float ay = y->z < 0.0f ? -y->z : y->z;
    if (ax > ay) return -1;
    if (ax < ay) return 1;
    return 0;
}

static void paint_movers(HDC dc, RECT *rc, const SeriesStore *st) {
    MoverRow rows[64];
    int i, n = 0, y, lh = 13;
    wchar_t line[80];

    ui_subheading(dc, &(RECT){ rc->left, rc->top, rc->right, rc->top + 12 },
                  L"MOVERS  |z| 30d");
    y = rc->top + 14;
    for (i = 0; i < st->n && n < 64; i++) {
        const DataSeries *s = &st->s[i];
        float z;
        if (s->n < 30) continue;
        z = fin_ret_zscore(s, 30);
        if (z == 0.0f && s->n < 31) continue;
        rows[n].lbl = s->label;
        rows[n].z = z;
        n++;
    }
    qsort(rows, (size_t)n, sizeof(rows[0]), mover_cmp);
    for (i = 0; i < n && i < 10 && y + lh <= rc->bottom; i++) {
        wsprintfW(line, L"%-10s %+.2f", rows[i].lbl, rows[i].z);
        SetTextColor(dc, rows[i].z >= 0.0f ? CLR_UP : CLR_DN);
        SelectObject(dc, fSm);
        TextOutW(dc, rc->left, y, line, lstrlenW(line));
        y += lh;
    }
    rc->top = y + 4;
}

static float regime_score(const SeriesStore *st) {
    DataSeries *vix, *dxy, *hyo;
    float s2s10 = 0.0f, score = 0.0f;

    vix = series_get((SeriesStore *)st, "VIX");
    dxy = series_get((SeriesStore *)st, "DXY");
    hyo = series_get((SeriesStore *)st, "HYO");
    fin_yield_spread_bps(st, "U10", "U2", &s2s10);
    if (vix && vix->n >= 20) score -= fin_level_zscore(vix, 90) * 0.35f;
    if (dxy && dxy->n >= 20) score -= fin_level_zscore(dxy, 90) * 0.25f;
    if (hyo && hyo->n >= 6) {
        float prev = hyo->val[hyo->n - 6];
        float chg = prev > 0.0f ? (series_last(hyo) - prev) / prev : 0.0f;
        score -= chg * 4.0f;
    }
    score += s2s10 * 0.004f;
    if (score > 1.0f) score = 1.0f;
    if (score < -1.0f) score = -1.0f;
    return score;
}

static void grid_cb(const SeriesStore *st, void *ctx) {
    GridCtx *g = (GridCtx *)ctx;
    static const struct { uint8_t kind; const wchar_t *lbl; } SEC[] = {
        { SER_ENERGY, L"ENERGY" }, { SER_FX, L"FX" }, { SER_RATE, L"RATES" },
        { SER_MACRO, L"MACRO" }, { SER_CRYPTO, L"CRYPTO" }
    };
    int cols = 4, i, k, si, rows, cell_h, cell_w, n = 0;
    wchar_t cap[48];
    RECT hdr, gloss, movers, area, regime;

    gloss = g->area;
    gloss.left = gloss.right - 228;
    movers = gloss;
    movers.bottom = gloss.top + (gloss.bottom - gloss.top) * 42 / 100;
    gloss.top = movers.bottom + 6;
    area = g->area;
    area.right = gloss.left - 8;
    area.bottom -= 18;
    regime = g->area;
    regime.top = g->area.bottom - 16;
    paint_movers(g->dc, &movers, st);
    gloss_paint_panel(g->dc, &gloss, PAGE_MKT);

    for (si = 0; si < (int)(sizeof(SEC) / sizeof(SEC[0])); si++) {
        int sec_n = 0;
        for (i = 0; i < st->n; i++)
            if (st->s[i].n >= 2 && st->s[i].kind == SEC[si].kind) sec_n++;
        if (sec_n == 0) continue;
        hdr = area;
        hdr.bottom = hdr.top + 12;
        wsprintfW(cap, L"%s  %d", SEC[si].lbl, sec_n);
        ui_subheading(g->dc, &hdr, cap);
        area.top += 14;
        rows = (sec_n + cols - 1) / cols;
        cell_h = 36;
        cell_w = (area.right - area.left) / cols;
        k = 0;
        for (i = 0; i < st->n; i++) {
            const DataSeries *s = &st->s[i];
            RECT c;
            if (s->n < 2 || s->kind != SEC[si].kind) continue;
            c.left = area.left + (k % cols) * cell_w + 2;
            c.right = c.left + cell_w - 8;
            c.top = area.top + (k / cols) * cell_h + 2;
            c.bottom = c.top + cell_h - 8;
            if (c.bottom > g->area.bottom - 16) break;
            chart_horizon(g->dc, &c, s, s->label, CLR_LINE, 5);
            k++;
        }
        area.top += rows * cell_h + 6;
        n += sec_n;
    }
    gloss_paint_footer(g->dc, &(RECT){ g->area.left, g->area.bottom - 14,
                                      gloss.left - 8, g->area.bottom }, PAGE_MKT);
    chart_regime_bar(g->dc, &regime, (regime_score(st) + 1.0f) * 50.0f, L"REGIME risk-on/off");
    if (n == 0)
        ui_label_rect(g->dc, &area, L"attesa dati...", CLR_OFF, fLbl);
}

static void page_markets(HDC dc, RECT body) {
    GridCtx g;

    g.dc = dc;
    g.area = body;
    data_store_read(grid_cb, &g);
}

/* ---------- scheda 3: FX / RATES ---------- */

static void paint_yield_curve(HDC dc, const RECT *rc, const SeriesStore *st) {
    RECT r = *rc, crv;
    wchar_t line[120];
    float s2s10 = 0.0f, s5s30 = 0.0f;

    ui_subheading(dc, &(RECT){ r.left, r.top, r.right, r.top + 12 },
                  L"US YIELD CURVE");
    crv = r;
    crv.top += 14;
    crv.bottom -= 18;
    chart_yield_curve(dc, &crv, st);
    fin_yield_spread_bps(st, "U10", "U2", &s2s10);
    fin_yield_spread_bps(st, "U30", "U5", &s5s30);
    wsprintfW(line, L"2s10s %+0.0f bp   5s30s %+0.0f bp", s2s10, s5s30);
    ui_label_rect(dc, &(RECT){ r.left, r.bottom - 16, r.right, r.bottom },
                  line, s2s10 < 0.0f ? CLR_DN : CLR_ACC, fSm);
}

typedef struct { HDC dc; RECT rc; } YieldCtx;

static void yield_cb(const SeriesStore *st, void *ctx) {
    YieldCtx *y = (YieldCtx *)ctx;
    paint_yield_curve(y->dc, &y->rc, st);
}

typedef struct {
    HDC dc;
    RECT net;
    RECT tbl;
} FxCtx;

static float fx_carry_lookup(const char *desk_id) {
    int i;
    for (i = 0; i < modules_fx_carry_top_count(); i++) {
        const FxCarryRow *c = modules_fx_carry_top_get(i);
        if (!c) continue;
        if (lstrcmpiA(c->pair + 3, desk_id) == 0 || strstr(c->pair, desk_id))
            return c->carry_spread;
    }
    return 0.0f;
}

static float fx_mom_lookup(const char *desk_id) {
    int i;
    for (i = 0; i < modules_fx_carry_top_count(); i++) {
        const FxCarryRow *c = modules_fx_carry_top_get(i);
        if (!c) continue;
        if (lstrcmpiA(c->pair + 3, desk_id) == 0 || strstr(c->pair, desk_id))
            return c->mom_63d;
    }
    return 0.0f;
}

static void fx_table_row(HDC dc, int x, int y, const wchar_t *cols[9], COLORREF c) {
    static const int OFF[9] = { 0, 72, 140, 200, 252, 304, 356, 408, 460 };
    int i;

    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    for (i = 0; i < 9; i++) {
        SetTextColor(dc, c);
        TextOutW(dc, x + OFF[i], y, cols[i], lstrlenW(cols[i]));
    }
}

static void fx_cb(const SeriesStore *st, void *ctx) {
    FxCtx *f = (FxCtx *)ctx;
    static const wchar_t *HDRS[9] = { L"PAIR", L"LAST", L"\x0394 1d", L"\x0394 1m",
                                      L"RV30%", L"CARRY", L"MOM63", L"52W LO", L"52W HI" };
    int i, y, row_h = 16;

    chart_fx_network(f->dc, &f->net, st);

    y = f->tbl.top;
    fx_table_row(f->dc, f->tbl.left, y, HDRS, CLR_DIM);
    y += row_h + 2;
    ui_hline(f->dc, f->tbl.left, y - 2, f->tbl.right, CLR_GRID);

    for (i = 0; i < st->n; i++) {
        const DataSeries *s = &st->s[i];
        wchar_t last_s[16], d1_s[16], dm_s[16], sg_s[16], lo_s[16], hi_s[16];
        wchar_t carry_s[16], mom_s[16];
        const wchar_t *cols[9];
        float last, prev1, prevm, d1, dm, carry, mom;
        int back;

        if (s->kind != SER_FX || s->n < 3) continue;
        if (y + row_h > f->tbl.bottom) break;

        last = series_last(s);
        prev1 = s->val[s->n - 2];
        back = s->n > 22 ? 22 : s->n - 1;
        prevm = s->val[s->n - 1 - back];
        d1 = prev1 > 0.0f ? (last - prev1) / prev1 * 100.0f : 0.0f;
        dm = prevm > 0.0f ? (last - prevm) / prevm * 100.0f : 0.0f;
        carry = fx_carry_lookup(s->id);
        mom = fx_mom_lookup(s->id);

        ui_fmt_wdouble(last_s, 16, last, last > 50.0f ? 2 : 4);
        ui_fmt_wdouble(d1_s, 16, d1, 2);
        ui_fmt_wdouble(dm_s, 16, dm, 1);
        ui_fmt_wdouble(sg_s, 16, fin_rv_ann_pct(s, 30, 0), 1);
        ui_fmt_wdouble(carry_s, 16, carry, 2);
        ui_fmt_wdouble(mom_s, 16, mom, 1);
        ui_fmt_wdouble(lo_s, 16, s->min_h, s->min_h > 50.0f ? 1 : 4);
        ui_fmt_wdouble(hi_s, 16, s->max_h, s->max_h > 50.0f ? 1 : 4);

        cols[0] = s->label;
        cols[1] = last_s;
        cols[2] = d1_s;
        cols[3] = dm_s;
        cols[4] = sg_s;
        cols[5] = carry_s;
        cols[6] = mom_s;
        cols[7] = lo_s;
        cols[8] = hi_s;
        fx_table_row(f->dc, f->tbl.left, y, cols, CLR_TXT);

        {
            RECT dot = { f->tbl.left - 10, y + 4, f->tbl.left - 3, y + 11 };
            HBRUSH b = CreateSolidBrush(d1 >= 0.0f ? CLR_UP : CLR_DN);
            FillRect(f->dc, &dot, b);
            DeleteObject(b);
        }
        y += row_h;
    }
}

static void page_fx(HDC dc, RECT body) {
    FxCtx f;
    int split = (body.right - body.left) * 38 / 100;
    RECT cip, curve, gloss, rank, cyc;
    YieldCtx yc;

    gloss = body;
    gloss.left = gloss.right - 228;
    body.right = gloss.left - 8;
    rank = gloss;
    rank.bottom = gloss.top + (gloss.bottom - gloss.top) * 55 / 100;
    cyc = gloss;
    cyc.top = rank.bottom + 6;
    ui_frame(dc, &rank, L"CARRY rank");
  {
        RECT inner = ui_panel_body(&rank);
        modules_paint_fx_ranking(dc, &inner);
    }
    ui_frame(dc, &cyc, L"CICLI grafo");
    {
        RECT inner = ui_panel_body(&cyc);
        modules_paint_fx_cycles(dc, &inner);
    }

    curve = (RECT){ body.left, body.bottom - 88, body.left + split, body.bottom };
    body.bottom -= 88;
    cip = (RECT){ body.left, body.bottom - 52, body.left + split, body.bottom };
    f.dc = dc;
    f.net = (RECT){ body.left, body.top, body.left + split, cip.top - 8 };
    f.tbl = (RECT){ body.left + split + 24, body.top, body.right, body.bottom };
    ui_subheading(dc, &(RECT){ f.net.left, f.net.top, f.net.right, f.net.top + 12 },
                  L"FX NETWORK  (click su un nodo per cambiare hub)");
    f.net.top += 14;
    data_store_read(fx_cb, &f);

    ui_subheading(dc, &(RECT){ cip.left, cip.top, cip.right, cip.top + 12 },
                  L"CIP FORWARD EUR/USD (SOFR vs ECB DFR)");
    cip.top += 14;
    {
        DataSeries usd, sof, dfr;
        wchar_t s_s[16], f3_s[16], f1_s[16], rd_s[12], rf_s[12], line[96];
        RECT lr;
        ldf spot, r_us, r_eu;

        if (data_series_snap("USD", &usd) && data_series_snap("SOF", &sof) &&
            data_series_snap("EDF", &dfr) && usd.n >= 2 && sof.n >= 2 && dfr.n >= 2) {
            spot = (ldf)series_last(&usd);
            r_us = (ldf)series_last(&sof) / 100.0L;
            r_eu = (ldf)series_last(&dfr) / 100.0L;
            ui_fmt_wdouble(s_s, 16, (double)spot, 4);
            ui_fmt_wdouble(f3_s, 16, (double)dcf_cip_forward(spot, r_us, r_eu, 0.25L), 4);
            ui_fmt_wdouble(f1_s, 16, (double)dcf_cip_forward(spot, r_us, r_eu, 1.0L), 4);
            ui_fmt_wdouble(rd_s, 12, (double)(r_us * 100.0L), 2);
            ui_fmt_wdouble(rf_s, 12, (double)(r_eu * 100.0L), 2);
            lr = (RECT){ cip.left, cip.top, cip.right, cip.top + 15 };
            wsprintfW(line, L"SPOT %s   SOFR %s%%   DFR %s%%", s_s, rd_s, rf_s);
            ui_label_rect(dc, &lr, line, CLR_TXT, fSm);
            lr.top += 16;
            lr.bottom += 16;
            wsprintfW(line, L"FWD 3M %s   FWD 1Y %s", f3_s, f1_s);
            ui_label_rect(dc, &lr, line, CLR_ACC, fSm);
        } else {
            lr = (RECT){ cip.left, cip.top, cip.right, cip.top + 15 };
            ui_label_rect(dc, &lr, L"attesa serie SOFR / ECB DFR...", CLR_OFF, fSm);
        }
    }

    yc.dc = dc;
    yc.rc = curve;
    data_store_read(yield_cb, &yc);
    gloss_paint_footer(dc, &(RECT){ body.left, body.bottom + 4, body.right, body.bottom + 18 },
                       PAGE_FX);
}

typedef struct { HDC dc; RECT body; } PageCtx;

typedef struct {
    HDC dc;
    RECT body;
} CorrCtx;

typedef struct {
    const char *a;
    const char *b;
    const wchar_t *note;
} CorrLink;

static void corr_cb(const SeriesStore *st, void *ctx);

static void page_nrg_cb(const SeriesStore *st, void *ctx) {
    PageCtx *p = (PageCtx *)ctx;
    if (g_nrg_tab == 1)
        energy_paint_page(p->dc, &p->body, st);
    else if (g_nrg_tab == 2)
        desk_paint_entsoe_wind(p->dc, &p->body, st);
    else if (g_nrg_tab == 3)
        desk_paint_entsoe_hourly(p->dc, &p->body, NULL);
    else
        energy_paint_desk(p->dc, &p->body, st);
}

static void page_nrg(HDC dc, RECT body) {
    PageCtx p;
    paint_subtabs(dc, &body, PAGE_NRG);
    p.dc = dc;
    p.body = body;
    data_store_read(page_nrg_cb, &p);
}

static void page_ops_cb(const SeriesStore *st, void *ctx) {
    PageCtx *p = (PageCtx *)ctx;
    ops_paint(p->dc, &p->body, st);
}

static void page_ops(HDC dc, RECT body) {
    PageCtx p = { dc, body };
    data_store_read(page_ops_cb, &p);
}

typedef struct { HDC dc; RECT body; } GeoWindCtx;

static void page_geo_wind_cb(const SeriesStore *st, void *ctx) {
    GeoWindCtx *g = (GeoWindCtx *)ctx;
    desk_paint_entsoe_wind(g->dc, &g->body, st);
}

static void page_geo_risk_cb(const SeriesStore *st, void *ctx) {
    GeoWindCtx *g = (GeoWindCtx *)ctx;
    desk_paint_georisk(g->dc, &g->body, st);
}

static void page_geo(HDC dc, RECT body) {
    paint_subtabs(dc, &body, PAGE_GEO);
    switch (g_geo_tab) {
    case 0:
        countries_paint(dc, &body);
        break;
    case 1:
        production_paint(dc, &body);
        break;
    case 2:
        companies_paint(dc, &body, -1);
        break;
    case 3:
        desk_paint_entsoe_capacity(dc, &body);
        break;
    case 4:
        {
            GeoWindCtx gw = { dc, body };
            data_store_read(page_geo_wind_cb, &gw);
        }
        break;
    case 5:
        {
            GeoWindCtx gw = { dc, body };
            data_store_read(page_geo_risk_cb, &gw);
        }
        break;
    case 6:
    default:
        ui_frame(dc, &body, L"GEO / POL HEADLINES");
        {
            RECT inner = ui_panel_body(&body);
            intel_paint_ticker(dc, &inner, "GEO", 14);
        }
        break;
    }
}

static void page_ingest(HDC dc, RECT body) {
    ingest_view_paint(dc, &body);
}

static void page_globe(HDC dc, RECT body) {
    globe_view_paint(dc, &body);
}

static void page_news(HDC dc, RECT body) {
    intel_paint_page(dc, &body);
}

/* ---------- CORR + RISK (merged on PAGE_RISK) ---------- */

static void corr_pair_row(HDC dc, int x, int y, const wchar_t *cols[6]) {
    static const int OFF[6] = { 0, 72, 132, 192, 252, 312 };
    int i;

    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    for (i = 0; i < 6; i++) {
        SetTextColor(dc, i >= 2 ? CLR_TXT : CLR_DIM);
        TextOutW(dc, x + OFF[i], y, cols[i], lstrlenW(cols[i]));
    }
}

static void corr_paint_pairs(HDC dc, RECT tbl, const SeriesStore *st,
                             const CorrLink *links, int nlinks, const wchar_t *title) {
    int y, row_h = 15, i, shown = 0;
    const wchar_t *hdr[6] = { L"PAIR", L"\x03C1 30d", L"\x03C1 90d", L"\x03B2(A|B)", L"n", L"link" };

    ui_subheading(dc, &(RECT){ tbl.left, tbl.top, tbl.right, tbl.top + 12 }, title);
    y = tbl.top + 14;
    corr_pair_row(dc, tbl.left, y, hdr);
    y += row_h + 2;
    ui_hline(dc, tbl.left, y - 2, tbl.right, CLR_GRID);

    for (i = 0; i < nlinks; i++) {
        const DataSeries *sa, *sb;
        CorrPair cp;
        wchar_t pair[16], r30[12], r90[12], b90[12], ns[8];
        const wchar_t *cols[6];
        float dr;

        if (y + row_h > tbl.bottom) break;
        sa = series_get((SeriesStore *)st, links[i].a);
        sb = series_get((SeriesStore *)st, links[i].b);
        if (!sa || !sb) continue;
        corr_pair_compute(sa, sb, &cp);
        if (!cp.ok) continue;
        dr = cp.rho30 - cp.rho90;
        if (fabsf(cp.rho90) < 0.3f && fabsf(dr) < 0.15f) continue;
        wsprintfW(pair, L"%hs-%hs", links[i].a, links[i].b);
        ui_fmt_wdouble(r30, 12, cp.rho30, 2);
        ui_fmt_wdouble(r90, 12, cp.rho90, 2);
        ui_fmt_wdouble(b90, 12, cp.beta90, 2);
        wsprintfW(ns, L"%d", cp.n90);
        cols[0] = pair;
        cols[1] = r30;
        cols[2] = r90;
        cols[3] = b90;
        cols[4] = ns;
        cols[5] = links[i].note;
        corr_pair_row(dc, tbl.left, y, cols);
        if (fabsf(dr) >= 0.15f) {
            RECT dot = { tbl.right - 8, y + 4, tbl.right - 2, y + 10 };
            HBRUSH b = CreateSolidBrush(RGB(255, 180, 80));
            FillRect(dc, &dot, b);
            DeleteObject(b);
        }
        y += row_h;
        shown++;
    }
    if (shown == 0 && y + row_h <= tbl.bottom) {
        SetTextColor(dc, CLR_OFF);
        SelectObject(dc, fSm);
        TextOutW(dc, tbl.left, y, L"(nessuna coppia |rho|>0.3 o |d rho| grande)", -1);
    }
}

static void corr_cb(const SeriesStore *st, void *ctx) {
    CorrCtx *c = (CorrCtx *)ctx;
    static const char MAT[12][4] = {
        "BRT", "WTI", "TTF", "HUB", "EUA", "PDE",
        "BTC", "ETH", "CBE", "GRN", "GPR", "VIX"
    };
    static const CorrLink ENERGY_LINKS[] = {
        { "BRT", "WTI", L"arb fisico / crack" },
        { "TTF", "HUB", L"gas Atlantic bridge" },
        { "COA", "TTF", L"dark spread" },
        { "BRT", "VIX", L"risk-off vol" },
        { "CPR", "BRT", L"proxy domanda CN" },
        { "BRT", "SPX", L"risk-on equity" },
        { "JKM", "TTF", L"LNG vs pipe EU" },
        { "BRT", "NGS", L"oil vs US gas stor" },
        { "TTF", "PDE", L"spark spread proxy" },
        { "BRT", "PDE", L"oil vs power DE" },
        { "EUA", "BRT", L"carbon vs oil" },
        { "NGF", "HUB", L"gas futures vs HH" },
        { "GPR", "VIX", L"geopol vs fear" },
        { "CPU", "GPR", L"climate vs geopol" },
    };
    static const CorrLink SYS_LINKS[] = {
        { "BTC", "BRT", L"oil vol spillover ~5%" },
        { "BTC", "HUB", L"mining fuel Henry Hub" },
        { "BTC", "TTF", L"EU gas vs mining" },
        { "BTC", "HAS", L"hashrate intensity" },
        { "BTC", "CBE", L"NARDL mining power" },
        { "BTC", "FEE", L"tx fees vs price" },
        { "BTC", "CVI", L"vol spillover" },
        { "BTC", "EMI", L"carbon footprint" },
        { "BTC", "EUA", L"carbon market" },
        { "GRN", "DIR", L"clean vs dirty" },
        { "GRN", "BTC", L"green vs crypto" },
        { "BTC", "XAU", L"safe haven block" },
        { "BTC", "HYO", L"credit tail risk" },
        { "BTC", "VIX", L"fear gauge" },
        { "BTC", "SPX", L"risk-on equity" },
        { "BTC", "DXY", L"dollar liquidity" },
        { "ETH", "BTC", L"alt beta" },
        { "HYO", "VIX", L"systemic stress duo" },
        { "NAS", "BTC", L"tech risk proxy" },
    };
    RECT banner, mat, left, right, gloss;
    int h = c->body.bottom - c->body.top;

    gloss = c->body;
    gloss.left = gloss.right - 228;
    c->body.right = gloss.left - 8;
    gloss_paint_panel(c->dc, &gloss, PAGE_RISK);

    banner = c->body;
    banner.bottom = c->body.top + h * 14 / 100;
    systemic_paint_banner(c->dc, &banner, st);

    mat = c->body;
    mat.top = banner.bottom + 6;
    mat.bottom = c->body.top + h * 54 / 100;
    ui_subheading(c->dc, &(RECT){ mat.left, mat.top, mat.right, mat.top + 12 },
                  L"MATRICE \x03C1 cluster energia|crypto|macro + \x0394\x03C1");
    mat.top += 14;
    chart_corr_matrix_delta(c->dc, &mat, st, MAT, 12);

    left = c->body;
    left.top = mat.bottom + 8;
    left.right = c->body.left + (c->body.right - c->body.left) / 2 - 4;
    right = c->body;
    right.left = left.right + 8;
    right.top = left.top;

    corr_paint_pairs(c->dc, left, st, ENERGY_LINKS,
                     (int)(sizeof(ENERGY_LINKS) / sizeof(ENERGY_LINKS[0])),
                     L"COPPIE HOT energia  |rho|>0.3");
    corr_paint_pairs(c->dc, right, st, SYS_LINKS,
                     (int)(sizeof(SYS_LINKS) / sizeof(SYS_LINKS[0])),
                     L"COPPIE HOT sistemico");

    gloss_paint_footer(c->dc, &(RECT){ c->body.left, c->body.bottom - 14,
                                       c->body.right, c->body.bottom }, PAGE_RISK);
}

static void page_risk_cb(const SeriesStore *st, void *ctx) {
    typedef struct { HDC dc; RECT body; } RiskCtx;
    RiskCtx *c = (RiskCtx *)ctx;
    risk_paint_page(c->dc, &c->body, st);
}

static void page_risk(HDC dc, RECT body) {
    CorrCtx c;
    RECT top, mid, bot;
    top = body;
    top.bottom = body.top + (body.bottom - body.top) * 52 / 100;
    mid = body;
    mid.top = top.bottom + 4;
    mid.bottom = body.top + (body.bottom - body.top) * 72 / 100;
    bot = body;
    bot.top = mid.bottom + 4;
    c.dc = dc;
    c.body = top;
    data_store_read(corr_cb, &c);
    {
        typedef struct { HDC dc; RECT body; } RiskCtx;
        RiskCtx p = { dc, mid };
        data_store_read(page_risk_cb, &p);
    }
    companies_paint_tiles(dc, &bot);
}

static void page_ships(HDC dc, RECT body) {
    ships_paint(dc, &body);
}

typedef struct {
    HDC dc;
    RECT body;
} CatPageCtx;

static void catalog_page_cb(const SeriesStore *st, void *ctx) {
    CatPageCtx *c = (CatPageCtx *)ctx;
    RECT main, qa;
    main = c->body;
    qa = c->body;
    qa.left = qa.right - 240;
    main.right = qa.left - 8;
    catalog_paint(c->dc, &main, st);
    ui_frame(c->dc, &qa, L"QA");
    {
        RECT qinner = ui_panel_body(&qa);
        qa_paint_panel(c->dc, &qinner);
    }
}

static void page_catalog(HDC dc, RECT body) {
    CatPageCtx c = { dc, body };
    data_store_read(catalog_page_cb, &c);
}

static void page_gas_cb(const SeriesStore *st, void *ctx) {
    PageCtx *p = (PageCtx *)ctx;
    gas_paint(p->dc, &p->body, st);
}

static void page_gas(HDC dc, RECT body) {
    PageCtx p = { dc, body };
    data_store_read(page_gas_cb, &p);
}

static void page_met(HDC dc, RECT body) {
    RECT map, top, mid, bot, ridge;
    int bh;

    if (body.bottom <= body.top + 120) return;
    bh = body.bottom - body.top;
    ridge = body;
    ridge.top = body.bottom - 72;
    if (ridge.top < body.top + bh / 2) ridge.top = body.top + bh / 2;
    body.bottom = ridge.top - 6;
    top = body;
    top.left = top.right - 240;
    top.bottom = body.top + (body.bottom - body.top) * 32 / 100;
    mid = top;
    mid.top = top.bottom + 6;
    mid.bottom = body.top + (body.bottom - body.top) * 62 / 100;
    bot = top;
    bot.top = mid.bottom + 6;
    bot.bottom = body.bottom;
    map = body;
    map.right = top.left - 8;
    if (map.right <= map.left + 40) return;
    weather_paint(dc, &map);
    ui_frame(dc, &top, L"HDD/CDD + ENSO");
    {
        RECT inner = ui_panel_body(&top);
        modules_paint_hdd_enso(dc, &inner);
    }
    ui_frame(dc, &mid, L"WIND DELTA");
    {
        RECT inner = ui_panel_body(&mid);
        modules_paint_wind_delta(dc, &inner);
    }
    ui_frame(dc, &bot, L"METEO SIGNALS + CLI feed");
    {
        RECT inner = ui_panel_body(&bot);
        RECT sig, cli;
        sig = inner;
        sig.bottom = inner.top + (inner.bottom - inner.top) * 55 / 100;
        cli = inner;
        cli.top = sig.bottom + 4;
        modules_paint_weather_panel(dc, &sig);
        intel_paint_ticker(dc, &cli, "CLIMATE", 6);
    }
    ui_frame(dc, &ridge, L"72h VENTO  ridgeline hub EU (proxy)");
    {
        static const wchar_t *HUBS[] = { L"BER", L"PAR", L"LON" };
        WeatherSite wx_snap[WEATHER_SITE_N];
        int wx_n = weather_copy_sites(wx_snap, WEATHER_SITE_N);
        RECT inner = ui_panel_body(&ridge);
        int i, sh = (inner.bottom - inner.top) / 3;

        if (sh < 8) return;
        for (i = 0; i < 3; i++) {
            RECT cell = inner;
            int j;
            cell.top = inner.top + i * sh;
            cell.bottom = cell.top + sh - 2;
            if (cell.bottom <= cell.top) continue;
            for (j = 0; j < wx_n; j++) {
                const WeatherSite *s = &wx_snap[j];
                DataSeries snap;
                int k, fc_n;
                if (!s->ok || lstrcmpW(s->name, HUBS[i]) != 0 || s->fc_n < 4)
                    continue;
                memset(&snap, 0, sizeof(snap));
                fc_n = s->fc_n;
                if (fc_n > WX_FC_H) fc_n = WX_FC_H;
                if (fc_n < 2) continue;
                snap.n = (uint16_t)fc_n;
                snap.live = 0.0f;
                for (k = 0; k < fc_n; k++)
                    snap.val[k] = s->fc_wind[k];
                snap.min_h = snap.val[0];
                snap.max_h = snap.val[0];
                for (k = 1; k < fc_n; k++) {
                    if (snap.val[k] < snap.min_h) snap.min_h = snap.val[k];
                    if (snap.val[k] > snap.max_h) snap.max_h = snap.val[k];
                }
                chart_horizon(dc, &cell, &snap, HUBS[i], CLR_UP, 3);
                break;
            }
        }
    }
}

void pages_paint(HDC dc) {
    RECT body = page_body();

    paint_tabs(dc, &body);
    if (g_page == PAGE_OPS)
        page_ops(dc, body);
    else if (g_page == PAGE_MKT)
        page_markets(dc, body);
    else if (g_page == PAGE_FX)
        page_fx(dc, body);
    else if (g_page == PAGE_NRG)
        page_nrg(dc, body);
    else if (g_page == PAGE_GAS)
        page_gas(dc, body);
    else if (g_page == PAGE_MET)
        page_met(dc, body);
    else if (g_page == PAGE_ASTRO)
        forcing_paint(dc, &body);
    else if (g_page == PAGE_LAB)
        lab_paint(dc, &body);
    else if (g_page == PAGE_SIG)
        sig_paint(dc, &body);
    else if (g_page == PAGE_RISK)
        page_risk(dc, body);
    else if (g_page == PAGE_GEO)
        page_geo(dc, body);
    else if (g_page == PAGE_AIS)
        page_ships(dc, body);
    else if (g_page == PAGE_NEWS)
        page_news(dc, body);
    else if (g_page == PAGE_CAT)
        page_catalog(dc, body);
    else if (g_page == PAGE_INGEST)
        page_ingest(dc, body);
    else if (g_page == PAGE_GLOBE)
        page_globe(dc, body);
}
