#include "desk_panels.h"
#include "chart.h"
#include "data.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static float json_float(const char *obj, const char *key, float def) {
    char pat[48];
    const char *p;
    char *e = NULL;

    wsprintfA(pat, "\"%s\"", key);
    p = strstr(obj, pat);
    if (!p) return def;
    p = strchr(p + strlen(pat), ':');
    if (!p) return def;
    return (float)strtod(p + 1, &e);
}

static int load_wind_csv(const char *desk, float *out, int cap) {
    wchar_t path[MAX_PATH];
    char line[128];
    FILE *f;
    int n = 0;

    wsprintfW(path, L"cache\\weather\\entsoe_wind\\%hs.csv", desk);
    f = _wfopen(path, L"r");
    if (!f) return 0;
    if (!fgets(line, sizeof(line), f)) { fclose(f); return 0; }
    while (fgets(line, sizeof(line), f) && n < cap) {
        char *comma = strchr(line, ',');
        if (!comma) continue;
        out[n++] = (float)strtod(comma + 1, NULL);
    }
    fclose(f);
    return n;
}

static int load_imbalance_recent(const char *desk, float *out, int cap) {
    wchar_t path[MAX_PATH];
    char *buf = NULL;
    long sz;
    FILE *f;
    const char *arr;
    const char *p;
    int n = 0;
    SYSTEMTIME st;

    GetLocalTime(&st);
    wsprintfW(path, L"cache\\weather\\entsoe_hourly\\imbalance\\%hs\\%04d-%02d.json",
              desk, (int)st.wYear, (int)st.wMonth);
    f = _wfopen(path, L"r");
    if (!f) {
        if (st.wMonth == 1)
            wsprintfW(path, L"cache\\weather\\entsoe_hourly\\imbalance\\%hs\\%04d-12.json",
                      desk, (int)st.wYear - 1);
        else
            wsprintfW(path, L"cache\\weather\\entsoe_hourly\\imbalance\\%hs\\%04d-%02d.json",
                      desk, (int)st.wYear, (int)st.wMonth - 1);
        f = _wfopen(path, L"r");
    }
    if (!f) return 0;
    fseek(f, 0, SEEK_END);
    sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (sz <= 0 || sz > 4 * 1024 * 1024) { fclose(f); return 0; }
    buf = (char *)malloc((size_t)sz + 1);
    if (!buf) { fclose(f); return 0; }
    if (fread(buf, 1, (size_t)sz, f) != (size_t)sz) {
        free(buf);
        fclose(f);
        return 0;
    }
    buf[sz] = 0;
    fclose(f);

    arr = strstr(buf, "\"imb_long\"");
    if (!arr) arr = strstr(buf, "\"imb_short\"");
    if (!arr) { free(buf); return 0; }
    p = strchr(arr, '[');
    if (!p) { free(buf); return 0; }
    p++;
    while (*p && n < cap) {
        char *e = NULL;
        double v;
        while (*p == ' ' || *p == '\n' || *p == '\r' || *p == ',') p++;
        if (*p == ']') break;
        v = strtod(p, &e);
        if (e == p) break;
        out[n++] = (float)v;
        p = e;
    }
    free(buf);
    return n;
}

void desk_paint_entsoe_capacity(HDC dc, const RECT *rc) {
    static const struct { const char *cc; const wchar_t *name; } CC[] = {
        { "DE", L"Germany" }, { "FR", L"France" }, { "IT", L"Italy" }
    };
    RECT r = *rc, row;
    wchar_t path[MAX_PATH];
    char buf[4096];
    int i, y;

    ui_subheading(dc, &(RECT){ r.left, r.top, r.right, r.top + 12 },
                  L"ENTSO-E  installed wind capacity (MW)");
    y = r.top + 18;
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);

    for (i = 0; i < 3; i++) {
        FILE *f;
        float y2024 = 0.0f, y2026 = 0.0f;
        wchar_t line[96], v24[16], v26[16];
        int bar_w;
        const char *blk;

        wsprintfW(path, L"cache\\weather\\entsoe_capacity\\%hs.json", CC[i].cc);
        f = _wfopen(path, L"r");
        if (!f) {
            SetTextColor(dc, CLR_OFF);
            wsprintfW(line, L"%-2s  cache mancante", CC[i].cc);
            TextOutW(dc, r.left, y, line, lstrlenW(line));
            y += 28;
            continue;
        }
        if (!fread(buf, 1, sizeof(buf) - 1, f)) { fclose(f); continue; }
        buf[sizeof(buf) - 1] = 0;
        fclose(f);
        blk = strstr(buf, "wind_mw_by_year");
        if (blk) {
            y2024 = json_float(blk, "2024", 0.0f);
            y2026 = json_float(blk, "2026", 0.0f);
        }
        ui_fmt_wdouble(v24, 16, y2024, 0);
        ui_fmt_wdouble(v26, 16, y2026, 0);
        SetTextColor(dc, CLR_TXT);
        wsprintfW(line, L"%-2s %-10s  2024 %s MW   2026 %s MW", CC[i].cc, CC[i].name, v24, v26);
        TextOutW(dc, r.left, y, line, lstrlenW(line));
        row.left = r.left;
        row.top = y + 14;
        row.right = r.right;
        row.bottom = row.top + 10;
        bar_w = row.right - row.left - 80;
        if (bar_w > 40 && y2026 > 0.0f) {
            RECT fill = row;
            fill.left += 80;
            fill.right = fill.left + (int)((y2024 / y2026) * (float)bar_w);
            if (fill.right > row.left + 80 + bar_w)
                fill.right = row.left + 80 + bar_w;
            FillRect(dc, &row, bBand);
            FillRect(dc, &fill, bWhite);
        }
        y += 32;
    }
    SetTextColor(dc, CLR_DIM);
    TextOutW(dc, r.left, r.bottom - 14,
             L"fonte cache/weather/entsoe_capacity  |  query_installed_generation_capacity",
             72);
}

void desk_paint_entsoe_wind(HDC dc, const RECT *rc, const SeriesStore *st) {
    static const struct { const char *desk; const wchar_t *z; } Z[] = {
        { "PDE", L"DE" }, { "PFR", L"FR" }, { "PIT", L"IT" },
        { "PNL", L"NL" }, { "PPL", L"PL" }
    };
    RECT r = *rc, cell;
    int i, cols = 3, rows = 2, cw, ch;
    float vals[64];
    DataSeries snap;

    (void)st;
    ui_subheading(dc, &(RECT){ r.left, r.top, r.right, r.top + 12 },
                  L"ENTSO-E  wind generation forecast (MW)");
    r.top += 16;
    cw = (r.right - r.left) / cols;
    ch = (r.bottom - r.top) / rows;
    for (i = 0; i < 5; i++) {
        int n, j;
        wchar_t title[24];

        cell.left = r.left + (i % cols) * cw;
        cell.right = cell.left + cw - 6;
        cell.top = r.top + (i / cols) * ch;
        cell.bottom = cell.top + ch - 4;
        n = load_wind_csv(Z[i].desk, vals, 64);
        wsprintfW(title, L"%s wind", Z[i].z);
        if (n >= 4) {
            memset(&snap, 0, sizeof(snap));
            lstrcpynW(snap.label, title, 14);
            snap.n = (uint16_t)n;
            for (j = 0; j < n; j++) {
                snap.val[j] = vals[j];
                if (j == 0 || vals[j] < snap.min_h) snap.min_h = vals[j];
                if (j == 0 || vals[j] > snap.max_h) snap.max_h = vals[j];
            }
            snap.live = vals[n - 1];
            chart_series_cell(dc, &cell, &snap);
        } else {
            ui_label_rect(dc, &cell, L"cache entsoe_wind mancante", CLR_OFF, fSm);
        }
    }
}

void desk_paint_entsoe_hourly(HDC dc, const RECT *rc, const char *desk) {
    static const char *DESKS[] = { "PDE", "PFR", "PIT" };
    RECT r = *rc, cell;
    int i, ncols = 3, cw;
    float vals[512];
    DataSeries snap;

    ui_subheading(dc, &(RECT){ r.left, r.top, r.right, r.top + 12 },
                  L"ENTSO-E  imbalance 15min  (ultimo mese)");
    r.top += 16;
    cw = (r.right - r.left) / ncols;
    for (i = 0; i < 3; i++) {
        int n, j, show;
        const char *id = desk && desk[0] ? desk : DESKS[i];
        wchar_t title[20];

        cell.left = r.left + i * cw;
        cell.right = cell.left + cw - 6;
        cell.top = r.top;
        cell.bottom = r.bottom - 16;
        n = load_imbalance_recent(id, vals, 512);
        wsprintfW(title, L"%hs imb", id);
        if (n >= 8) {
            show = n > 96 ? 96 : n;
            memset(&snap, 0, sizeof(snap));
            lstrcpynW(snap.label, title, 14);
            snap.n = (uint16_t)show;
            for (j = 0; j < show; j++) {
                float v = vals[n - show + j];
                snap.val[j] = v;
                if (j == 0 || v < snap.min_h) snap.min_h = v;
                if (j == 0 || v > snap.max_h) snap.max_h = v;
            }
            snap.live = vals[n - 1];
            chart_series_cell(dc, &cell, &snap);
        } else {
            ui_label_rect(dc, &cell, L"cache entsoe_hourly mancante", CLR_OFF, fSm);
        }
        if (desk && desk[0]) break;
    }
    SetTextColor(dc, CLR_DIM);
    SelectObject(dc, fSm);
    TextOutW(dc, r.left, r.bottom - 12,
             L"imb_long MW  |  cache/weather/entsoe_hourly/imbalance", 52);
}

void desk_paint_georisk(HDC dc, const RECT *rc, const SeriesStore *st) {
    static const char *IDS[] = { "GPR", "CPU", "CVI", "EUA" };
    RECT r = *rc, cell;
    int i, w2;

    ui_subheading(dc, &(RECT){ r.left, r.top, r.right, r.top + 12 },
                  L"GEO RISK  indici macro + carbon");
    r.top += 16;
    w2 = (r.right - r.left) / 2;
    for (i = 0; i < 4; i++) {
        DataSeries snap;
        cell.left = r.left + (i % 2) * w2;
        cell.right = cell.left + w2 - 6;
        cell.top = r.top + (i / 2) * ((r.bottom - r.top) / 2);
        cell.bottom = cell.top + (r.bottom - r.top) / 2 - 8;
        if (data_series_snap(IDS[i], &snap))
            chart_series_cell(dc, &cell, &snap);
        else if (st) {
            DataSeries *s = series_get((SeriesStore *)st, IDS[i]);
            if (s && s->n >= 2)
                chart_series_cell(dc, &cell, s);
        }
    }
}
