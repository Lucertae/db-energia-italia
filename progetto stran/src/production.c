#include "production.h"
#include "ingest_eia.h"
#include "data.h"
#include "series.h"
#include "chart.h"
#include "glossary.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    const wchar_t *iso;
    const wchar_t *name;
    const char *iso3;
    const char *eia_iso2;
} CountryDef;

static const CountryDef C_DEF[] = {
    { L"US", L"United States", "USA", "US" },
    { L"CN", L"China",         "CHN", "CHN" },
    { L"DE", L"Germany",       "DEU", "DEU" },
    { L"JP", L"Japan",         "JPN", "JPN" },
    { L"IN", L"India",         "IND", "IND" },
    { L"BR", L"Brazil",        "BRA", "BRA" },
    { L"GB", L"United Kingdom","GBR", "GBR" },
    { L"FR", L"France",        "FRA", "FRA" },
    { L"IT", L"Italy",         "ITA", "ITA" },
    { L"RU", L"Russia",        "RUS", "RUS" },
    { L"AU", L"Australia",     "AUS", "AUS" },
    { L"MX", L"Mexico",        "MEX", "MEX" },
    { L"KR", L"South Korea",   "KOR", "KOR" },
    { L"ZA", L"South Africa",  "ZAF", "ZAF" },
    { L"CA", L"Canada",        "CAN", "CAN" },
    { L"ES", L"Spain",         "ESP", "ESP" },
    { L"NL", L"Netherlands",   "NLD", "NLD" },
    { L"NO", L"Norway",        "NOR", "NOR" },
    { L"PL", L"Poland",        "POL", "POL" },
    { L"SA", L"Saudi Arabia",  "SAU", "SAU" },
    { L"AE", L"UAE",           "ARE", "ARE" },
    { L"TR", L"Turkey",        "TUR", "TUR" },
};

static ProdCountry g_pc[PROD_COUNTRY_MAX];
static int g_pc_n;
static wchar_t g_prod_note[96] = L"OWID annual + EIA";

static const wchar_t *FUEL_LBL[FUEL_COUNT] = {
    L"SOL", L"WIN", L"HYD", L"NUC", L"GAS", L"COAL", L"OIL", L"BIO", L"OTH"
};

const wchar_t *production_fuel_label(int fuel) {
    if (fuel < 0 || fuel >= FUEL_COUNT) return L"?";
    return FUEL_LBL[fuel];
}

void production_init(void) {
    int i, n = (int)(sizeof(C_DEF) / sizeof(C_DEF[0]));
    if (n > PROD_COUNTRY_MAX) n = PROD_COUNTRY_MAX;
    g_pc_n = n;
    memset(g_pc, 0, sizeof(g_pc));
    for (i = 0; i < n; i++) {
        lstrcpynW(g_pc[i].iso, C_DEF[i].iso, 4);
        lstrcpynW(g_pc[i].name, C_DEF[i].name, (int)(sizeof(g_pc[i].name) / sizeof(wchar_t)));
    }
}

int production_country_count(void) { return g_pc_n; }

const ProdCountry *production_get(int i) {
    if (i < 0 || i >= g_pc_n) return NULL;
    return &g_pc[i];
}

static float parse_f(const char *s) {
    char *e = NULL;
    double v;
    if (!s || !*s) return 0.0f;
    v = strtod(s, &e);
    return (e == s) ? 0.0f : (float)v;
}

static int col_find(const char *hdr, const char *name) {
    const char *p = hdr;
    int idx = 0;
    while (*p) {
        const char *comma = p;
        size_t n = strlen(name);
        while (*comma && *comma != ',') comma++;
        if ((size_t)(comma - p) == n && strncmp(p, name, n) == 0)
            return idx;
        idx++;
        if (*comma == ',') p = comma + 1;
        else break;
    }
    return -1;
}

static const char *row_field(const char *line, int col, char *buf, size_t cap) {
    const char *p = line;
    int i = 0;
    if (col < 0 || !line || !buf || cap < 2) return NULL;
    while (*p) {
        const char *comma = p;
        while (*comma && *comma != ',') comma++;
        if (i == col) {
            size_t n = (size_t)(comma - p);
            if (n >= cap) n = cap - 1;
            memcpy(buf, p, n);
            buf[n] = 0;
            return buf;
        }
        i++;
        if (*comma == ',') p = comma + 1;
        else break;
    }
    return NULL;
}

static void owid_apply_row(const char *line, const int cols[11], int year) {
    char fld[64];
    int i;
    if (!row_field(line, 2, fld, sizeof(fld))) return;
    for (i = 0; i < g_pc_n; i++) {
        float pri, sol, win, hyd, nuc, gas, coal, oil, bio, oth, elec;
        if (strcmp(C_DEF[i].iso3, fld) != 0) continue;
        if (g_pc[i].year > 0 && year < (int)g_pc[i].year) continue;
        pri = sol = win = hyd = nuc = gas = coal = oil = bio = oth = elec = 0.0f;
        if (cols[0] >= 0 && row_field(line, cols[0], fld, sizeof(fld))) pri = parse_f(fld);
        if (cols[1] >= 0 && row_field(line, cols[1], fld, sizeof(fld))) sol = parse_f(fld);
        if (cols[2] >= 0 && row_field(line, cols[2], fld, sizeof(fld))) win = parse_f(fld);
        if (cols[3] >= 0 && row_field(line, cols[3], fld, sizeof(fld))) hyd = parse_f(fld);
        if (cols[4] >= 0 && row_field(line, cols[4], fld, sizeof(fld))) nuc = parse_f(fld);
        if (cols[5] >= 0 && row_field(line, cols[5], fld, sizeof(fld))) gas = parse_f(fld);
        if (cols[6] >= 0 && row_field(line, cols[6], fld, sizeof(fld))) coal = parse_f(fld);
        if (cols[7] >= 0 && row_field(line, cols[7], fld, sizeof(fld))) oil = parse_f(fld);
        if (cols[8] >= 0 && row_field(line, cols[8], fld, sizeof(fld))) bio = parse_f(fld);
        if (cols[9] >= 0 && row_field(line, cols[9], fld, sizeof(fld))) oth = parse_f(fld);
        if (cols[10] >= 0 && row_field(line, cols[10], fld, sizeof(fld))) elec = parse_f(fld);
        if (pri <= 0.0f && elec <= 0.0f) continue;
        if (pri > 0.0f) {
            g_pc[i].consumption_mtoe = pri / 11.63f;
            g_pc[i].have_flow = 1;
        }
        g_pc[i].year = (uint16_t)year;
        g_pc[i].gen[FUEL_SOLAR] = sol;
        g_pc[i].gen[FUEL_WIND] = win;
        g_pc[i].gen[FUEL_HYDRO] = hyd;
        g_pc[i].gen[FUEL_NUCLEAR] = nuc;
        g_pc[i].gen[FUEL_GAS] = gas;
        g_pc[i].gen[FUEL_COAL] = coal;
        g_pc[i].gen[FUEL_OIL] = oil;
        g_pc[i].gen[FUEL_BIO] = bio;
        g_pc[i].gen[FUEL_OTHER] = oth;
        g_pc[i].demand_twh = elec > 0.0f ? elec
            : sol + win + hyd + nuc + gas + coal + oil + bio + oth;
        g_pc[i].have_gen = g_pc[i].demand_twh > 0.0f;
        break;
    }
}

static void production_load_owid(void) {
    char line[16384];
    FILE *f;
    int cols[11];
    int c_pri, c_sol, c_win, c_hyd, c_nuc, c_gas, c_coal, c_oil, c_bio, c_oth, c_elec;
    int loaded = 0, i;

    f = fopen("cache\\owid\\owid-energy-data.csv", "r");
    if (!f) {
        lstrcpyW(g_prod_note, L"OWID cache mancante");
        return;
    }
    if (!fgets(line, sizeof(line), f)) { fclose(f); return; }
    c_pri = col_find(line, "primary_energy_consumption");
    c_sol = col_find(line, "solar_electricity");
    c_win = col_find(line, "wind_electricity");
    c_hyd = col_find(line, "hydro_electricity");
    c_nuc = col_find(line, "nuclear_electricity");
    c_gas = col_find(line, "gas_electricity");
    c_coal = col_find(line, "coal_electricity");
    c_oil = col_find(line, "oil_electricity");
    c_bio = col_find(line, "biofuel_electricity");
    c_oth = col_find(line, "other_renewable_electricity");
    c_elec = col_find(line, "electricity_generation");
    cols[0] = c_pri; cols[1] = c_sol; cols[2] = c_win; cols[3] = c_hyd;
    cols[4] = c_nuc; cols[5] = c_gas; cols[6] = c_coal; cols[7] = c_oil;
    cols[8] = c_bio; cols[9] = c_oth; cols[10] = c_elec;
    while (fgets(line, sizeof(line), f)) {
        char fld[16];
        int year = 0;
        if (!row_field(line, 1, fld, sizeof(fld))) continue;
        year = atoi(fld);
        if (year < 2000) continue;
        owid_apply_row(line, cols, year);
    }
    fclose(f);
    for (i = 0; i < g_pc_n; i++)
        if (g_pc[i].have_flow || g_pc[i].have_gen) loaded++;
    wsprintfW(g_prod_note, L"OWID %d/%d paesi  US ref %u", loaded, g_pc_n, g_pc[0].year);
}

void production_refresh(void) {
    int i;
    if (g_pc_n <= 0) production_init();
    production_load_owid();
    for (i = 0; i < g_pc_n; i++) {
        uint16_t yr = 0;
        float mtoe = 0.0f;
        if (C_DEF[i].eia_iso2 && ingest_eia_have_key() &&
            ingest_eia_country_primary(C_DEF[i].eia_iso2, &mtoe, &yr)) {
            g_pc[i].consumption_mtoe = mtoe;
            g_pc[i].year = yr;
            g_pc[i].have_flow = 1;
        }
    }
}

typedef struct { HDC dc; RECT rc; } PwrBarCtx;

static void pwr_bar_cb(const SeriesStore *st, void *ctx) {
    PwrBarCtx *p = (PwrBarCtx *)ctx;
    static const char *PWR_IDS[] = { "PDE", "PFR", "PIT", "PNL", "PPL" };
    static const wchar_t *PWR_LBL[] = { L"DE", L"FR", L"IT", L"NL", L"PL" };
    chart_bar_last(p->dc, &p->rc, st, PWR_IDS, PWR_LBL, 5, L"EUR/MWh DA");
}

void production_paint(HDC dc, const RECT *rc) {
    RECT r = *rc, charts, tbl, gloss, pwr;
    PwrBarCtx pbc;
    int col_w, y, i, f;
    wchar_t hdr[128], cell[16];
    static const int MIX_IDX[] = { 0, 2, 8 };

    if (r.bottom <= r.top + 40) return;

    gloss = r;
    gloss.left = gloss.right - 228;
    r.right = gloss.left - 8;
    gloss_paint_panel(dc, &gloss, PAGE_GEO);

    charts = r;
    charts.bottom = r.top + 108;
    ui_subheading(dc, &(RECT){ charts.left, charts.top, charts.right, charts.top + 12 },
                  L"MIX ELETTRICO OWID");
    charts.top += 14;
    for (i = 0; i < 3; i++) {
        RECT mix = charts;
        const ProdCountry *p = production_get(MIX_IDX[i]);
        mix.right = mix.left + (charts.right - charts.left) / 3 - 4;
        mix.left += i * ((charts.right - charts.left) / 3);
        if (p && p->have_gen)
            chart_fuel_stack(dc, &mix, p);
    }

    pwr = r;
    pwr.top = charts.bottom + 6;
    pwr.bottom = pwr.top + 52;
    ui_subheading(dc, &(RECT){ pwr.left, pwr.top, pwr.right, pwr.top + 12 },
                  L"POWER DAY-AHEAD  EUR/MWh");
    pwr.top += 14;
    pbc.dc = dc;
    pbc.rc = pwr;
    data_store_read(pwr_bar_cb, &pbc);

    tbl = r;
    tbl.top = pwr.bottom + 8;
    col_w = 36;
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    SetTextColor(dc, CLR_DIM);
    wsprintfW(hdr, L"%-14s", L"COUNTRY");
    TextOutW(dc, tbl.left, tbl.top, hdr, lstrlenW(hdr));
    for (f = 0; f < FUEL_COUNT; f++) {
        int x = tbl.left + 112 + f * col_w;
        TextOutW(dc, x, tbl.top, production_fuel_label(f), lstrlenW(production_fuel_label(f)));
    }
    TextOutW(dc, tbl.left + 112 + FUEL_COUNT * col_w + 6, tbl.top, L"TWh", 3);
    TextOutW(dc, tbl.left + 112 + FUEL_COUNT * col_w + 48, tbl.top, L"Mtoe", 4);
    y = tbl.top + 16;
    ui_hline(dc, tbl.left, y - 2, tbl.right, CLR_GRID);

    for (i = 0; i < g_pc_n; i++) {
        const ProdCountry *p = &g_pc[i];
        if (y + 14 > tbl.bottom - 16) break;
        SetTextColor(dc, CLR_TXT);
        wsprintfW(hdr, L"%-2s %-11s", p->iso, p->name);
        TextOutW(dc, tbl.left, y, hdr, lstrlenW(hdr));
        for (f = 0; f < FUEL_COUNT; f++) {
            int x = tbl.left + 112 + f * col_w;
            if (p->have_gen && p->gen[f] > 0.0f) {
                ui_fmt_wdouble(cell, 16, p->gen[f], f >= FUEL_GAS ? 0 : 1);
                SetTextColor(dc, CLR_ACC);
            } else {
                lstrcpyW(cell, L"-");
                SetTextColor(dc, CLR_OFF);
            }
            TextOutW(dc, x, y, cell, lstrlenW(cell));
        }
        if (p->demand_twh > 0.0f) {
            ui_fmt_wdouble(cell, 16, p->demand_twh, 0);
            SetTextColor(dc, CLR_TXT);
            TextOutW(dc, tbl.left + 112 + FUEL_COUNT * col_w + 6, y, cell, lstrlenW(cell));
        }
        if (p->have_flow && p->consumption_mtoe > 0.0f) {
            ui_fmt_wdouble(cell, 16, p->consumption_mtoe, 1);
            TextOutW(dc, tbl.left + 112 + FUEL_COUNT * col_w + 48, y, cell, lstrlenW(cell));
        }
        y += 14;
    }
    SetTextColor(dc, CLR_OFF);
    TextOutW(dc, tbl.left, tbl.bottom - 14, g_prod_note, lstrlenW(g_prod_note));
    gloss_paint_footer(dc, &(RECT){ r.left, tbl.bottom - 28, r.right, tbl.bottom - 16 },
                       PAGE_GEO);
}
