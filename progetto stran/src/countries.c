#include "countries.h"
#include "chart.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    uint16_t year;
    float primary_twh;
    float elec_twh;
    float ren_share;
    float fossil_share;
    float solar_twh;
    float wind_twh;
    float coal_twh;
    float gas_twh;
    float nuclear_twh;
    float hydro_twh;
    float ghg;
    float kwh_pc;
} CtryYearPt;

typedef struct {
    wchar_t iso2[4];
    wchar_t name[22];
    char    iso3[4];
    int     n;
    CtryYearPt pt[CTRY_HIST_MAX];
} CountryRec;

static const struct {
    const wchar_t *iso2;
    const char *iso3;
    const wchar_t *name;
} OWID_MAP[] = {
    { L"US", "USA", L"United States" },
    { L"CN", "CHN", L"China" },
    { L"DE", "DEU", L"Germany" },
    { L"JP", "JPN", L"Japan" },
    { L"IN", "IND", L"India" },
    { L"BR", "BRA", L"Brazil" },
    { L"GB", "GBR", L"United Kingdom" },
    { L"FR", "FRA", L"France" },
    { L"IT", "ITA", L"Italy" },
    { L"RU", "RUS", L"Russia" },
    { L"AU", "AUS", L"Australia" },
    { L"MX", "MEX", L"Mexico" },
    { L"KR", "KOR", L"South Korea" },
    { L"ZA", "ZAF", L"South Africa" },
    { L"CA", "CAN", L"Canada" },
    { L"ES", "ESP", L"Spain" },
    { L"NL", "NLD", L"Netherlands" },
    { L"NO", "NOR", L"Norway" },
    { L"PL", "POL", L"Poland" },
    { L"SA", "SAU", L"Saudi Arabia" },
    { L"AE", "ARE", L"United Arab Emirates" },
    { L"TR", "TUR", L"Turkey" },
};

static CountryRec g_ctry[CTRY_MAX];
static int g_ctry_n;
static int g_sel;
static RECT g_list_rc;
static int  g_list_y0;

static uint32_t g_mkt_ymd[SER_POINTS];
static float g_mkt_px[SER_POINTS];
static float g_mkt_ren[SER_POINTS];
static float g_mkt_ghg[SER_POINTS];
static int g_mkt_n;

static wchar_t g_status[128] = L"OWID: attesa cache";

static float parse_f(const char *s) {
    char *e = NULL;
    double v;

    if (!s || !*s) return 0.0f;
    v = strtod(s, &e);
    if (e == s) return 0.0f;
    return (float)v;
}

static int parse_year(const char *s) {
    long y;

    if (!s || !*s) return 0;
    y = strtol(s, NULL, 10);
    if (y < 1900 || y > 2100) return 0;
    return (int)y;
}

static uint32_t parse_ts_ymd(const char *s) {
    int y, m, d;

    if (!s || strlen(s) < 10) return 0;
    if (sscanf(s, "%d-%d-%d", &y, &m, &d) != 3) return 0;
    if (y < 2000 || y > 2100 || m < 1 || m > 12 || d < 1 || d > 31) return 0;
    return (uint32_t)y * 10000u + (uint32_t)m * 100u + (uint32_t)d;
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

static CountryRec *ctry_by_iso3(const char *iso3) {
    int i;

    for (i = 0; i < g_ctry_n; i++)
        if (strcmp(g_ctry[i].iso3, iso3) == 0)
            return &g_ctry[i];
    return NULL;
}

static void ctry_seed_catalog(void) {
    int i, n = (int)(sizeof(OWID_MAP) / sizeof(OWID_MAP[0]));

    g_ctry_n = 0;
    if (n > CTRY_MAX) n = CTRY_MAX;
    memset(g_ctry, 0, sizeof(g_ctry));
    for (i = 0; i < n; i++) {
        lstrcpynW(g_ctry[i].iso2, OWID_MAP[i].iso2, 4);
        lstrcpynW(g_ctry[i].name, OWID_MAP[i].name, 22);
        lstrcpynA(g_ctry[i].iso3, OWID_MAP[i].iso3, 4);
    }
    g_ctry_n = n;
}

static void load_owid_csv(const wchar_t *path) {
    char line[16384];
    char fld[128];
    FILE *f;
    int c_year = -1, c_iso = -1, c_pri = -1, c_ele = -1, c_ren = -1, c_fos = -1;
    int c_sol = -1, c_win = -1, c_coal = -1, c_gas = -1, c_nuc = -1, c_hyd = -1;
    int c_ghg = -1, c_kwh = -1;
    int rows = 0;

    f = _wfopen(path, L"r");
    if (!f) return;
    if (!fgets(line, sizeof(line), f)) { fclose(f); return; }
    c_year = col_find(line, "year");
    c_iso = col_find(line, "iso_code");
    c_pri = col_find(line, "primary_energy_consumption");
    c_ele = col_find(line, "electricity_generation");
    c_ren = col_find(line, "renewables_share_elec");
    c_fos = col_find(line, "fossil_share_elec");
    c_sol = col_find(line, "solar_electricity");
    c_win = col_find(line, "wind_electricity");
    c_coal = col_find(line, "coal_electricity");
    c_gas = col_find(line, "gas_electricity");
    c_nuc = col_find(line, "nuclear_electricity");
    c_hyd = col_find(line, "hydro_electricity");
    c_ghg = col_find(line, "greenhouse_gas_emissions");
    c_kwh = col_find(line, "per_capita_electricity");
    if (c_year < 0 || c_iso < 0) { fclose(f); return; }

    while (fgets(line, sizeof(line), f)) {
        CountryRec *c;
        CtryYearPt *pt;
        int yr;

        if (!row_field(line, c_iso, fld, sizeof(fld))) continue;
        c = ctry_by_iso3(fld);
        if (!c) continue;
        if (!row_field(line, c_year, fld, sizeof(fld))) continue;
        yr = parse_year(fld);
        if (yr < 1965) continue;
        if (c->n >= CTRY_HIST_MAX) continue;
        pt = &c->pt[c->n];
        pt->year = (uint16_t)yr;
        pt->primary_twh = c_pri >= 0 && row_field(line, c_pri, fld, sizeof(fld)) ? parse_f(fld) : 0.0f;
        pt->elec_twh = c_ele >= 0 && row_field(line, c_ele, fld, sizeof(fld)) ? parse_f(fld) : 0.0f;
        pt->ren_share = c_ren >= 0 && row_field(line, c_ren, fld, sizeof(fld)) ? parse_f(fld) : 0.0f;
        pt->fossil_share = c_fos >= 0 && row_field(line, c_fos, fld, sizeof(fld)) ? parse_f(fld) : 0.0f;
        pt->solar_twh = c_sol >= 0 && row_field(line, c_sol, fld, sizeof(fld)) ? parse_f(fld) : 0.0f;
        pt->wind_twh = c_win >= 0 && row_field(line, c_win, fld, sizeof(fld)) ? parse_f(fld) : 0.0f;
        pt->coal_twh = c_coal >= 0 && row_field(line, c_coal, fld, sizeof(fld)) ? parse_f(fld) : 0.0f;
        pt->gas_twh = c_gas >= 0 && row_field(line, c_gas, fld, sizeof(fld)) ? parse_f(fld) : 0.0f;
        pt->nuclear_twh = c_nuc >= 0 && row_field(line, c_nuc, fld, sizeof(fld)) ? parse_f(fld) : 0.0f;
        pt->hydro_twh = c_hyd >= 0 && row_field(line, c_hyd, fld, sizeof(fld)) ? parse_f(fld) : 0.0f;
        pt->ghg = c_ghg >= 0 && row_field(line, c_ghg, fld, sizeof(fld)) ? parse_f(fld) : 0.0f;
        pt->kwh_pc = c_kwh >= 0 && row_field(line, c_kwh, fld, sizeof(fld)) ? parse_f(fld) : 0.0f;
        if (pt->primary_twh <= 0.0f && pt->elec_twh <= 0.0f) continue;
        c->n++;
        rows++;
    }
    fclose(f);
    wsprintfW(g_status, L"OWID %d righe paese-anno", rows);
}

static float ctry_last_metric(const CountryRec *p) {
    float pri, elec;

    if (!p || p->n <= 0) return 0.0f;
    pri = p->pt[p->n - 1].primary_twh;
    elec = p->pt[p->n - 1].elec_twh;
    if (pri > 0.0f) return pri;
    return elec;
}

static float ctry_last_ren(const CountryRec *p) {
    if (!p || p->n <= 0) return 0.0f;
    return p->pt[p->n - 1].ren_share;
}

static int ctry_cmp(const void *a, const void *b) {
    const CountryRec *ca = (const CountryRec *)a;
    const CountryRec *cb = (const CountryRec *)b;
    float va = ctry_last_metric(ca);
    float vb = ctry_last_metric(cb);

    if (va > vb) return -1;
    if (va < vb) return 1;
    return cb->n - ca->n;
}

static void ctry_sort_loaded(void) {
    qsort(g_ctry, (size_t)g_ctry_n, sizeof(g_ctry[0]), ctry_cmp);
}

static void load_market_csv(const wchar_t *path) {
    char line[2048];
    char fld[64];
    FILE *f;
    int c_ts = -1, c_px = -1, c_ren = -1, c_ghg = -1;
    int step = 0, kept = 0;
    uint32_t last_day = 0;

    g_mkt_n = 0;
    f = _wfopen(path, L"r");
    if (!f) return;
    if (!fgets(line, sizeof(line), f)) { fclose(f); return; }
    c_ts = col_find(line, "Timestamp");
    c_px = col_find(line, "Historical_Electricity_Prices");
    c_ren = col_find(line, "Renewable_Penetration_Rate");
    c_ghg = col_find(line, "GHG_Emissions");
    if (c_ts < 0 || c_px < 0) { fclose(f); return; }

    while (fgets(line, sizeof(line), f) && g_mkt_n < SER_POINTS) {
        uint32_t ymd;

        if (!row_field(line, c_ts, fld, sizeof(fld))) continue;
        ymd = parse_ts_ymd(fld);
        if (!ymd) continue;
        step++;
        if (ymd == last_day) continue;
        if (step % 24 != 1 && last_day != 0) continue;
        last_day = ymd;
        g_mkt_ymd[g_mkt_n] = ymd;
        g_mkt_px[g_mkt_n] = row_field(line, c_px, fld, sizeof(fld)) ? parse_f(fld) : 0.0f;
        g_mkt_ren[g_mkt_n] = c_ren >= 0 && row_field(line, c_ren, fld, sizeof(fld)) ? parse_f(fld) : 0.0f;
        g_mkt_ghg[g_mkt_n] = c_ghg >= 0 && row_field(line, c_ghg, fld, sizeof(fld)) ? parse_f(fld) : 0.0f;
        if (g_mkt_px[g_mkt_n] > 0.0f) {
            g_mkt_n++;
            kept++;
        }
    }
    fclose(f);
    if (kept > 0) {
        wchar_t tail[48];
        wsprintfW(tail, L"  |  market %dd", kept);
        if (lstrlenW(g_status) + lstrlenW(tail) < 120) lstrcatW(g_status, tail);
    }
}

void countries_init(void) {
    ctry_seed_catalog();
    countries_reload();
}

void countries_reload(void) {
    CreateDirectoryW(L"cache\\owid", NULL);
    CreateDirectoryW(L"cache\\electricity_market", NULL);
    ctry_seed_catalog();
    load_owid_csv(L"cache\\owid\\owid-energy-data.csv");
    load_market_csv(L"cache\\electricity_market\\electricity_market_dataset.csv");
    ctry_sort_loaded();
    if (g_sel >= g_ctry_n) g_sel = 0;
}

int countries_count(void) { return g_ctry_n; }
int countries_selected(void) { return g_sel; }

void countries_set_selected(int i) {
    if (i < 0 || i >= g_ctry_n) return;
    g_sel = i;
}

int countries_list_hit(POINT pt) {
    int i, y0;

    if (!PtInRect(&g_list_rc, pt)) return -1;
    y0 = g_list_y0;
    if (pt.y < y0) return -1;
    i = (pt.y - y0) / 14;
    if (i < 0 || i >= g_ctry_n) return -1;
    return i;
}

const wchar_t *countries_status_line(void) { return g_status; }

static void fill_series(DataSeries *s, const wchar_t *lbl, uint8_t kind,
                        const uint32_t *ymd, const float *val, int n) {
    int i;

    memset(s, 0, sizeof(*s));
    lstrcpynW(s->label, lbl, 14);
    s->kind = kind;
    if (n > SER_POINTS) n = SER_POINTS;
    s->n = (uint16_t)n;
    for (i = 0; i < n; i++) {
        s->ymd[i] = ymd[i];
        s->val[i] = val[i];
        if (i == 0 || val[i] < s->min_h) s->min_h = val[i];
        if (i == 0 || val[i] > s->max_h) s->max_h = val[i];
    }
    if (n > 0) s->live = val[n - 1];
}

static void ctry_series(const CountryRec *c, float (*getter)(const CtryYearPt *),
                        DataSeries *out, const wchar_t *lbl) {
    static uint32_t ymd[CTRY_HIST_MAX];
    static float val[CTRY_HIST_MAX];
    int i, n = 0;

    for (i = 0; i < c->n; i++) {
        float v = getter(&c->pt[i]);
        if (v <= 0.0f) continue;
        ymd[n] = (uint32_t)c->pt[i].year * 10000u + 701u;
        val[n] = v;
        n++;
    }
    fill_series(out, lbl, SER_ENERGY, ymd, val, n);
}

static void paint_fuel_mix(HDC dc, const RECT *rc, const CountryRec *c) {
    RECT bar = *rc;
    const CtryYearPt *p;
    float parts[6], sum = 0.0f;
    COLORREF cols[6] = { RGB(180,180,180), RGB(120,120,120), RGB(90,160,220),
                         RGB(80,200,120), RGB(220,200,80), RGB(200,120,200) };
    const wchar_t *tags[6] = { L"COAL", L"GAS", L"HYD", L"WIN", L"SOL", L"NUC" };
    int i, x, w, filled;
    wchar_t cap[64];

    if (!c || c->n <= 0) return;
    p = &c->pt[c->n - 1];
    parts[0] = p->coal_twh;
    parts[1] = p->gas_twh;
    parts[2] = p->hydro_twh;
    parts[3] = p->wind_twh;
    parts[4] = p->solar_twh;
    parts[5] = p->nuclear_twh;
    for (i = 0; i < 6; i++) sum += parts[i];
    wsprintfW(cap, L"MIX ELETTRICO %u", (unsigned)p->year);
    ui_subheading(dc, &bar, cap);
    bar.top += 14;
    if (sum <= 0.0f) {
        ui_label_rect(dc, &bar, L"mix non disponibile", CLR_OFF, fSm);
        return;
    }
    w = bar.right - bar.left;
    x = bar.left;
    filled = bar.top + 10;
    for (i = 0; i < 6; i++) {
        int seg = (int)((parts[i] / sum) * (float)w);
        RECT seg_rc = { x, bar.top, x + seg, filled };
        if (seg > 0) {
            HBRUSH b = CreateSolidBrush(cols[i]);
            FillRect(dc, &seg_rc, b);
            DeleteObject(b);
            x += seg;
        }
    }
    bar.top = filled + 8;
    SetTextColor(dc, CLR_DIM);
    SelectObject(dc, fSm);
    for (i = 0; i < 6; i++) {
        RECT leg;
        wchar_t seg[24];
        if (parts[i] <= 0.0f) continue;
        wsprintfW(seg, L"%s %.0f", tags[i], parts[i]);
        leg.left = bar.left + (i % 3) * ((bar.right - bar.left) / 3);
        leg.right = leg.left + (bar.right - bar.left) / 3 - 4;
        leg.top = bar.top + (i / 3) * 12;
        leg.bottom = leg.top + 12;
        DrawTextW(dc, seg, -1, &leg, DT_LEFT | DT_SINGLELINE | DT_END_ELLIPSIS | DT_NOPREFIX);
    }
}

static float get_primary(const CtryYearPt *p) { return p->primary_twh; }
static float get_elec(const CtryYearPt *p) { return p->elec_twh; }
static float get_ren(const CtryYearPt *p) { return p->ren_share; }
static float get_fossil(const CtryYearPt *p) { return p->fossil_share; }
static float get_solar(const CtryYearPt *p) { return p->solar_twh; }
static float get_wind(const CtryYearPt *p) { return p->wind_twh; }

void countries_paint(HDC dc, const RECT *rc) {
    RECT r = *rc, list, charts, mix, mkt;
    const CountryRec *c;
    wchar_t row[96], val[16], ren[16];
    int i, y, x0, cw, ch;
    DataSeries s;

    if (r.bottom <= r.top + 40) return;
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    SetTextColor(dc, CLR_DIM);
    TextOutW(dc, r.left, r.top, countries_status_line(), lstrlenW(countries_status_line()));
    r.top += 14;

    list = r;
    list.right = r.left + (r.right - r.left) * 38 / 100;
    charts.left = list.right + 8;
    charts.right = r.right;
    charts.top = r.top;
    charts.bottom = r.top + (r.bottom - r.top) * 52 / 100;
    mix.left = charts.left;
    mix.right = charts.right;
    mix.top = charts.bottom + 4;
    mix.bottom = mix.top + 56;
    mkt.left = r.left;
    mkt.right = r.right;
    mkt.top = mix.bottom + 6;
    mkt.bottom = r.bottom;
    g_list_rc = list;

    ui_subheading(dc, &list, L"PAESI  (click)");
    list.top += 16;
    g_list_y0 = list.top;
    y = list.top;
    for (i = 0; i < g_ctry_n; i++) {
        const CountryRec *p = &g_ctry[i];
        float metric = ctry_last_metric(p);
        float ren_v = ctry_last_ren(p);
        RECT row_rc;

        if (y + 14 > list.bottom) break;
        row_rc.left = list.left;
        row_rc.right = list.right;
        row_rc.top = y;
        row_rc.bottom = y + 14;
        if (i == g_sel) {
            FillRect(dc, &row_rc, bBand);
            SetTextColor(dc, CLR_ACC);
        } else {
            SetTextColor(dc, p->n > 0 ? CLR_TXT : CLR_OFF);
        }
        ui_fmt_wdouble(val, 16, metric, metric >= 1000.0f ? 0 : 1);
        ui_fmt_wdouble(ren, 16, ren_v, 0);
        wsprintfW(row, L"%.2s %-9s %5s TWh %s%% ren",
                  p->iso2, p->name, val, ren);
        DrawTextW(dc, row, -1, &row_rc, DT_LEFT | DT_VCENTER | DT_SINGLELINE |
                  DT_END_ELLIPSIS | DT_NOPREFIX);
        y += 14;
    }

    c = (g_sel >= 0 && g_sel < g_ctry_n) ? &g_ctry[g_sel] : NULL;
    if (c && c->n >= 2) {
        wchar_t title[56];
        const CtryYearPt *last = &c->pt[c->n - 1];

        wsprintfW(title, L"%s %s  OWID %u-%u", c->iso2, c->name,
                  (unsigned)c->pt[0].year, (unsigned)last->year);
        ui_subheading(dc, &charts, title);
        charts.top += 16;
        cw = (charts.right - charts.left - 8) / 3;
        ch = (charts.bottom - charts.top - 8) / 2;
        for (i = 0; i < 6; i++) {
            RECT cell;
            x0 = charts.left + (i % 3) * (cw + 4);
            y = charts.top + (i / 3) * (ch + 4);
            cell.left = x0;
            cell.top = y;
            cell.right = x0 + cw;
            cell.bottom = y + ch;
            if (i == 0) ctry_series(c, get_primary, &s, L"PRI TWh");
            else if (i == 1) ctry_series(c, get_elec, &s, L"ELEC TWh");
            else if (i == 2) ctry_series(c, get_ren, &s, L"REN %");
            else if (i == 3) ctry_series(c, get_solar, &s, L"SOL TWh");
            else if (i == 4) ctry_series(c, get_wind, &s, L"WIN TWh");
            else ctry_series(c, get_fossil, &s, L"FOSS %");
            if (s.n >= 2) chart_series_cell(dc, &cell, &s);
        }
        paint_fuel_mix(dc, &mix, c);
    } else {
        ui_label_rect(dc, &charts, L"OWID: cache\\owid\\owid-energy-data.csv mancante", CLR_OFF, fLbl);
    }

    if (g_mkt_n >= 2) {
        RECT c0, c1, c2;
        int mw = (mkt.right - mkt.left - 8) / 3;

        ui_subheading(dc, &mkt, L"ELECTRICITY MARKET  storico");
        mkt.top += 16;
        c0.left = mkt.left; c0.top = mkt.top;
        c0.right = mkt.left + mw; c0.bottom = mkt.bottom;
        c1.left = c0.right + 4; c1.top = mkt.top;
        c1.right = c1.left + mw; c1.bottom = mkt.bottom;
        c2.left = c1.right + 4; c2.top = mkt.top;
        c2.right = mkt.right; c2.bottom = mkt.bottom;
        fill_series(&s, L"PX EUR", SER_ENERGY, g_mkt_ymd, g_mkt_px, g_mkt_n);
        chart_series_cell(dc, &c0, &s);
        fill_series(&s, L"REN %", SER_ENERGY, g_mkt_ymd, g_mkt_ren, g_mkt_n);
        chart_series_cell(dc, &c1, &s);
        fill_series(&s, L"GHG idx", SER_ENERGY, g_mkt_ymd, g_mkt_ghg, g_mkt_n);
        chart_series_cell(dc, &c2, &s);
    }
}
