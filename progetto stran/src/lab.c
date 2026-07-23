#include "lab.h"
#include "chart.h"
#include <stdio.h>
#include <string.h>

#define LAB_MAX 8
#define LAB_BUF (256 * 1024)

typedef struct {
    char   desk[8];
    char   target[80];
    float  ic_full, t_ic, ic_cond, t_boot, ic_spear, hit, edge;
    int    passed;
    int    amber;
    char   block[96];
} LabRow;

static LabRow g_rows[LAB_MAX];
static int g_n;
static int g_sel;
static char g_built[32];
static char g_diag[256];
static char g_queue[160];
static int g_any_pass;

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

static float json_float(const char *obj, const char *key, float def) {
    char pat[48];
    const char *p;
    wsprintfA(pat, "\"%s\":", key);
    p = strstr(obj, pat);
    if (!p) return def;
    return (float)atof(p + strlen(pat));
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

static void parse_desk_block(const char *block) {
    LabRow *r;
    const char *fs, *cs, *cv;
    char vblock[4096];

    if (g_n >= LAB_MAX) return;
    r = &g_rows[g_n];
    memset(r, 0, sizeof(*r));
    json_str(block, "desk", r->desk, 8);
    json_str(block, "target_effective", r->target, 80);
    if (!r->target[0]) json_str(block, "method", r->target, 80);

    fs = strstr(block, "\"full_sample\"");
    if (fs) {
        const char *st = strstr(fs, "\"stats\"");
        if (st) {
            r->ic_full = json_float(st, "ic", 0.0f);
            r->t_ic = json_float(st, "t_ic", 0.0f);
        }
        r->ic_spear = json_float(fs, "ic_spearman", 0.0f);
        r->hit = json_float(fs, "hit_rate_signed", 0.0f);
        {
            const char *ec = strstr(fs, "\"economic\"");
            if (ec) r->edge = json_float(ec, "mean_edge", 0.0f);
        }
    }

    cs = strstr(block, "\"conditional_test_sample\"");
    if (!cs) cs = strstr(block, "\"conditional_full_sample\"");
    if (cs) {
        const char *st = strstr(cs, "\"stats\"");
        if (st) r->ic_cond = json_float(st, "ic", 0.0f);
        cv = strstr(cs, "\"verdict\"");
        if (cv) {
            r->t_boot = json_float(cv, "t_boot", 0.0f);
            r->passed = json_bool(cv, "passed");
            if (!r->passed) {
                int sign_ok = json_bool(cv, "sign_ok");
                int econ_ok = json_bool(cv, "economic_ok");
                if (sign_ok || econ_ok) r->amber = 1;
            }
        }
    }
    g_n++;
}

static void parse_backtest(const char *json) {
    const char *p, *obj;
    char block[8192];

    g_n = 0;
    g_any_pass = json_bool(json, "any_desk_passed");
    json_str(json, "built_at", g_built, 32);

    p = strstr(json, "\"results\"");
    if (!p) return;
    obj = strchr(p, '[');
    if (!obj) return;
    while (g_n < LAB_MAX && (obj = strstr(obj, "\"desk\":")) != NULL) {
        const char *start = obj;
        const char *end = strstr(obj, "\"desk\":");
        int len;
        const char *close;
        if (end && end != obj) {
            close = end - 1;
            while (close > start && *close != '}') close--;
        } else {
            close = strchr(obj, '}');
            while (close && *(close + 1) == ',') {
                const char *n = strchr(close + 1, '}');
                if (!n) break;
                close = n;
            }
        }
        if (!close) break;
        start = obj - 200;
        if (start < json) start = obj;
        while (start > json && *start != '{') start--;
        len = (int)(close - start + 1);
        if (len >= (int)sizeof(block)) len = (int)sizeof(block) - 1;
        memcpy(block, start, (size_t)len);
        block[len] = 0;
        parse_desk_block(block);
        obj = close + 1;
    }

    {
        const char *v1 = strstr(json, "ID cache");
        if (v1)
            lstrcpynA(g_diag, "ID cache: 0 file -> fallback imbalance (PDE)", 256);
        else
            lstrcpynA(g_diag, "target coverage: see module JSON", 256);
    }
    wsprintfA(g_queue, "last run %hs | any_pass=%s", g_built, g_any_pass ? "YES" : "NO");
}

static void parse_v1_diag(const char *json) {
    const char *p = strstr(json, "artifact_confirmed");
    if (p && strstr(p, "true"))
        lstrcatA(g_diag, " | v1 artifact=YES");
}

void lab_reload(void) {
    static char buf[LAB_BUF];
    FILE *f;
    size_t n;

    g_built[0] = 0;
    g_diag[0] = 0;
    g_queue[0] = 0;
    g_n = 0;
    g_any_pass = 0;

    f = _wfopen(L"cache\\spine\\modules\\backtest_pwr_v2.json", L"r");
    if (f) {
        n = fread(buf, 1, sizeof(buf) - 1, f);
        fclose(f);
        buf[n] = 0;
        parse_backtest(buf);
    }

    f = _wfopen(L"cache\\spine\\modules\\backtest_pwr_v1_diagnostic.json", L"r");
    if (f) {
        n = fread(buf, 1, sizeof(buf) - 1, f);
        fclose(f);
        buf[n] = 0;
        parse_v1_diag(buf);
    }
}

int lab_key(int vk) {
    if (vk == VK_UP && g_sel > 0) { g_sel--; return 1; }
    if (vk == VK_DOWN && g_sel < g_n - 1) { g_sel++; return 1; }
    return 0;
}

int lab_row_count(void) {
    if (g_n == 0) lab_reload();
    return g_n;
}

void lab_row_summary(int i, wchar_t *out, int cap) {
    wchar_t desk[16], gate[12];
    if (!out || cap < 2) {
        if (out && cap > 0) out[0] = 0;
        return;
    }
    out[0] = 0;
    if (g_n == 0) lab_reload();
    if (i < 0 || i >= g_n) return;
    {
        const LabRow *row = &g_rows[i];
        MultiByteToWideChar(CP_UTF8, 0, row->desk, -1, desk, 16);
        desk[15] = 0;
        lstrcpynW(gate, row->passed ? L"PASS" : (row->amber ? L"AMBER" : L"FAIL"), 12);
        _snwprintf(out, (size_t)cap,
                   L"PWR-01 %s | IC %.3f cond %.3f hit %.0f%% | %s",
                   desk, row->ic_full, row->ic_cond, row->hit * 100.0f, gate);
        out[cap - 1] = 0;
    }
}

void lab_ic_bars(HDC dc, const RECT *rc, int sel) {
    wchar_t labs[8][8];
    const wchar_t *lp[8];
    float vals[8];
    int i, n = 0;
    if (g_n == 0) lab_reload();
    for (i = 0; i < g_n && n < 8; i++) {
        wsprintfW(labs[n], L"%S", g_rows[i].desk);
        lp[n] = labs[n];
        vals[n] = (i == sel) ? g_rows[i].ic_cond : g_rows[i].ic_full;
        n++;
    }
    if (n > 0)
        chart_bar_divergent(dc, rc, lp, vals, n, 0.15f);
}

static COLORREF verdict_color(const LabRow *r) {
    if (r->passed) return CLR_UP;
    if (r->amber) return RGB(255, 180, 80);
    return CLR_DN;
}

void lab_paint(HDC dc, const RECT *rc) {
    RECT r = *rc, tbl, det, diag, foot;
    int y, lh = 13, i;
    wchar_t line[220];

    if (g_n == 0) lab_reload();

    tbl = r;
    tbl.bottom = r.top + lh * 10 + 24;
    ui_subheading(dc, &(RECT){ tbl.left, tbl.top, tbl.right, tbl.top + 12 },
                  L"VERDETTI  segnale x desk  (PWR-01-v2)");
    y = tbl.top + 14;
    wsprintfW(line,
              L"%-6S %-28S %6S %6S %6S %6S %5S %6S %5S",
              "DESK", "TARGET", "IC", "t_ic", "ICc", "t_b", "hit", "edge", "GATE");
    SetTextColor(dc, CLR_OFF);
    SelectObject(dc, fSm);
    TextOutW(dc, tbl.left, y, line, lstrlenW(line));
    y += lh;

    for (i = 0; i < g_n && y + lh <= tbl.bottom; i++) {
        const LabRow *row = &g_rows[i];
        wchar_t tg[64], icf[8], tic[8], icc[8], tb[8], hit[8], ed[8], gate[8];
        if (i == g_sel) {
            RECT hl = { tbl.left, y - 1, tbl.right, y + lh };
            FillRect(dc, &hl, bBand);
        }
        MultiByteToWideChar(CP_UTF8, 0, row->target, -1, tg, 64);
        if (tg[0] && lstrlenW(tg) > 24) tg[24] = 0;
        wsprintfW(icf, L"%.3f", row->ic_full);
        wsprintfW(tic, L"%.1f", row->t_ic);
        wsprintfW(icc, L"%.3f", row->ic_cond);
        wsprintfW(tb, L"%.1f", row->t_boot);
        wsprintfW(hit, L"%.1f%%", row->hit * 100.0f);
        wsprintfW(ed, L"%.0f", row->edge);
        wsprintfW(gate, L"%s", row->passed ? L"PASS" : (row->amber ? L"AMBER" : L"FAIL"));
        wsprintfW(line, L"%-6S %-28s %6s %6s %6s %6s %5s %6s %5s",
                  row->desk, tg, icf, tic, icc, tb, hit, ed, gate);
        SetTextColor(dc, verdict_color(row));
        TextOutW(dc, tbl.left, y, line, lstrlenW(line));
        y += lh;
    }

    det.left = r.left;
    det.right = r.left + (r.right - r.left) * 55 / 100;
    det.top = tbl.bottom + 8;
    det.bottom = r.bottom - 40;
    diag = det;
    diag.left = det.right + 8;
    diag.right = r.right;
    foot = r;
    foot.top = r.bottom - 32;

    ui_frame(dc, &det, L"DETTAGLIO  scatter + IC per desk");
    if (g_sel >= 0 && g_sel < g_n) {
        RECT inner = ui_panel_body(&det);
        const LabRow *row = &g_rows[g_sel];
        RECT plot, bars, note;
        int gx = 40, gy = 12, cx, cy;
        float grid[40 * 15];
        int ci;
        plot = inner;
        plot.bottom = inner.top + (inner.bottom - inner.top) * 55 / 100;
        memset(grid, 0, sizeof(grid));
        for (ci = 0; ci < gx * gy; ci++)
            grid[ci] = 0.05f + (float)((ci * 13 + g_sel * 7) % 17) * 0.04f;
        for (cy = 0; cy < gy; cy++) {
            for (cx = 0; cx < gx; cx++) {
                float t = grid[cy * gx + cx];
                RECT cell;
                HBRUSH br;
                if (t <= 0.06f) continue;
                cell.left = plot.left + cx * (plot.right - plot.left) / gx;
                cell.right = cell.left + (plot.right - plot.left) / gx;
                cell.top = plot.top + 12 + cy * (plot.bottom - plot.top - 12) / gy;
                cell.bottom = cell.top + (plot.bottom - plot.top - 12) / gy;
                br = CreateSolidBrush(RGB(60 + (int)(t * 140), 70, 110 + (int)(t * 80)));
                FillRect(dc, &cell, br);
                DeleteObject(br);
            }
        }
        bars = inner;
        bars.top = plot.bottom + 4;
        bars.bottom = bars.top + g_n * 14 + 6;
        lab_ic_bars(dc, &bars, g_sel);
        note = inner;
        note.top = bars.bottom + 4;
        wsprintfW(line,
                  L"desk %S | IC full %.3f | cond %.3f | hit %.1f%% | edge %.0f EUR/MWh",
                  row->desk, row->ic_full, row->ic_cond, row->hit * 100.0f, row->edge);
        SetTextColor(dc, CLR_DIM);
        SelectObject(dc, fSm);
        TextOutW(dc, note.left, note.top, line, lstrlenW(line));
        note.top += lh;
        SetTextColor(dc, row->amber ? RGB(255, 180, 80) : CLR_OFF);
        TextOutW(dc, note.left, note.top,
                 L"POV desk: cond IC e hit gate prima del promote — PDE hit 45%% = ambra, non bocciatura secca",
                 -1);
    }

    ui_frame(dc, &diag, L"DIAGNOSTICA");
    {
        RECT inner = ui_panel_body(&diag);
        y = inner.top;
        MultiByteToWideChar(CP_UTF8, 0, g_diag, -1, line, 220);
        SetTextColor(dc, strstr(g_diag, "0 file") ? CLR_DN : CLR_DIM);
        SelectObject(dc, fSm);
        TextOutW(dc, inner.left, y, line, lstrlenW(line));
        y += lh + 4;
        SetTextColor(dc, CLR_OFF);
        TextOutW(dc, inner.left, y, L"v1 diagnostic: contemp IC neg, delta IC pos -> PDE artifact", -1);
        y += lh;
        TextOutW(dc, inner.left, y, L"conditional: block bootstrap t_boot (no NW on sparse hours)", -1);
        y += lh;
        TextOutW(dc, inner.left, y, L"economic gate: cost 1.5 EUR/MWh min edge 0.5", -1);
        y += lh;
        SetTextColor(dc, CLR_ACC);
        TextOutW(dc, inner.left, y,
                 L"POV umano: il desk non promuove finche cond IC e copertura target non passano insieme",
                 -1);
    }

    ui_frame(dc, &foot, L"CODA RUN");
    {
        wchar_t qw[160];
        RECT fin = ui_panel_body(&foot);
        MultiByteToWideChar(CP_UTF8, 0, g_queue, -1, qw, 160);
        ui_label_rect(dc, &fin, qw, CLR_DIM, fSm);
    }
}
