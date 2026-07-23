#include "catalog.h"
#include "sources.h"
#include "chart.h"
#include "fin.h"
#include <math.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>

#define CAT_MAX   160
#define CAT_VIS   22
#define CAT_LINE  15

typedef struct {
    char     id[4];
    wchar_t  label[24];
    wchar_t  provider[14];
    wchar_t  stream[28];
    wchar_t  unit[14];
    wchar_t  freq[10];
    wchar_t  db[22];
    wchar_t  desc[56];
    uint8_t  kind;
    uint8_t  prov_code;
} CatEntry;

typedef struct {
    CatEntry e[CAT_MAX];
    int n;
} CatIndex;

static wchar_t g_search[40];
static int g_prov = 0;
static int g_sel;
static int g_scroll;
static RECT g_list_rc;
static CatIndex g_idx;
static char g_sel_id[4];
static int g_idx_dirty = 1;

static void cat_build(CatIndex *ix);
static void cat_ensure(void) {
    if (g_idx_dirty) {
        cat_build(&g_idx);
        g_idx_dirty = 0;
    }
}

static const wchar_t *PROV_NAMES[] = {
    L"ALL", L"FRED", L"ENTSO-E", L"EIA", L"ECB", L"CRYPTO", L"LIBERO", L"STOOQ"
};

static void wlower(wchar_t *s) {
    for (; *s; s++) {
        if (*s >= L'A' && *s <= L'Z') *s = (wchar_t)(*s - L'A' + L'a');
    }
}

static BOOL wcontains(const wchar_t *hay, const wchar_t *needle) {
    wchar_t h[64], n[40];

    if (!needle || !needle[0]) return TRUE;
    lstrcpynW(h, hay, 64);
    lstrcpynW(n, needle, 40);
    wlower(h);
    wlower(n);
    return wcsstr(h, n) != NULL;
}

static uint8_t prov_code(const wchar_t *p) {
    if (!wcscmp(p, L"FRED")) return 1;
    if (!wcscmp(p, L"ENTSO-E")) return 2;
    if (!wcscmp(p, L"EIA")) return 3;
    if (!wcscmp(p, L"ECB")) return 4;
    if (!wcscmp(p, L"CRYPTO")) return 5;
    if (!wcscmp(p, L"LIBERO")) return 6;
    if (!wcscmp(p, L"STOOQ")) return 7;
    return 0;
}

static void meta_libero(CatEntry *e, const char *id) {
    static const struct { const char *id; const wchar_t *u; const wchar_t *f; const wchar_t *d; } L[] = {
        { "CBE", L"GWh", L"weekly", L"Cambridge Bitcoin Electricity" },
        { "EMI", L"tCO2", L"daily", L"BTC network emissions" },
        { "CVI", L"idx", L"daily", L"Crypto volatility index (BTC RV)" },
        { "FEE", L"BTC", L"daily", L"Mean transaction fees" },
        { "DIF", L"idx", L"daily", L"BTC mining difficulty" },
        { "REV", L"USD", L"daily", L"Miner revenue estimate" },
        { "BVL", L"USD", L"daily", L"BTC traded volume" },
        { "MCP", L"USD", L"daily", L"BTC market cap" },
        { "GPR", L"idx", L"monthly", L"Geopolitical risk index" },
        { "CPU", L"idx", L"monthly", L"Climate policy uncertainty" },
        { "EUA", L"EUR/t", L"daily", L"EU ETS carbon futures" },
        { "GRN", L"USD", L"daily", L"Clean energy ETF basket" },
        { "DIR", L"USD", L"daily", L"Fossil energy ETF basket" },
        { "NGF", L"USD/MMBtu", L"daily", L"US natural gas front future" },
        { "HAS", L"EH/s", L"daily", L"BTC network hashrate" },
    };
    int i;

    lstrcpynW(e->provider, L"LIBERO", 14);
    lstrcpynW(e->db, L"libero.db", 22);
    lstrcpynW(e->stream, L"export CSV", 28);
    for (i = 0; i < (int)(sizeof(L) / sizeof(L[0])); i++) {
        if (strncmp(L[i].id, id, 3) == 0) {
            lstrcpynW(e->unit, L[i].u, 14);
            lstrcpynW(e->freq, L[i].f, 10);
            lstrcpynW(e->desc, L[i].d, 56);
            return;
        }
    }
    lstrcpynW(e->unit, L"—", 14);
    lstrcpynW(e->freq, L"daily", 10);
    lstrcpynW(e->desc, L"Libero macro series", 56);
}

static void meta_power(CatEntry *e, const char *id) {
    static const struct { const char *id; const wchar_t *lbl; const wchar_t *eic; } Z[] = {
        { "PDE", L"PWR DE", L"10Y1001A1001A82H" },
        { "PFR", L"PWR FR", L"10YFR-RTE------C" },
        { "PIT", L"PWR IT", L"10Y1001A1001A73I" },
        { "PNL", L"PWR NL", L"10YNL----------L" },
        { "PPL", L"PWR PL", L"10YPL-AREA-----S" },
        { "PNO", L"PWR NO", L"10YNO-0--------2" },
        { "PAT", L"PWR AT", L"10YAT-APG------L" },
    };
    int i;

    lstrcpynW(e->provider, L"ENTSO-E", 14);
    lstrcpynW(e->db, L"transparency.entsoe.eu", 22);
    lstrcpynW(e->stream, L"A44 day-ahead", 28);
    lstrcpynW(e->unit, L"EUR/MWh", 14);
    lstrcpynW(e->freq, L"hourly", 10);
    for (i = 0; i < (int)(sizeof(Z) / sizeof(Z[0])); i++) {
        if (strncmp(Z[i].id, id, 3) == 0) {
            lstrcpynW(e->label, Z[i].lbl, 24);
            wsprintfW(e->desc, L"DA price zone %s", Z[i].eic);
            return;
        }
    }
    lstrcpynW(e->desc, L"EU power day-ahead", 56);
}

static void meta_crypto(CatEntry *e, const char *id) {
    static const struct { const char *id; const wchar_t *n; const char *bin; } C[] = {
        { "BTC", L"Bitcoin", "BTCUSDT" }, { "ETH", L"Ethereum", "ETHUSDT" },
        { "SOL", L"Solana", "SOLUSDT" }, { "BNB", L"BNB", "BNBUSDT" },
        { "XRP", L"Ripple", "XRPUSDT" }, { "ADA", L"Cardano", "ADAUSDT" },
        { "DOT", L"Polkadot", "DOTUSDT" }, { "LNK", L"Chainlink", "LINKUSDT" },
        { "AVX", L"Avalanche", "AVAXUSDT" }, { "MAT", L"Polygon", "POLUSDT" },
        { "DOG", L"Dogecoin", "DOGEUSDT" }, { "LTC", L"Litecoin", "LTCUSDT" },
        { "UDC", L"USD Coin", "USDCUSDT" },
    };
    int i;

    e->kind = SER_CRYPTO;
    lstrcpynW(e->provider, L"CRYPTO", 14);
    lstrcpynW(e->db, L"api.binance.com", 22);
    lstrcpynW(e->unit, L"USD", 14);
    lstrcpynW(e->freq, L"1m live", 10);
    for (i = 0; i < (int)(sizeof(C) / sizeof(C[0])); i++) {
        if (strncmp(C[i].id, id, 3) == 0) {
            lstrcpynW(e->label, C[i].n, 24);
            wsprintfW(e->stream, L"klines %hs", C[i].bin);
            lstrcpynW(e->desc, L"Binance spot + Kraken cross-check", 56);
            return;
        }
    }
}

static void meta_from_source(CatEntry *e, const SourceDef *def) {
    e->kind = def->ser_kind;
    lstrcpynW(e->label, def->label, 24);
    if (def->backend == SRC_FRED && def->fred_id) {
        lstrcpynW(e->provider, L"FRED", 14);
        lstrcpynW(e->db, L"fred.stlouisfed.org", 22);
        wsprintfW(e->stream, L"%hs", def->fred_id);
        lstrcpynW(e->freq, L"daily", 10);
        if (def->ser_kind == SER_FX) {
            lstrcpynW(e->unit, L"USD", 14);
            lstrcpynW(e->desc, L"USD per foreign currency", 56);
        } else if (def->ser_kind == SER_RATE) {
            lstrcpynW(e->unit, L"%", 14);
            lstrcpynW(e->desc, L"Policy / sovereign yield", 56);
        } else if (def->ser_kind == SER_ENERGY) {
            lstrcpynW(e->unit, L"USD/bbl or /MMBtu", 14);
            lstrcpynW(e->desc, L"Commodity benchmark", 56);
        } else {
            lstrcpynW(e->unit, L"idx", 14);
            lstrcpynW(e->desc, L"Macro / sentiment index", 56);
        }
        return;
    }
    if (def->backend == SRC_EIA) {
        if (strncmp(def->id, "CRU", 3) == 0 || strncmp(def->id, "NGS", 3) == 0) {
            lstrcpynW(e->provider, L"EIA", 14);
            lstrcpynW(e->db, L"eia.gov public", 22);
            lstrcpynW(e->stream, L"LeafHandler weekly", 28);
            lstrcpynW(e->unit, strncmp(def->id, "NGS", 3) == 0 ? L"BCF" : L"kbbl", 14);
            lstrcpynW(e->freq, L"weekly", 10);
            lstrcpynW(e->desc, L"US inventory — no API key", 56);
            return;
        }
        meta_libero(e, def->id);
        return;
    }
    lstrcpynW(e->provider, L"CACHE", 14);
    lstrcpynW(e->db, L"cache/*.csv", 22);
    lstrcpynW(e->stream, L"local", 28);
}

static void cat_add(CatIndex *ix, const char *id, void (*fill)(CatEntry *, const char *)) {
    CatEntry e;

    if (ix->n >= CAT_MAX) return;
    memset(&e, 0, sizeof(e));
    lstrcpynA(e.id, id, 4);
    if (fill) fill(&e, id);
    else {
        lstrcpynW(e.label, L"—", 24);
        lstrcpynW(e.provider, L"CACHE", 14);
    }
    e.prov_code = prov_code(e.provider);
    ix->e[ix->n++] = e;
}

static void cat_build(CatIndex *ix) {
    static const char *CRYPTO[] = {
        "BTC","ETH","SOL","BNB","XRP","ADA","DOT","LNK","AVX","MAT","DOG","LTC","UDC"
    };
    static const char *PWR[] = { "PDE","PFR","PIT","PNL","PPL","PNO","PAT" };
    static const char *CROSS[] = {
        "USD","JPY","GBP","BRL","ZAR","INR","CNY","MXN","ENK","ESK"
    };
    int i;

    ix->n = 0;
    for (i = 0; i < g_sources_n; i++) {
        const SourceDef *def = &g_sources[i];
        CatEntry e;
        memset(&e, 0, sizeof(e));
        lstrcpynA(e.id, def->id, 4);
        meta_from_source(&e, def);
        e.prov_code = prov_code(e.provider);
        if (ix->n < CAT_MAX) ix->e[ix->n++] = e;
    }
    for (i = 0; i < (int)(sizeof(PWR) / sizeof(PWR[0])); i++)
        cat_add(ix, PWR[i], meta_power);
    for (i = 0; i < (int)(sizeof(CRYPTO) / sizeof(CRYPTO[0])); i++)
        cat_add(ix, CRYPTO[i], meta_crypto);
    for (i = 0; i < (int)(sizeof(CROSS) / sizeof(CROSS[0])); i++) {
        CatEntry e;
        memset(&e, 0, sizeof(e));
        lstrcpynA(e.id, CROSS[i], 4);
        lstrcpynW(e.provider, L"ECB", 14);
        lstrcpynW(e.db, L"ecb.europa.eu", 22);
        lstrcpynW(e.stream, L"eurofxref-daily", 28);
        lstrcpynW(e.unit, L"EUR", 14);
        lstrcpynW(e.freq, L"live 2m", 10);
        lstrcpynW(e.desc, L"Derived EUR cross from ECB + FRED", 56);
        e.kind = SER_FX;
        e.prov_code = 4;
        wsprintfW(e.label, L"EUR/%hs", CROSS[i]);
        if (ix->n < CAT_MAX) ix->e[ix->n++] = e;
    }
}

static BOOL cat_match(const CatEntry *e) {
    wchar_t idw[8];

    if (g_prov > 0 && e->prov_code != (uint8_t)g_prov) return FALSE;
    if (!g_search[0]) return TRUE;
    idw[0] = (wchar_t)e->id[0];
    idw[1] = (wchar_t)e->id[1];
    idw[2] = (wchar_t)e->id[2];
    idw[3] = 0;
    if (wcontains(idw, g_search)) return TRUE;
    if (wcontains(e->label, g_search)) return TRUE;
    if (wcontains(e->provider, g_search)) return TRUE;
    if (wcontains(e->stream, g_search)) return TRUE;
    if (wcontains(e->desc, g_search)) return TRUE;
    if (wcontains(e->db, g_search)) return TRUE;
    return FALSE;
}

static int cat_visible(const CatIndex *ix, int out_idx[CAT_MAX]) {
    int i, n = 0;
    for (i = 0; i < ix->n && n < CAT_MAX; i++) {
        if (cat_match(&ix->e[i]))
            out_idx[n++] = i;
    }
    return n;
}

static void ymd_fmt(uint32_t ymd, wchar_t *out, int cap) {
    wsprintfW(out, L"%04u-%02u-%02u",
        ymd / 10000u, (ymd / 100u) % 100u, ymd % 100u);
}

static void paint_attrs(HDC dc, RECT r, const CatEntry *e, const DataSeries *s) {
    wchar_t line[96], v[20], d0[16], d1[16];
    RECT row = r;
    float z, rv, dd;
    int y = r.top;

    row.bottom = row.top + 14;
    wsprintfW(line, L"%s  [%hs]", e->label, e->id);
    ui_subheading(dc, &row, line);
    y += 16;

    #define ATTR(lbl, val) do { \
        row.top = y; row.bottom = y + CAT_LINE; \
        wsprintfW(line, L"%-10s %s", lbl, val); \
        SetTextColor(dc, CLR_DIM); SelectObject(dc, fSm); \
        DrawTextW(dc, line, -1, &row, DT_LEFT | DT_SINGLELINE | DT_NOPREFIX); \
        y += CAT_LINE; \
    } while (0)

    ATTR(L"provider", e->provider);
    ATTR(L"database", e->db);
    ATTR(L"stream", e->stream);
    ATTR(L"unit", e->unit);
    ATTR(L"freq", e->freq);
    ATTR(L"desc", e->desc);

    if (s && s->n >= 2) {
        ui_fmt_wdouble(v, 20, series_last(s), s->val[s->n - 1] >= 100.0f ? 2 : 4);
        ATTR(L"last", v);
        ui_fmt_wdouble(v, 20, s->live > 0 ? s->live : series_last(s), 4);
        ATTR(L"live", v);
        wsprintfW(line, L"%d pts", s->n);
        ATTR(L"history", line);
        ymd_fmt(s->ymd[0], d0, 16);
        ymd_fmt(s->ymd[s->n - 1], d1, 16);
        wsprintfW(line, L"%s → %s", d0, d1);
        ATTR(L"range", line);
        ui_fmt_wdouble(v, 20, s->min_h, 2);
        ATTR(L"min", v);
        ui_fmt_wdouble(v, 20, s->max_h, 2);
        ATTR(L"max", v);
        rv = fin_rv_ann_pct(s, 90, e->kind == SER_CRYPTO);
        if (rv > 0.0f) {
            ui_fmt_wdouble(v, 20, rv, 1);
            wsprintfW(line, L"%s %% ann", v);
            ATTR(L"RV90", line);
        }
        z = fin_level_zscore(s, 90);
        if (z == z && fabsf(z) < 50.0f) {
            ui_fmt_wdouble(v, 20, z, 2);
            ATTR(L"z90", v);
        }
        dd = fin_max_dd_pct(s);
        if (dd > 0.0f) {
            ui_fmt_wdouble(v, 20, dd, 1);
            wsprintfW(line, L"-%s %%", v);
            ATTR(L"maxDD", line);
        }
    } else {
        ATTR(L"status", L"no data in cache");
    }
    #undef ATTR
}

void catalog_paint(HDC dc, const RECT *body, const SeriesStore *st) {
    static int vis_idx[CAT_MAX];
    RECT area = *body, list, detail, chart_rc, chip, srch;
    wchar_t buf[80];
    int vis_n, i, y, li;
    const CatEntry *sel = NULL;
    const DataSeries *ssel = NULL;

    cat_ensure();
    vis_n = cat_visible(&g_idx, vis_idx);
    if (g_sel >= vis_n) g_sel = vis_n > 0 ? vis_n - 1 : 0;
    if (g_scroll > g_sel) g_scroll = g_sel;
    if (g_sel >= g_scroll + CAT_VIS) g_scroll = g_sel - CAT_VIS + 1;
    if (g_scroll < 0) g_scroll = 0;
    if (vis_n > 0) {
        sel = &g_idx.e[vis_idx[g_sel]];
        lstrcpynA(g_sel_id, sel->id, 4);
        ssel = series_get((SeriesStore *)st, sel->id);
    } else
        g_sel_id[0] = 0;

    area.top += 2;
    srch = area;
    srch.bottom = srch.top + 18;
    wsprintfW(buf, L"SEARCH: %s_", g_search);
    SetBkMode(dc, TRANSPARENT);
    SetTextColor(dc, CLR_ACC);
    SelectObject(dc, fSm);
    DrawTextW(dc, buf, -1, &srch, DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX);
    area.top = srch.bottom + 4;

    chip = area;
    chip.bottom = chip.top + 16;
    for (i = 0; i < (int)(sizeof(PROV_NAMES) / sizeof(PROV_NAMES[0])); i++) {
        int cw = 58;
        RECT c = { chip.left + i * (cw + 3), chip.top, chip.left + i * (cw + 3) + cw, chip.bottom };
        FillRect(dc, &c, (i == g_prov) ? bWhite : bBand);
        SetTextColor(dc, (i == g_prov) ? CLR_BG : CLR_DIM);
        DrawTextW(dc, (wchar_t *)PROV_NAMES[i], -1, &c,
                  DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX);
    }
    area.top = chip.bottom + 6;

    list = area;
    list.right = list.left + 280;
    g_list_rc = list;
    detail.left = list.right + 8;
    detail.right = area.right;
    detail.top = area.top;
    detail.bottom = area.bottom;

    chart_rc = detail;
    chart_rc.bottom = detail.top + (detail.bottom - detail.top) * 55 / 100;
    if (ssel && ssel->n >= 2) {
        wchar_t title[32];
        wsprintfW(title, L"%s  %hs", sel->label, sel->id);
        ui_frame(dc, &chart_rc, title);
        {
            RECT inner = ui_panel_body(&chart_rc);
            chart_sparkline(dc, &inner, ssel, CLR_LINE, CLR_UP);
        }
    } else if (sel) {
        ui_frame(dc, &chart_rc, L"no series data");
    }

    {
        RECT attr = detail;
        attr.top = chart_rc.bottom + 6;
        ui_frame(dc, &attr, L"ATTRIBUTES");
        if (sel) {
            RECT inner = ui_panel_body(&attr);
            paint_attrs(dc, inner, sel, ssel);
        }
    }

    ui_frame(dc, &list, L"STREAMS");
    {
        RECT inner = ui_panel_body(&list);
        y = inner.top;
        wsprintfW(buf, L"%d / %d streams", vis_n, g_idx.n);
        SetTextColor(dc, CLR_OFF);
        SelectObject(dc, fSm);
        TextOutW(dc, inner.left, y, buf, lstrlenW(buf));
        y += 14;

        for (li = 0; li < CAT_VIS; li++) {
            int vi = g_scroll + li;
            RECT row;
            wchar_t rowtxt[48];
            COLORREF fg;

            if (vi >= vis_n) break;
            row = inner;
            row.top = y;
            row.bottom = y + CAT_LINE;
            {
                const CatEntry *e = &g_idx.e[vis_idx[vi]];
                const DataSeries *ds = series_get((SeriesStore *)st, e->id);
                wchar_t lv[12];

                if (ds && ds->n > 0)
                    ui_fmt_wdouble(lv, 12, series_last(ds), ds->val[ds->n - 1] >= 100 ? 1 : 3);
                else
                    lstrcpyW(lv, L"—");
                wsprintfW(rowtxt, L"%hs %-10s %s", e->id, e->provider, lv);
            }
            if (vi == g_sel) {
                FillRect(dc, &row, bBand);
                fg = CLR_ACC;
            } else {
                fg = CLR_DIM;
            }
            SetTextColor(dc, fg);
            DrawTextW(dc, rowtxt, -1, &row, DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX);
            y += CAT_LINE;
        }
    }
}

int catalog_prov_hit(POINT pt) {
    RECT chip;
    int i;

    if (!g_list_rc.top) return -1;
    chip.left = g_list_rc.left;
    chip.top = g_list_rc.top - 22;
    chip.bottom = chip.top + 16;
    for (i = 0; i < (int)(sizeof(PROV_NAMES) / sizeof(PROV_NAMES[0])); i++) {
        int cw = 58;
        RECT c = { chip.left + i * (cw + 3), chip.top, chip.left + i * (cw + 3) + cw, chip.bottom };
        if (PtInRect(&c, pt)) return i;
    }
    return -1;
}

int catalog_list_hit(POINT pt) {
    static int vis_idx[CAT_MAX];
    RECT inner;
    int vis_n, y, li;

    if (!PtInRect(&g_list_rc, pt)) return -1;
    cat_ensure();
    vis_n = cat_visible(&g_idx, vis_idx);
    inner = ui_panel_body(&g_list_rc);
    y = inner.top + 14;
    for (li = 0; li < CAT_VIS; li++) {
        int vi = g_scroll + li;
        RECT row = { inner.left, y, inner.right, y + CAT_LINE };
        if (vi >= vis_n) break;
        if (PtInRect(&row, pt)) return vi;
        y += CAT_LINE;
    }
    return -1;
}

void catalog_key_char(wchar_t ch) {
    int n = lstrlenW(g_search);
    if (ch == 8 || ch == 127) {
        if (n > 0) g_search[n - 1] = 0;
    } else if (ch >= 32 && n < (int)(sizeof(g_search) / sizeof(g_search[0])) - 1) {
        g_search[n] = ch;
        g_search[n + 1] = 0;
    }
    g_sel = 0;
    g_scroll = 0;
    g_idx_dirty = 1;
}

void catalog_clear_search(void) {
    g_search[0] = 0;
    g_sel = 0;
    g_scroll = 0;
    g_idx_dirty = 1;
}

void catalog_key_down(int vk) {
    static int vis_idx[CAT_MAX];
    int vis_n;

    cat_ensure();
    vis_n = cat_visible(&g_idx, vis_idx);
    if (vis_n <= 0) return;
    if (vk == VK_DOWN) {
        if (g_sel + 1 < vis_n) g_sel++;
    } else if (vk == VK_UP) {
        if (g_sel > 0) g_sel--;
    } else if (vk == VK_NEXT) {
        g_sel += CAT_VIS;
        if (g_sel >= vis_n) g_sel = vis_n - 1;
    } else if (vk == VK_PRIOR) {
        g_sel -= CAT_VIS;
        if (g_sel < 0) g_sel = 0;
    } else if (vk == VK_HOME) {
        g_sel = 0;
    } else if (vk == VK_END) {
        g_sel = vis_n - 1;
    }
}

const char *catalog_selected_id(void) {
    return g_sel_id[0] ? g_sel_id : NULL;
}

void catalog_set_prov(int p) {
    if (p >= 0 && p < (int)(sizeof(PROV_NAMES) / sizeof(PROV_NAMES[0]))) {
        g_prov = p;
        g_sel = 0;
        g_scroll = 0;
        g_idx_dirty = 1;
    }
}

void catalog_select_idx(int idx) {
    static int vis_idx[CAT_MAX];
    int vis_n;

    cat_ensure();
    vis_n = cat_visible(&g_idx, vis_idx);
    if (idx >= 0 && idx < vis_n)
        g_sel = idx;
}
