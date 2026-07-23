#include "modules.h"
#include "chart.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define MOD_MAX       32
#define MOD_CYCLES    6
#define MOD_CARRY     12
#define MOD_WXSIG     8
#define MOD_BUF       (96 * 1024)

static ModuleRow g_mod[MOD_MAX];
static int g_mod_n;
static char g_mod_brief[128];
static FxCycleRow g_cyc[MOD_CYCLES];
static int g_cyc_n;
static FxCarryRow g_carry[MOD_CARRY];
static int g_carry_n;
static char g_fx_graph_note[120];
static int g_fx_edge_n;
static int g_fx_ccy_n;
static WeatherSigRow g_wxsig[MOD_WXSIG];
static int g_wxsig_n;
static WindDeltaRow g_wxd[4];
static int g_wxd_n;
static HddZoneRow g_hdd[8];
static int g_hdd_n;
static EnsoSnap g_enso;
static char g_mod_ts[32];

static const char *json_str(const char *obj, const char *key, char *out, int cap) {
    char pat[48];
    const char *p, *q;

    if (!obj || !key || !out || cap < 2) return NULL;
    wsprintfA(pat, "\"%s\":\"", key);
    p = strstr(obj, pat);
    if (!p) return NULL;
    p += strlen(pat);
    q = strchr(p, '"');
    if (!q || (int)(q - p) >= cap) return NULL;
    memcpy(out, p, (size_t)(q - p));
    out[q - p] = 0;
    return out;
}

static int json_bool(const char *obj, const char *key) {
    char pat[48];
    const char *p;

    wsprintfA(pat, "\"%s\":", key);
    p = strstr(obj, pat);
    if (!p) return 0;
    p += strlen(pat);
    while (*p == ' ') p++;
    return strncmp(p, "true", 4) == 0;
}

static float json_float(const char *obj, const char *key, float def) {
    char pat[48];
    const char *p;

    wsprintfA(pat, "\"%s\":", key);
    p = strstr(obj, pat);
    if (!p) return def;
    return (float)atof(p + strlen(pat));
}

static BOOL read_file_utf8(const wchar_t *wpath, char *buf, size_t cap, size_t *out_n) {
    FILE *f = _wfopen(wpath, L"r");

    if (!f || !buf || cap < 2) return FALSE;
    *out_n = fread(buf, 1, cap - 1, f);
    fclose(f);
    buf[*out_n] = 0;
    return TRUE;
}

static void parse_modules_index(const char *json) {
    const char *p, *obj;
    char block[640];

    g_mod_n = 0;
    g_mod_brief[0] = 0;
    g_mod_ts[0] = 0;
    json_str(json, "brief", g_mod_brief, (int)sizeof(g_mod_brief));
    json_str(json, "built_at", g_mod_ts, (int)sizeof(g_mod_ts));

    p = strstr(json, "\"modules\"");
    if (!p) return;
    obj = strchr(p, '[');
    if (!obj) return;

    while (g_mod_n < MOD_MAX && (obj = strstr(obj, "\"module\":")) != NULL) {
        const char *end = strchr(obj, '}');
        int len;

        if (!end) break;
        len = (int)(end - obj + 1);
        if (len >= (int)sizeof(block)) len = (int)sizeof(block) - 1;
        memcpy(block, obj, (size_t)len);
        block[len] = 0;
        json_str(block, "module", g_mod[g_mod_n].id, 24);
        json_str(block, "message", g_mod[g_mod_n].msg, 96);
        g_mod[g_mod_n].ok = json_bool(block, "ok");
        g_mod_n++;
        obj = end + 1;
    }
}

static void parse_fx_graph(const char *json) {
    const char *p, *obj;
    char block[512];

    g_cyc_n = 0;
    g_fx_graph_note[0] = 0;
    g_fx_edge_n = 0;
    g_fx_ccy_n = 0;
    json_str(json, "note", g_fx_graph_note, (int)sizeof(g_fx_graph_note));
    {
        const char *q = strstr(json, "\"edge_count\":");
        if (q) g_fx_edge_n = atoi(q + 13);
        q = strstr(json, "\"nodes\"");
        if (q) {
            const char *a = strchr(q, '[');
            const char *b;
            if (a) {
                b = strchr(a, ']');
                if (b) {
                    const char *c = a;
                    while (c < b) {
                        if (*c == '"') g_fx_ccy_n++;
                        c++;
                    }
                    g_fx_ccy_n /= 2;
                }
            }
        }
    }

    p = strstr(json, "\"cycles\"");
    if (!p) return;
    obj = strchr(p, '[');
    if (!obj) return;

    while (g_cyc_n < MOD_CYCLES && (obj = strstr(obj, "\"profit_bps\":")) != NULL) {
        const char *start = obj;
        const char *end = strchr(obj, '}');
        int len;

        if (!end) break;
        while (start > obj - 200 && start > json && *start != '{') start--;
        len = (int)(end - start + 1);
        if (len >= (int)sizeof(block)) len = (int)sizeof(block) - 1;
        memcpy(block, start, (size_t)len);
        block[len] = 0;

        json_str(block, "pair", g_cyc[g_cyc_n].pair, 12);
        g_cyc[g_cyc_n].profit_bps = json_float(block, "profit_bps", 0.0f);
        g_cyc[g_cyc_n].actionable = json_bool(block, "actionable");
        g_cyc_n++;
        obj = end + 1;
    }
}

static void parse_fx_carry(const char *json) {
    const char *p, *obj;
    char block[512];

    g_carry_n = 0;
    p = strstr(json, "\"signals\"");
    if (!p) p = strstr(json, "\"top_momentum\"");
    if (!p) return;
    obj = strchr(p, '[');
    if (!obj) return;

    while (g_carry_n < MOD_CARRY && (obj = strstr(obj, "\"pair\":")) != NULL) {
        const char *end = strchr(obj, '}');
        int len;

        if (!end) break;
        while (obj > json && *obj != '{') obj--;
        len = (int)(end - obj + 1);
        if (len >= (int)sizeof(block)) len = (int)sizeof(block) - 1;
        memcpy(block, obj, (size_t)len);
        block[len] = 0;
        json_str(block, "pair", g_carry[g_carry_n].pair, 12);
        g_carry[g_carry_n].mom_63d = json_float(block, "mom_63d_pct", 0.0f);
        g_carry[g_carry_n].carry_spread = json_float(block, "carry_spread_ann_pct", 0.0f);
        g_carry_n++;
        obj = end + 1;
    }
}

static void parse_weather_signals(const char *json) {
    const char *p, *obj;
    char block[640];

    g_wxsig_n = 0;
    p = strstr(json, "\"signals\"");
    if (!p) return;
    obj = strchr(p, '[');
    if (!obj) return;

    while (g_wxsig_n < MOD_WXSIG && (obj = strstr(obj, "\"id\":")) != NULL) {
        const char *end = strchr(obj, '}');
        int len;

        if (!end) break;
        while (obj > json && *obj != '{') obj--;
        len = (int)(end - obj + 1);
        if (len >= (int)sizeof(block)) len = (int)sizeof(block) - 1;
        memcpy(block, obj, (size_t)len);
        block[len] = 0;
        json_str(block, "id", g_wxsig[g_wxsig_n].id, 16);
        json_str(block, "msg", g_wxsig[g_wxsig_n].msg, 96);
        json_str(block, "sector", g_wxsig[g_wxsig_n].sector, 12);
        g_wxsig[g_wxsig_n].alert = json_bool(block, "alert");
        g_wxsig_n++;
        obj = end + 1;
    }
}

static void parse_wind_delta(const char *json) {
    const char *p, *obj;
    char block[640];

    g_wxd_n = 0;
    p = strstr(json, "\"deltas\"");
    if (!p) return;
    obj = strchr(p, '[');
    if (!obj) return;
    while (g_wxd_n < 4 && (obj = strstr(obj, "\"desk\":")) != NULL) {
        const char *end = strchr(obj, '}');
        int len;
        if (!end) break;
        while (obj > json && *obj != '{') obj--;
        len = (int)(end - obj + 1);
        if (len >= (int)sizeof(block)) len = (int)sizeof(block) - 1;
        memcpy(block, obj, (size_t)len);
        block[len] = 0;
        json_str(block, "desk", g_wxd[g_wxd_n].desk, 8);
        g_wxd[g_wxd_n].delta_norm = json_float(block, "delta_norm", 0.0f);
        g_wxd[g_wxd_n].om_mw = json_float(block, "om_mw_proxy", 0.0f);
        g_wxd[g_wxd_n].pub_mw = json_float(block, "pub_wind_mw", 0.0f);
        g_wxd[g_wxd_n].alert = json_bool(block, "alert");
        g_wxd_n++;
        obj = end + 1;
    }
}

static void parse_hdd_cdd(const char *json) {
    const char *p, *obj;
    char block[512];

    g_hdd_n = 0;
    p = strstr(json, "\"zones\"");
    if (!p) return;
    obj = strchr(p, '[');
    if (!obj) return;
    while (g_hdd_n < 8 && (obj = strstr(obj, "\"zone_id\":")) != NULL) {
        const char *end = strchr(obj, '}');
        int len;
        if (!end) break;
        while (obj > json && *obj != '{') obj--;
        len = (int)(end - obj + 1);
        if (len >= (int)sizeof(block)) len = (int)sizeof(block) - 1;
        memcpy(block, obj, (size_t)len);
        block[len] = 0;
        json_str(block, "zone_id", g_hdd[g_hdd_n].zone, 8);
        g_hdd[g_hdd_n].hdd_anom = json_float(block, "hdd_anom", 0.0f);
        g_hdd[g_hdd_n].cdd_anom = json_float(block, "cdd_anom", 0.0f);
        g_hdd_n++;
        obj = end + 1;
    }
}

static void parse_enso(const char *json) {
    const char *p;
    g_enso.oni = 0.0f;
    g_enso.phase[0] = 0;
    p = strstr(json, "\"latest\"");
    if (!p) return;
    g_enso.oni = json_float(p, "oni", 0.0f);
    json_str(p, "phase", g_enso.phase, 16);
}

void modules_reload(void) {
    static char buf[MOD_BUF];
    size_t n;

    g_mod_n = 0;
    g_cyc_n = 0;
    g_carry_n = 0;
    g_wxsig_n = 0;
    g_wxd_n = 0;
    g_hdd_n = 0;
    g_enso.oni = 0.0f;
    g_enso.phase[0] = 0;
    g_mod_brief[0] = 0;
    g_mod_ts[0] = 0;

    g_fx_graph_note[0] = 0;
    g_fx_edge_n = 0;
    g_fx_ccy_n = 0;

    if (read_file_utf8(L"cache\\spine\\modules_index.json", buf, sizeof(buf), &n))
        parse_modules_index(buf);
    if (read_file_utf8(L"cache\\spine\\modules\\fx_graph.json", buf, sizeof(buf), &n))
        parse_fx_graph(buf);
    if (read_file_utf8(L"cache\\spine\\modules\\fx_carry.json", buf, sizeof(buf), &n))
        parse_fx_carry(buf);
    if (read_file_utf8(L"cache\\spine\\modules\\weather_signals.json", buf, sizeof(buf), &n))
        parse_weather_signals(buf);
    if (read_file_utf8(L"cache\\spine\\modules\\weather_wind_delta.json", buf, sizeof(buf), &n))
        parse_wind_delta(buf);
    if (read_file_utf8(L"cache\\spine\\modules\\weather_hdd_cdd.json", buf, sizeof(buf), &n))
        parse_hdd_cdd(buf);
    if (read_file_utf8(L"cache\\spine\\modules\\weather_enso.json", buf, sizeof(buf), &n))
        parse_enso(buf);
}

int modules_count(void) { return g_mod_n; }

const ModuleRow *modules_get(int i) {
    if (i < 0 || i >= g_mod_n) return NULL;
    return &g_mod[i];
}

const char *modules_brief(void) { return g_mod_brief; }

const char *modules_built_at(void) { return g_mod_ts; }

int modules_wind_delta_count(void) { return g_wxd_n; }

const WindDeltaRow *modules_wind_delta_get(int i) {
    if (i < 0 || i >= g_wxd_n) return NULL;
    return &g_wxd[i];
}

int modules_hdd_zone_count(void) { return g_hdd_n; }

const HddZoneRow *modules_hdd_zone_get(int i) {
    if (i < 0 || i >= g_hdd_n) return NULL;
    return &g_hdd[i];
}

const EnsoSnap *modules_enso(void) { return &g_enso; }

int modules_fx_cycle_count(void) { return g_cyc_n; }

const FxCycleRow *modules_fx_cycle_get(int i) {
    if (i < 0 || i >= g_cyc_n) return NULL;
    return &g_cyc[i];
}

int modules_fx_carry_top_count(void) { return g_carry_n; }

const FxCarryRow *modules_fx_carry_top_get(int i) {
    if (i < 0 || i >= g_carry_n) return NULL;
    return &g_carry[i];
}

int modules_weather_sig_count(void) { return g_wxsig_n; }

const WeatherSigRow *modules_weather_sig_get(int i) {
    if (i < 0 || i >= g_wxsig_n) return NULL;
    return &g_wxsig[i];
}

void modules_paint_fx_ranking(HDC dc, RECT *rc) {
    wchar_t labs[12][12];
    const wchar_t *lp[12];
    float vals[12], moms[12];
    int y = rc->top, i, n = 0, lh = 13;
    ui_subheading(dc, &(RECT){ rc->left, y, rc->right, y + 12 }, L"CARRY rank  (decisionale)");
    y += 14;
    for (i = 0; i < g_carry_n && n < 12; i++) {
        wsprintfW(labs[n], L"%hs", g_carry[i].pair);
        lp[n] = labs[n];
        vals[n] = g_carry[i].carry_spread != 0.0f ? g_carry[i].carry_spread : g_carry[i].mom_63d;
        moms[n] = g_carry[i].mom_63d;
        n++;
    }
    if (n > 0) {
        RECT br = { rc->left, y, rc->right, y + n * lh + 6 };
        chart_bar_divergent(dc, &br, lp, vals, n, 5.0f);
        y = br.bottom + 4;
    }
    for (i = 0; i < n && y + lh <= rc->bottom; i++) {
        wchar_t line[64];
        COLORREF fg;
        wsprintfW(line, L"%s mom63 %+.1f%%", labs[i], moms[i]);
        fg = (vals[i] >= 0.0f && moms[i] >= 0.0f) ? CLR_UP :
             (vals[i] < 0.0f && moms[i] < 0.0f) ? CLR_DN : RGB(255, 180, 80);
        SetTextColor(dc, fg);
        SelectObject(dc, fSm);
        TextOutW(dc, rc->left, y, line, lstrlenW(line));
        y += lh;
    }
    if (y + lh <= rc->bottom) {
        SetTextColor(dc, CLR_OFF);
        TextOutW(dc, rc->left, y, L"colore concorde/discorde carry vs momentum", -1);
    }
}

void modules_paint_fx_cycles(HDC dc, RECT *rc) {
    wchar_t line[160], nw[120];
    int y = rc->top, i, lh = 13;
    ui_subheading(dc, &(RECT){ rc->left, y, rc->right, y + 12 }, L"CICLI  Bellman-Ford");
    y += 14;
    if (g_cyc_n == 0) {
        SetTextColor(dc, CLR_UP);
        SelectObject(dc, fLbl);
        TextOutW(dc, rc->left, y, L"nessun ciclo < costo", 20);
        y += lh + 2;
        wsprintfW(line, L"%d ccys  %d edges  fee 2bp  -> mercato efficiente oggi",
                  g_fx_ccy_n, g_fx_edge_n);
        SetTextColor(dc, CLR_DIM);
        SelectObject(dc, fSm);
        TextOutW(dc, rc->left, y, line, lstrlenW(line));
        y += lh;
    } else {
        for (i = 0; i < g_cyc_n && y + lh <= rc->bottom; i++) {
            wsprintfW(line, L"%hs  %+0.1f bp%s", g_cyc[i].pair, g_cyc[i].profit_bps,
                      g_cyc[i].actionable ? L" *" : L"");
            SetTextColor(dc, g_cyc[i].profit_bps > 0.0f ? CLR_ACC : CLR_DN);
            SelectObject(dc, fSm);
            TextOutW(dc, rc->left, y, line, lstrlenW(line));
            y += lh;
        }
    }
    if (g_fx_graph_note[0] && y + lh <= rc->bottom) {
        MultiByteToWideChar(CP_UTF8, 0, g_fx_graph_note, -1, nw, 120);
        SetTextColor(dc, CLR_OFF);
        SelectObject(dc, fSm);
        TextOutW(dc, rc->left, y, nw, lstrlenW(nw));
    }
}

void modules_paint_fx_panel(HDC dc, RECT *rc) {
    wchar_t line[280];
    int y = rc->top, i;
    const int lh = 14;

    if (y + lh > rc->bottom) return;
    ui_subheading(dc, &(RECT){ rc->left, y, rc->right, y + 12 }, L"BRIDGE MODULES");
    y += 14;

    if (g_mod_brief[0] && y + lh <= rc->bottom) {
        wchar_t bw[96];
        MultiByteToWideChar(CP_UTF8, 0, g_mod_brief, -1, bw, 96);
        SetTextColor(dc, CLR_DIM);
        SelectObject(dc, fSm);
        TextOutW(dc, rc->left, y, bw, lstrlenW(bw));
        y += lh;
    }

    for (i = 0; i < g_mod_n && y + lh <= rc->bottom; i++) {
        const ModuleRow *m = &g_mod[i];
        wchar_t msgw[96];
        MultiByteToWideChar(CP_UTF8, 0, m->msg, -1, msgw, 96);
        wsprintfW(line, L"  %s %hs  %.70ls", m->ok ? L"+" : L"!", m->id, msgw);
        SetTextColor(dc, m->ok ? CLR_UP : CLR_DN);
        TextOutW(dc, rc->left, y, line, lstrlenW(line));
        y += lh;
    }

    if (g_carry_n > 0 && y + lh <= rc->bottom) {
        int j, n = g_carry_n, show = n < 9 ? n : 9;
        wchar_t labs[9][12];
        const wchar_t *lp[9];
        float vals[9];
        y += 2;
        ui_subheading(dc, &(RECT){ rc->left, y, rc->right, y + 12 }, L"CARRY rank (ann%)");
        y += 14;
        for (j = 0; j < show; j++) {
            wsprintfW(labs[j], L"%hs", g_carry[j].pair);
            lp[j] = labs[j];
            vals[j] = g_carry[j].carry_spread != 0.0f ? g_carry[j].carry_spread : g_carry[j].mom_63d;
        }
        if (show > 0) {
            RECT br = { rc->left, y, rc->right, y + show * lh + 4 };
            chart_bar_divergent(dc, &br, lp, vals, show, 5.0f);
            y = br.bottom + 4;
        }
    }

    if (g_cyc_n > 0 && y + lh <= rc->bottom) {
        y += 2;
        ui_subheading(dc, &(RECT){ rc->left, y, rc->right, y + 12 }, L"GRAPH CYCLES (daily ref)");
        y += 14;
        for (i = 0; i < g_cyc_n && i < 3 && y + lh <= rc->bottom; i++) {
            wsprintfW(line, L"  #%d  %+0.1f bp%s", i + 1, g_cyc[i].profit_bps,
                      g_cyc[i].actionable ? L" *" : L"");
            SetTextColor(dc, g_cyc[i].profit_bps > 0.0f ? CLR_ACC : CLR_DIM);
            TextOutW(dc, rc->left, y, line, lstrlenW(line));
            y += lh;
        }
    }

    if (g_carry_n > 0 && y + lh <= rc->bottom) {
        y += 2;
        ui_subheading(dc, &(RECT){ rc->left, y, rc->right, y + 12 }, L"MOMENTUM 63d");
        y += 14;
        for (i = 0; i < g_carry_n && i < 3 && y + lh <= rc->bottom; i++) {
            wsprintfW(line, L"  %hs  %+0.1f%%", g_carry[i].pair, g_carry[i].mom_63d);
            SetTextColor(dc, g_carry[i].mom_63d >= 0.0f ? CLR_UP : CLR_DN);
            TextOutW(dc, rc->left, y, line, lstrlenW(line));
            y += lh;
        }
    }
}

void modules_paint_weather_panel(HDC dc, RECT *rc) {
    wchar_t line[280];
    int y = rc->top, i;
    const int lh = 14;

    if (y + lh > rc->bottom) return;
    ui_subheading(dc, &(RECT){ rc->left, y, rc->right, y + 12 }, L"METEO SIGNALS");
    y += 14;

    if (g_wxsig_n == 0 && y + lh <= rc->bottom) {
        SetTextColor(dc, CLR_DIM);
        SelectObject(dc, fSm);
        TextOutW(dc, rc->left, y, L"  run spine_build (weather pipeline)", 36);
        return;
    }

    for (i = 0; i < g_wxsig_n && y + lh <= rc->bottom; i++) {
        const WeatherSigRow *s = &g_wxsig[i];
        wchar_t msgw[96];
        MultiByteToWideChar(CP_UTF8, 0, s->msg, -1, msgw, 96);
        wsprintfW(line, L"  %s %hs  %.55ls", s->alert ? L"!!" : L"--", s->id, msgw);
        SetTextColor(dc, s->alert ? CLR_DN : CLR_DIM);
        SelectObject(dc, fSm);
        TextOutW(dc, rc->left, y, line, lstrlenW(line));
        y += lh;
    }
}

void modules_paint_wind_delta(HDC dc, RECT *rc) {
    wchar_t labs[4][8];
    const wchar_t *lp[4];
    float vals[4];
    int y = rc->top, i, lh = 13, n = 0;
    ui_subheading(dc, &(RECT){ rc->left, y, rc->right, y + 12 }, L"WIND DELTA live (PWR-01-v2)");
    y += 14;
    if (g_wxd_n == 0) {
        SetTextColor(dc, CLR_OFF);
        SelectObject(dc, fSm);
        TextOutW(dc, rc->left, y, L"  no delta cache", 16);
        return;
    }
    for (i = 0; i < g_wxd_n && n < 4; i++) {
        const WindDeltaRow *w = &g_wxd[i];
        wsprintfW(labs[n], L"%hs", w->desk);
        lp[n] = labs[n];
        vals[n] = w->delta_norm;
        n++;
    }
    if (n > 0 && rc->right > rc->left + 48) {
        RECT br = { rc->left, y, rc->right, y + n * lh + 8 };
        float vmax = 1.0f;
        for (i = 0; i < n; i++)
            if (fabsf(vals[i]) > vmax) vmax = fabsf(vals[i]);
        if (vmax < 0.05f) vmax = 0.05f;
        chart_bar_divergent(dc, &br, lp, vals, n, vmax);
        y = br.bottom + 4;
    }
    for (i = 0; i < g_wxd_n && y + lh <= rc->bottom; i++) {
        const WindDeltaRow *w = &g_wxd[i];
        wchar_t line[96], deskw[12], omw[20], pubw[20];
        MultiByteToWideChar(CP_UTF8, 0, w->desk, -1, deskw, 12);
        ui_fmt_wdouble(omw, 20, w->om_mw, 0);
        ui_fmt_wdouble(pubw, 20, w->pub_mw, 0);
        wsprintfW(line, L"%s OM %s pub %s MW%s",
                  deskw, omw, pubw, w->alert ? L" ALERT" : L"");
        SetTextColor(dc, w->alert ? CLR_DN : CLR_DIM);
        SelectObject(dc, fSm);
        TextOutW(dc, rc->left, y, line, lstrlenW(line));
        y += lh;
    }
}

void modules_paint_hdd_enso(HDC dc, RECT *rc) {
    wchar_t line[160], labs[6][12];
    const wchar_t *lp[6];
    float vals[6];
    int y = rc->top, i, n = 0, lh = 13;
    const EnsoSnap *e = &g_enso;

    ui_subheading(dc, &(RECT){ rc->left, y, rc->right, y + 12 }, L"HDD/CDD anomalia");
    y += 14;
    for (i = 0; i < g_hdd_n && n < 6; i++) {
        if (g_hdd[i].zone[0] == 'N' || g_hdd[i].zone[0] == 'P' ||
            g_hdd[i].zone[0] == 'B' || g_hdd[i].zone[0] == 'L') {
            wsprintfW(labs[n], L"%hs", g_hdd[i].zone);
            lp[n] = labs[n];
            vals[n] = g_hdd[i].hdd_anom;
            n++;
        }
    }
    if (n > 0) {
        RECT br = { rc->left, y, rc->right, y + n * lh + 4 };
        chart_bar_divergent(dc, &br, lp, vals, n, 3.0f);
        y = br.bottom + 6;
    }
    if (e->phase[0] && y + lh <= rc->bottom) {
        wsprintfW(line, L"ENSO ONI=%.2f  %hs", e->oni, e->phase);
        SetTextColor(dc, e->oni > 0.5f ? CLR_DN : CLR_DIM);
        SelectObject(dc, fSm);
        TextOutW(dc, rc->left, y, line, lstrlenW(line));
    }
}

void modules_paint_spine_grid(HDC dc, RECT *rc) {
    int i, cols = 3, cw, ch, n = g_mod_n, y0 = rc->top;
    wchar_t ts[40];

    if (n > MOD_MAX) n = MOD_MAX;
    ui_subheading(dc, &(RECT){ rc->left, y0, rc->right, y0 + 12 }, L"SPINE moduli");
    y0 += 14;
    if (g_mod_ts[0]) {
        MultiByteToWideChar(CP_UTF8, 0, g_mod_ts, -1, ts, 40);
        SetTextColor(dc, CLR_OFF);
        SelectObject(dc, fSm);
        TextOutW(dc, rc->left, y0, ts, lstrlenW(ts));
        y0 += 12;
    }
    cw = (rc->right - rc->left) / cols;
    ch = 14;
    for (i = 0; i < n; i++) {
        const ModuleRow *m = &g_mod[i];
        RECT cell;
        HBRUSH br;
        wchar_t line[32];
        int col = i % cols;
        int row = i / cols;
        COLORREF fg;
        if (!m) continue;
        cell.left = rc->left + col * cw;
        cell.right = cell.left + cw - 2;
        cell.top = y0 + row * ch;
        cell.bottom = cell.top + ch - 1;
        if (cell.bottom > rc->bottom) break;
        if (!m->ok) br = CreateSolidBrush(RGB(50, 20, 20));
        else if (strstr(m->msg, "FAIL") || strstr(m->msg, "0 file"))
            br = CreateSolidBrush(RGB(60, 45, 20));
        else br = CreateSolidBrush(RGB(20, 50, 20));
        FillRect(dc, &cell, br);
        DeleteObject(br);
        wsprintfW(line, L"%hs", m->id);
        fg = m->ok ? CLR_UP : CLR_DN;
        if (m->ok && (strstr(m->msg, "FAIL") || strstr(m->msg, "0 file")))
            fg = RGB(255, 180, 80);
        SetTextColor(dc, fg);
        SelectObject(dc, fSm);
        DrawTextW(dc, line, -1, &cell, DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX);
    }
}
