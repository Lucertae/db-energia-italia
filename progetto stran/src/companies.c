#include "companies.h"
#include "ingest_stooq.h"
#include "ingest.h"
#include "corr.h"
#include "data.h"
#include "series.h"
#include "chart.h"
#include "glossary.h"
#include <stdio.h>
#include <string.h>

typedef struct {
    const char *sym;
    const wchar_t *name;
    const wchar_t *country;
    const wchar_t *segment;
    uint8_t tier;
} CoDef;

static const CoDef CO_DEF[] = {
    { "xom.us",   L"ExxonMobil",      L"US",   L"integrated",  CO_TIER_MAJOR },
    { "cvx.us",   L"Chevron",         L"US",   L"integrated",  CO_TIER_MAJOR },
    { "shel.uk",  L"Shell",           L"UK",   L"integrated",  CO_TIER_MAJOR },
    { "bp.uk",    L"BP",              L"UK",   L"integrated",  CO_TIER_MAJOR },
    { "tte.fr",   L"TotalEnergies",   L"FR",   L"integrated",  CO_TIER_MAJOR },
    { "eqnr.us",  L"Equinor",         L"NO",   L"integrated",  CO_TIER_MAJOR },
    { "eni.it",   L"Eni",             L"IT",   L"integrated",  CO_TIER_MAJOR },
    { "rep.mc",   L"Repsol",          L"ES",   L"integrated",  CO_TIER_MAJOR },
    { "2222.sa",  L"Saudi Aramco",    L"SA",   L"NOC",         CO_TIER_NATIONAL },
    { "pbr.us",   L"Petrobras",       L"BR",   L"NOC",         CO_TIER_NATIONAL },
    { "ptr.us",   L"PetroChina",      L"CN",   L"NOC",         CO_TIER_NATIONAL },
    { "snpm.us",  L"Sinopec",         L"CN",   L"NOC",         CO_TIER_NATIONAL },
    { "cop.us",   L"ConocoPhillips",  L"US",   L"E&P",         CO_TIER_SEMI },
    { "eog.us",   L"EOG Resources",   L"US",   L"E&P",         CO_TIER_SEMI },
    { "oxy.us",   L"Occidental",      L"US",   L"E&P",         CO_TIER_SEMI },
    { "slb.us",   L"SLB",             L"US",   L"oilfield",    CO_TIER_SEMI },
    { "hal.us",   L"Halliburton",     L"US",   L"oilfield",    CO_TIER_SEMI },
    { "lng.us",   L"Cheniere LNG",    L"US",   L"LNG",         CO_TIER_SEMI },
    { "vlo.us",   L"Valero",          L"US",   L"refining",    CO_TIER_SEMI },
    { "mpc.us",   L"Marathon Petro",  L"US",   L"refining",    CO_TIER_SEMI },
    { "enel.it",  L"Enel",            L"IT",   L"utility",     CO_TIER_UTILITY },
    { "ng.uk",    L"National Grid",   L"UK",   L"utility",     CO_TIER_UTILITY },
    { "eon.de",   L"E.ON",            L"DE",   L"utility",     CO_TIER_UTILITY },
    { "rwe.de",   L"RWE",             L"DE",   L"utility",     CO_TIER_UTILITY },
    { "ibe.mc",   L"Iberdrola",       L"ES",   L"utility",     CO_TIER_UTILITY },
    { "nee.us",   L"NextEra Energy",  L"US",   L"utility",     CO_TIER_UTILITY },
    { "duk.us",   L"Duke Energy",     L"US",   L"utility",     CO_TIER_UTILITY },
    { "engi.pa",  L"Engie",           L"FR",   L"utility",     CO_TIER_UTILITY },
    { "snam.it",  L"Snam",            L"IT",   L"gas distrib", CO_TIER_DISTRIB },
    { "ig.it",    L"Italgas",         L"IT",   L"gas distrib", CO_TIER_DISTRIB },
    { "wmb.us",   L"Williams",        L"US",   L"midstream",   CO_TIER_DISTRIB },
    { "kmi.us",   L"Kinder Morgan",  L"US",   L"midstream",   CO_TIER_DISTRIB },
    { "oke.us",   L"ONEOK",           L"US",   L"midstream",   CO_TIER_DISTRIB },
    { "edp.pt",   L"EDP",             L"PT",   L"utility",     CO_TIER_UTILITY },
    { "orsted.co",L"Orsted",          L"DK",   L"wind util",   CO_TIER_UTILITY },
};

static CompanyQuote g_co[CO_MAX];
static int g_co_n;

static const wchar_t *tier_name(int t) {
    switch (t) {
    case CO_TIER_MAJOR:    return L"MAJOR";
    case CO_TIER_NATIONAL: return L"NOC";
    case CO_TIER_SEMI:     return L"SEMI";
    case CO_TIER_UTILITY:  return L"UTIL";
    case CO_TIER_DISTRIB:  return L"DIST";
    default: return L"?";
    }
}

typedef struct { CompanyQuote *arr; } CoBatchCtx;

static void co_hist_path(const char *sym, wchar_t *path, int cap);
static void co_hist_append(const char *sym, uint32_t ymd, float close);

static void co_batch_cb(const char *sym, float close, float prev, void *ctx) {
    CoBatchCtx *b = (CoBatchCtx *)ctx;
    int i;
    SYSTEMTIME st;

    GetSystemTime(&st);
    for (i = 0; i < g_co_n; i++) {
        if (lstrcmpA(b->arr[i].sym, sym) != 0) continue;
        b->arr[i].price = close;
        b->arr[i].chg_pct = prev > 0.0f ? (close - prev) / prev * 100.0f : 0.0f;
        b->arr[i].have = 1;
        b->arr[i].ymd = (uint32_t)(st.wYear * 10000u + st.wMonth * 100u + st.wDay);
        co_hist_append(sym, b->arr[i].ymd, close);
        return;
    }
}

static void co_hist_path(const char *sym, wchar_t *path, int cap) {
    char safe[24];
    int i, j = 0;

    for (i = 0; sym[i] && j < (int)sizeof(safe) - 2; i++)
        safe[j++] = sym[i] == '.' ? '_' : sym[i];
    safe[j] = 0;
    wsprintfW(path, L"cache\\stooq\\%hs.csv", safe);
    (void)cap;
}

static void co_hist_append(const char *sym, uint32_t ymd, float close) {
    wchar_t path[MAX_PATH];
    FILE *f;
    char last[32];
    int y, m, d;

    if (!sym || close <= 0.0f || ymd < 20000101u) return;
    CreateDirectoryW(L"cache\\stooq", NULL);
    co_hist_path(sym, path, MAX_PATH);
    y = (int)(ymd / 10000u);
    m = (int)((ymd / 100u) % 100u);
    d = (int)(ymd % 100u);
    wsprintfA(last, "%04d-%02d-%02d", y, m, d);

    {
        int newf = 1;
        f = _wfopen(path, L"r");
        if (f) {
            char buf[64], prev[32];
            newf = 0;
            prev[0] = 0;
            while (fgets(buf, (int)sizeof(buf), f)) {
                if (buf[0] >= '0' && buf[0] <= '9' && buf[4] == '-')
                    lstrcpynA(prev, buf, (int)sizeof(prev));
            }
            fclose(f);
            if (prev[0] && lstrcmpA(prev, last) == 0) return;
        }
        f = _wfopen(path, L"a");
        if (!f) return;
        if (newf) fprintf(f, "DATE,VALUE\n");
        fprintf(f, "%04d-%02d-%02d,%.6f\n", y, m, d, close);
        fclose(f);
    }
}

static int co_hist_load(const char *sym, DataSeries *out) {
    wchar_t path[MAX_PATH];
    static char body[65536];
    size_t len = 0;
    FILE *f;
    static uint32_t ymd[SER_POINTS];
    static float val[SER_POINTS];
    int n;

    if (!sym || !out) return 0;
    memset(out, 0, sizeof(*out));
    co_hist_path(sym, path, MAX_PATH);
    f = _wfopen(path, L"r");
    if (!f) return 0;
    len = fread(body, 1, sizeof(body) - 1, f);
    fclose(f);
    body[len] = 0;
    n = ingest_fred_hist(body, len, ymd, val, SER_POINTS);
    if (n < 5) return 0;
    out->n = (uint16_t)n;
    memcpy(out->ymd, ymd, (size_t)n * sizeof(ymd[0]));
    memcpy(out->val, val, (size_t)n * sizeof(val[0]));
    out->live = val[n - 1];
    return 1;
}

static float co_rho_spx(const char *sym) {
    DataSeries co, spx;
    CorrPair cp;

    if (!co_hist_load(sym, &co)) return 0.0f;
    if (!data_series_snap("SPX", &spx) || spx.n < 5) return 0.0f;
    corr_pair_compute(&co, &spx, &cp);
    return cp.ok ? cp.rho90 : 0.0f;
}

void companies_init(void) {
    int i, n = (int)(sizeof(CO_DEF) / sizeof(CO_DEF[0]));

    if (n > CO_MAX) n = CO_MAX;
    g_co_n = n;
    memset(g_co, 0, sizeof(g_co));
    for (i = 0; i < n; i++) {
        lstrcpynA(g_co[i].sym, CO_DEF[i].sym, (int)sizeof(g_co[i].sym));
        lstrcpynW(g_co[i].name, CO_DEF[i].name, (int)(sizeof(g_co[i].name) / sizeof(wchar_t)));
        lstrcpynW(g_co[i].country, CO_DEF[i].country, (int)(sizeof(g_co[i].country) / sizeof(wchar_t)));
        lstrcpynW(g_co[i].segment, CO_DEF[i].segment, (int)(sizeof(g_co[i].segment) / sizeof(wchar_t)));
        g_co[i].tier = CO_DEF[i].tier;
    }
}

int companies_count(void) { return g_co_n; }

const CompanyQuote *companies_get(int i) {
    if (i < 0 || i >= g_co_n) return NULL;
    return &g_co[i];
}

void companies_refresh(void) {
    int batch, nbatch, i, cnt, base;
    const char *syms[16];
    CoBatchCtx ctx;

    if (g_co_n <= 0) companies_init();
    ctx.arr = g_co;
    nbatch = (g_co_n + 15) / 16;
    for (batch = 0; batch < nbatch; batch++) {
        base = batch * 16;
        cnt = g_co_n - base;
        if (cnt > 16) cnt = 16;
        for (i = 0; i < cnt; i++) syms[i] = g_co[base + i].sym;
        ingest_stooq_batch(syms, cnt, co_batch_cb, &ctx);
    }
}

void companies_paint(HDC dc, const RECT *rc, int filter_tier) {
    RECT r = *rc, gloss, sparks, cell;
    int row_h = 15, y, i, w4;
    wchar_t px[16], chg[16], seg[48];
    DataSeries co_snap;

    if (r.bottom <= r.top + 12) return;

    gloss = r;
    gloss.left = gloss.right - 228;
    r.right = gloss.left - 8;
    gloss_paint_panel(dc, &gloss, PAGE_GEO);

    sparks = r;
    sparks.bottom = r.top + 88;
    ui_subheading(dc, &(RECT){ sparks.left, sparks.top, sparks.right, sparks.top + 12 },
                  L"MAJORS  storico Stooq");
    sparks.top += 14;
    w4 = (sparks.right - sparks.left) / 4;
    for (i = 0; i < 4 && i < g_co_n; i++) {
        if (!co_hist_load(g_co[i].sym, &co_snap)) continue;
        cell.left = sparks.left + i * w4;
        cell.right = cell.left + w4 - 4;
        cell.top = sparks.top;
        cell.bottom = sparks.bottom;
        chart_series_cell(dc, &cell, &co_snap);
    }
    y = sparks.bottom + 6;
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    SetTextColor(dc, CLR_DIM);
    TextOutW(dc, r.left, y, L"TIER   NAME                 CN   SEGMENT           PX      CHG%   \x03C1 SPX", 62);
    y += row_h + 2;
    ui_hline(dc, r.left, y - 2, r.right, CLR_GRID);

    for (i = 0; i < g_co_n; i++) {
        const CompanyQuote *c = &g_co[i];
        RECT dot;
        HBRUSH br;
        if (filter_tier >= 0 && c->tier != (uint8_t)filter_tier) continue;
        if (y + row_h > r.bottom) break;
        dot = (RECT){ r.left, y + 4, r.left + 5, y + 9 };
        br = CreateSolidBrush(c->have ? (c->chg_pct >= 0.0f ? CLR_UP : CLR_DN) : CLR_OFF);
        FillRect(dc, &dot, br);
        DeleteObject(br);
        if (!c->have) {
            SetTextColor(dc, CLR_OFF);
            wsprintfW(seg, L"%-5s %-20s %-4s %-16s  --", tier_name(c->tier),
                      c->name, c->country, c->segment);
        } else {
            ui_fmt_wdouble(px, 16, c->price, c->price > 100.0f ? 1 : 2);
            ui_fmt_wdouble(chg, 16, c->chg_pct >= 0.0f ? c->chg_pct : -c->chg_pct, 2);
            SetTextColor(dc, c->chg_pct >= 0.0f ? CLR_UP : CLR_DN);
            wsprintfW(seg, L"%-5s %-20s %-4s %-16s %6s %s%s", tier_name(c->tier),
                      c->name, c->country, c->segment, px,
                      c->chg_pct >= 0.0f ? L"+" : L"-", chg);
        }
        TextOutW(dc, r.left + 8, y, seg, lstrlenW(seg));
        {
            float rho = co_rho_spx(c->sym);
            wchar_t rs[12];
            if (rho != 0.0f) {
                ui_fmt_wdouble(rs, 12, rho, 2);
                SetTextColor(dc, CLR_DIM);
                TextOutW(dc, r.left + 420, y, rs, lstrlenW(rs));
            }
        }
        y += row_h;
    }
    gloss_paint_footer(dc, &(RECT){ r.left, r.bottom - 14, r.right, r.bottom },
                       PAGE_GEO);
}

void companies_paint_tiles(HDC dc, const RECT *rc) {
    static const int PICK[] = {
        0, 1, 2, 3, 4, 5, 6, 12, 13, 14, 15, 16, 17, 18, 19
    };
    RECT r = *rc, cell;
    int i, cols = 5, cw, ch, y0 = r.top;
    wchar_t line[48];

    if (g_co_n <= 0) companies_init();
    ui_subheading(dc, &(RECT){ r.left, y0, r.right, y0 + 12 },
                  L"EQUITY ENERGY  rho vs SPX");
    y0 += 14;
    cw = (r.right - r.left) / cols;
    ch = (r.bottom - y0) / 3;
    if (ch < 24) ch = 24;
    for (i = 0; i < 15; i++) {
        const CompanyQuote *c;
        int idx = PICK[i];
        float rho;
        int col = i % cols;
        int row = i / cols;
        if (idx < 0 || idx >= g_co_n) continue;
        c = &g_co[idx];
        cell.left = r.left + col * cw;
        cell.right = cell.left + cw - 4;
        cell.top = y0 + row * ch;
        cell.bottom = cell.top + ch - 4;
        if (cell.bottom > r.bottom) break;
        FillRect(dc, &cell, bBand);
        rho = co_rho_spx(c->sym);
        if (c->have) {
            wchar_t chg[12];
            ui_fmt_wdouble(chg, 12, c->chg_pct, 1);
            wsprintfW(line, L"%-8s %+0.1f%%", c->name, c->chg_pct);
            SetTextColor(dc, c->chg_pct >= 0.0f ? CLR_UP : CLR_DN);
        } else {
            wsprintfW(line, L"%-8s --", c->name);
            SetTextColor(dc, CLR_OFF);
        }
        SelectObject(dc, fSm);
        DrawTextW(dc, line, -1, &cell, DT_LEFT | DT_TOP | DT_SINGLELINE | DT_NOPREFIX);
        if (rho != 0.0f) {
            RECT sub = cell;
            wchar_t rs[16];
            sub.top += 12;
            ui_fmt_wdouble(rs, 16, rho, 2);
            wsprintfW(line, L"rho %s", rs);
            SetTextColor(dc, CLR_DIM);
            DrawTextW(dc, line, -1, &sub, DT_LEFT | DT_TOP | DT_SINGLELINE | DT_NOPREFIX);
        }
    }
}
