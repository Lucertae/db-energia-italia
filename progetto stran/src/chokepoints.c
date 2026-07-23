#include "chokepoints.h"
#include "ships.h"
#include "intel.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CP_HIST_MAX 4096

typedef struct {
    char date[12];
    char desk_id[12];
    int  n_total;
    int  n_tanker;
} CpHist;

static ChokepointRow g_cp[CP_MAX_ROWS];
static int g_cp_n;
static IntelHeadline g_head[CP_MAX_HEAD];
static int g_head_n;
static CpHist g_hist[CP_HIST_MAX];
static int g_hist_n;

static void cp_seed_row(int i, const char *desk, const char *pw, const char *name,
                        float lat, float lon,
                        float lat0, float lat1, float lon0, float lon1) {
    ChokepointRow *r = &g_cp[i];

    memset(r, 0, sizeof(*r));
    lstrcpynA(r->desk_id, desk, (int)sizeof(r->desk_id));
    lstrcpynA(r->pw_id, pw, (int)sizeof(r->pw_id));
    lstrcpynA(r->name, name, CP_NAME_LEN);
    r->lat = lat;
    r->lon = lon;
    r->bbox[0] = lat0;
    r->bbox[1] = lat1;
    r->bbox[2] = lon0;
    r->bbox[3] = lon1;
}

void chokepoints_init(void) {
    g_cp_n = 0;
    g_head_n = 0;
    g_hist_n = 0;
    cp_seed_row(g_cp_n++, "HORMUZ", "chokepoint6", "Strait of Hormuz",
                26.56f, 56.25f, 26.0f, 27.0f, 55.5f, 57.0f);
    cp_seed_row(g_cp_n++, "MALACCA", "chokepoint5", "Strait of Malacca",
                2.5f, 101.5f, 0.5f, 6.0f, 99.0f, 104.5f);
    cp_seed_row(g_cp_n++, "CAPE", "chokepoint7", "Cape of Good Hope",
                -34.35f, 18.47f, -36.0f, -32.0f, 17.0f, 20.0f);
    cp_seed_row(g_cp_n++, "BAB", "chokepoint4", "Bab el-Mandeb",
                12.58f, 43.33f, 12.0f, 13.5f, 42.5f, 44.5f);
    cp_seed_row(g_cp_n++, "SUNDA", "chokepoint19", "Sunda Strait",
                -5.8f, 105.9f, -7.0f, -5.0f, 104.5f, 106.5f);
    cp_seed_row(g_cp_n++, "LOMBOK", "chokepoint15", "Lombok Strait",
                -8.5f, 115.8f, -9.5f, -7.5f, 115.0f, 116.5f);
    cp_seed_row(g_cp_n++, "SUEZ", "chokepoint1", "Suez Canal",
                30.0f, 32.5f, 29.5f, 31.5f, 32.0f, 33.5f);
}

static ChokepointRow *cp_find_desk(const char *desk_id) {
    int i;
    for (i = 0; i < g_cp_n; i++)
        if (lstrcmpiA(g_cp[i].desk_id, desk_id) == 0)
            return &g_cp[i];
    return NULL;
}

static void cp_compute_baselines(void) {
    int i, j;

    for (i = 0; i < g_cp_n; i++) {
        ChokepointRow *r = &g_cp[i];
        long sum = 0;
        int cnt = 0;

        r->baseline_total = 0;
        r->delta_pct = 0;
        for (j = 0; j < g_hist_n; j++) {
            if (lstrcmpiA(g_hist[j].desk_id, r->desk_id) != 0) continue;
            if (r->last_date[0] && lstrcmpA(g_hist[j].date, r->last_date) == 0)
                continue;
            sum += g_hist[j].n_total;
            cnt++;
            if (cnt >= 30) break;
        }
        if (cnt > 0)
            r->baseline_total = (int)(sum / cnt);
        if (r->baseline_total > 0 && r->n_total > 0)
            r->delta_pct = (int)(((long)r->n_total - r->baseline_total) * 100L / r->baseline_total);
    }
}

int chokepoints_reload(void) {
    wchar_t path[MAX_PATH];
    FILE *f;
    char line[256];
    int loaded = 0;

    g_hist_n = 0;
    for (int i = 0; i < g_cp_n; i++) {
        g_cp[i].last_date[0] = 0;
        g_cp[i].n_total = 0;
        g_cp[i].n_tanker = 0;
    }

    wsprintfW(path, L"cache\\portwatch\\chokepoints.csv");
    f = _wfopen(path, L"r");
    if (!f) return 0;

    while (fgets(line, sizeof(line), f) && g_hist_n < CP_HIST_MAX) {
        char date[16], desk[16];
        int ntot = 0, ntank = 0;

        if (line[0] == 'd') continue;
        if (sscanf(line, "%15[^,],%15[^,],%*[^,],%*[^,],%d,%d", date, desk, &ntot, &ntank) < 4)
            continue;
        lstrcpynA(g_hist[g_hist_n].date, date, 12);
        lstrcpynA(g_hist[g_hist_n].desk_id, desk, 12);
        g_hist[g_hist_n].n_total = ntot;
        g_hist[g_hist_n].n_tanker = ntank;
        g_hist_n++;
        loaded++;
    }
    fclose(f);

    for (int i = 0; i < g_cp_n; i++) {
        ChokepointRow *r = &g_cp[i];
        for (int j = 0; j < g_hist_n; j++) {
            if (lstrcmpiA(g_hist[j].desk_id, r->desk_id) != 0) continue;
            if (!r->last_date[0] || lstrcmpA(g_hist[j].date, r->last_date) > 0) {
                lstrcpynA(r->last_date, g_hist[j].date, 12);
                r->n_total = g_hist[j].n_total;
                r->n_tanker = g_hist[j].n_tanker;
            }
        }
    }
    cp_compute_baselines();
    return loaded;
}

void chokepoints_ais_update(void) {
    int i;

    for (i = 0; i < g_cp_n; i++)
        g_cp[i].ais_live = ships_count_in_bbox(
            g_cp[i].bbox[0], g_cp[i].bbox[1],
            g_cp[i].bbox[2], g_cp[i].bbox[3]);
}

int chokepoints_count(void) { return g_cp_n; }

const ChokepointRow *chokepoints_get(int i) {
    if (i < 0 || i >= g_cp_n) return NULL;
    return &g_cp[i];
}

void chokepoints_brief(wchar_t *out, int cap) {
    const ChokepointRow *h, *m;

    if (!out || cap < 8) return;
    out[0] = 0;
    h = cp_find_desk("HORMUZ");
    m = cp_find_desk("MALACCA");
    if (h && h->n_total > 0) {
        if (h->delta_pct <= -40)
            wsprintfW(out, L"ALERT Hormuz transits %d%% vs 30d baseline (%d/d)", h->delta_pct, h->n_total);
        else if (h->delta_pct <= -20)
            wsprintfW(out, L"WARN Hormuz below baseline %d%%  tankers %d  AIS %d", h->delta_pct, h->n_tanker, h->ais_live);
        else
            wsprintfW(out, L"Hormuz %d transits (%+d%%)  tankers %d", h->n_total, h->delta_pct, h->n_tanker);
    }
    if (m && m->n_total > 0 && (int)lstrlenW(out) < cap - 40) {
        wchar_t tail[80];
        wsprintfW(tail, L"  |  Malacca %d (%+d%%)", m->n_total, m->delta_pct);
        lstrcatW(out, tail);
    }
}

int intel_reload_headlines(void) {
    wchar_t path[MAX_PATH];
    FILE *f;
    char line[512];

    g_head_n = 0;
    wsprintfW(path, L"cache\\intel\\headlines.csv");
    f = _wfopen(path, L"r");
    if (!f) return 0;

    while (fgets(line, sizeof(line), f) && g_head_n < CP_MAX_HEAD) {
        char ts[32], src[16], title[220], url[280];

        if (line[0] == 't') continue;
        if (sscanf(line, "%31[^,],%15[^,],%*[^,],%219[^,],%255[^\r\n]", ts, src, title, url) < 3)
            continue;
        lstrcpynA(g_head[g_head_n].ts, ts, 24);
        lstrcpynA(g_head[g_head_n].source, src, 12);
        lstrcpynA(g_head[g_head_n].title, title, 200);
        lstrcpynA(g_head[g_head_n].url, url, 256);
        g_head_n++;
    }
    fclose(f);
    return g_head_n;
}

int intel_headline_count(void) { return g_head_n; }

const IntelHeadline *intel_headline_get(int i) {
    if (i < 0 || i >= g_head_n) return NULL;
    return &g_head[i];
}

static COLORREF cp_delta_color(int delta) {
    if (delta <= -30) return RGB(255, 90, 90);
    if (delta <= -15) return RGB(255, 180, 80);
    if (delta >= 15) return RGB(120, 220, 140);
    return CLR_DIM;
}

void chokepoints_lng_eu_stats(int *count7, int *delta) {
    static const char *DESKS[] = { "SUEZ", "BAB", "HORMUZ", "MALACCA" };
    int d, j, cur = 0, prev = 0;
    char dates[14][12];
    int date_n = 0, i;

    if (count7) *count7 = 0;
    if (delta) *delta = 0;
    for (i = g_hist_n - 1; i >= 0 && date_n < 14; i--) {
        int found = 0;
        for (j = 0; j < date_n; j++)
            if (lstrcmpA(g_hist[i].date, dates[j]) == 0) { found = 1; break; }
        if (!found) {
            lstrcpynA(dates[date_n], g_hist[i].date, 12);
            date_n++;
        }
    }
    for (d = 0; d < 4; d++) {
        for (j = 0; j < g_hist_n; j++) {
            if (lstrcmpiA(g_hist[j].desk_id, DESKS[d]) != 0) continue;
            if (date_n > 0 && lstrcmpA(g_hist[j].date, dates[0]) <= 0 &&
                (date_n < 7 || lstrcmpA(g_hist[j].date, dates[6]) >= 0))
                cur += g_hist[j].n_tanker;
            if (date_n > 13 && lstrcmpA(g_hist[j].date, dates[7]) <= 0 &&
                lstrcmpA(g_hist[j].date, dates[13]) >= 0)
                prev += g_hist[j].n_tanker;
        }
    }
    if (count7) *count7 = cur;
    if (delta) *delta = cur - prev;
}

void chokepoints_paint(HDC dc, const RECT *rc) {
    RECT r = *rc;
    wchar_t line[220];
    RECT tick;
    int i, y;

    if (r.bottom <= r.top + 20) return;
    SetBkMode(dc, TRANSPARENT);
    ui_subheading(dc, &r, L"CHOKEPOINTS  IMF PortWatch + AIS live");
    r.top += 14;

    chokepoints_ais_update();
    for (i = 0; i < g_cp_n && r.top + 12 < r.bottom; i++) {
        const ChokepointRow *c = &g_cp[i];
        if (!c->n_total && !c->ais_live) continue;
        if (c->last_date[0])
            wsprintfW(line, L"%-7hs %hs  tot %3d  tnk %3d  %+3d%%  AIS %2d",
                      c->desk_id, c->last_date, c->n_total, c->n_tanker, c->delta_pct, c->ais_live);
        else
            wsprintfW(line, L"%-7hs (no PW)  AIS %2d", c->desk_id, c->ais_live);
        SetTextColor(dc, cp_delta_color(c->delta_pct));
        TextOutW(dc, r.left, r.top, line, lstrlenW(line));
        r.top += 12;
    }

    y = r.top + 6;
    if (y + 14 < r.bottom) {
        wchar_t brief[160];
        chokepoints_brief(brief, 160);
        if (brief[0]) {
            ui_subheading(dc, &(RECT){ r.left, y, r.right, y + 12 }, L"BRIEF");
            y += 14;
            SetTextColor(dc, CLR_ACC);
            TextOutW(dc, r.left, y, brief, lstrlenW(brief));
            y += 16;
        }
    }

    if (y + 14 < r.bottom && g_head_n > 0) {
        ui_subheading(dc, &(RECT){ r.left, y, r.right, y + 12 }, L"HEADLINES  RSS");
        y += 14;
        tick.left = r.left;
        tick.right = r.right;
        tick.top = y;
        tick.bottom = r.bottom;
        intel_paint_ticker(dc, &tick, "MARITIME", 6);
    }
}
