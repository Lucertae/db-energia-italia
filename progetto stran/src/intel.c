#include "intel.h"
#include "data.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static IntelRow g_rows[INTEL_HEAD_MAX];
static int g_row_n;
static IntelEvent g_evts[INTEL_EVT_MAX];
static int g_evt_n;
static int g_stats_feeds;
static int g_stats_heads;
static char g_built[28];

static int g_cat;
static int g_scroll;
static RECT g_sidebar_rc;
static FILETIME g_index_ft;
static int g_index_ft_set;

static BOOL index_file_ft(FILETIME *ft) {
    WIN32_FILE_ATTRIBUTE_DATA fa;
    if (!ft) return FALSE;
    if (!GetFileAttributesExW(L"cache\\intel\\desk_index.json", GetFileExInfoStandard, &fa))
        return FALSE;
    *ft = fa.ftLastWriteTime;
    return TRUE;
}

const char *intel_desk_built_at(void) {
    return g_built[0] ? g_built : "?";
}

static const struct {
    const char *id;
    const wchar_t *label;
} G_CATS[INTEL_CAT_N] = {
    { "ALL",     L"ALL" },
    { "ENERGY",  L"NRG" },
    { "GEO",     L"GEO" },
    { "DEFENSE", L"DEF" },
    { "FINANCE", L"FIN" },
    { "TECH",    L"TEC" },
    { "CLIMATE", L"CLI" },
    { "MARITIME",L"SEA" },
};

static int g_cat_counts[INTEL_CAT_N];

static const char *json_str(const char *obj, const char *key, char *out, int cap) {
    char pat[48];
    const char *p, *q;

    if (!out || cap < 2) return NULL;
    out[0] = 0;
    wsprintfA(pat, "\"%s\"", key);
    p = strstr(obj, pat);
    if (!p) return NULL;
    p = strchr(p + strlen(pat), '"');
    if (!p) return NULL;
    p++;
    q = strchr(p, '"');
    if (!q) return NULL;
    if ((int)(q - p) >= cap) return NULL;
    memcpy(out, p, (size_t)(q - p));
    out[q - p] = 0;
    return out;
}

static int row_matches_cat(const IntelRow *r, int cat) {
    if (cat <= 0) return 1;
    if (cat < 0 || cat >= INTEL_CAT_N) return 0;
    return lstrcmpiA(r->desk, G_CATS[cat].id) == 0;
}

void intel_desk_init(void) {
    g_row_n = 0;
    g_evt_n = 0;
    g_cat = 0;
    g_scroll = 0;
    g_stats_feeds = 0;
    g_stats_heads = 0;
    g_built[0] = 0;
    memset(g_cat_counts, 0, sizeof(g_cat_counts));
}

int intel_desk_reload(void) {
    wchar_t path[MAX_PATH];
    FILE *f;
    char *buf;
    long sz;
    const char *p, *arr;
    int i;

    intel_desk_init();
    wsprintfW(path, L"cache\\intel\\desk_index.json");
    f = _wfopen(path, L"rb");
    if (!f) return 0;

    fseek(f, 0, SEEK_END);
    sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (sz <= 0 || sz > 8 * 1024 * 1024) {
        fclose(f);
        return 0;
    }
    buf = (char *)malloc((size_t)sz + 1);
    if (!buf) {
        fclose(f);
        return 0;
    }
    fread(buf, 1, (size_t)sz, f);
    buf[sz] = 0;
    fclose(f);

    json_str(buf, "built_at", g_built, (int)sizeof(g_built));

    p = strstr(buf, "\"stats\"");
    if (p) {
        const char *feeds = strstr(p, "\"feeds\"");
        const char *heads = strstr(p, "\"headlines\"");
        if (feeds) g_stats_feeds = atoi(feeds + 9);
        if (heads) g_stats_heads = atoi(heads + 13);
    }

    arr = strstr(buf, "\"headlines\"");
    if (arr) {
        arr = strchr(arr, '[');
        if (arr) {
            p = arr;
            while (g_row_n < INTEL_HEAD_MAX && (p = strchr(p, '{')) != NULL) {
                IntelRow *r = &g_rows[g_row_n];
                const char *end = strchr(p, '}');
                char block[900];

                if (!end) break;
                if ((int)(end - p) >= (int)sizeof(block)) {
                    p = end + 1;
                    continue;
                }
                memcpy(block, p, (size_t)(end - p + 1));
                block[end - p + 1] = 0;
                memset(r, 0, sizeof(*r));
                json_str(block, "desk", r->desk, (int)sizeof(r->desk));
                json_str(block, "ts", r->ts, (int)sizeof(r->ts));
                json_str(block, "source", r->source, (int)sizeof(r->source));
                json_str(block, "name", r->name, (int)sizeof(r->name));
                json_str(block, "title", r->title, (int)sizeof(r->title));
                json_str(block, "url", r->url, (int)sizeof(r->url));
                if (r->title[0]) g_row_n++;
                p = end + 1;
            }
        }
    }

    for (i = 0; i < g_row_n; i++) {
        int c;
        g_cat_counts[0]++;
        for (c = 1; c < INTEL_CAT_N; c++)
            if (row_matches_cat(&g_rows[i], c))
                g_cat_counts[c]++;
    }

    arr = strstr(buf, "\"events\"");
    if (arr) {
        arr = strchr(arr, '[');
        if (arr) {
            p = arr;
            while (g_evt_n < INTEL_EVT_MAX && (p = strchr(p, '{')) != NULL) {
                IntelEvent *e = &g_evts[g_evt_n];
                const char *end = strchr(p, '}');
                char block[700];

                if (!end) break;
                if ((int)(end - p) >= (int)sizeof(block)) {
                    p = end + 1;
                    continue;
                }
                memcpy(block, p, (size_t)(end - p + 1));
                block[end - p + 1] = 0;
                memset(e, 0, sizeof(*e));
                json_str(block, "type", e->type, (int)sizeof(e->type));
                json_str(block, "ts", e->ts, (int)sizeof(e->ts));
                json_str(block, "title", e->title, (int)sizeof(e->title));
                json_str(block, "severity", e->severity, (int)sizeof(e->severity));
                json_str(block, "source", e->source, (int)sizeof(e->source));
                json_str(block, "url", e->url, (int)sizeof(e->url));
                if (e->title[0]) g_evt_n++;
                p = end + 1;
            }
        }
    }

    free(buf);
    if (g_row_n > 0 && index_file_ft(&g_index_ft)) g_index_ft_set = 1;
    return g_row_n;
}

int intel_desk_poll(void) {
    FILETIME ft;

    if (!index_file_ft(&ft)) return 0;
    if (!g_index_ft_set) {
        g_index_ft = ft;
        g_index_ft_set = 1;
        return 0;
    }
    if (ft.dwLowDateTime == g_index_ft.dwLowDateTime &&
        ft.dwHighDateTime == g_index_ft.dwHighDateTime)
        return 0;
    g_index_ft = ft;
    return intel_desk_reload() > 0 ? 1 : 0;
}

void intel_desk_set_category(int cat) {
    if (cat < 0 || cat >= INTEL_CAT_N) return;
    g_cat = cat;
    g_scroll = 0;
}

int intel_desk_category(void) { return g_cat; }

int intel_desk_scroll(void) { return g_scroll; }

void intel_desk_scroll_delta(int lines) {
    int vis = intel_desk_visible_count();
    int max_scroll = vis - 1;
    if (max_scroll < 0) max_scroll = 0;
    g_scroll += lines;
    if (g_scroll < 0) g_scroll = 0;
    if (g_scroll > max_scroll) g_scroll = max_scroll;
}

int intel_desk_visible_count(void) {
    int i, n = 0;
    for (i = 0; i < g_row_n; i++)
        if (row_matches_cat(&g_rows[i], g_cat)) n++;
    return n;
}

const wchar_t *intel_desk_cat_label(int cat) {
    if (cat < 0 || cat >= INTEL_CAT_N) return L"?";
    return G_CATS[cat].label;
}

int intel_desk_cat_count(int cat) {
    if (cat < 0 || cat >= INTEL_CAT_N) return 0;
    return g_cat_counts[cat];
}

static COLORREF evt_color(const char *type) {
    if (!type || !type[0]) return CLR_DIM;
    if (lstrcmpiA(type, "quake") == 0) return RGB(255, 140, 90);
    if (lstrcmpiA(type, "disaster") == 0) return RGB(255, 90, 90);
    if (lstrcmpiA(type, "weather") == 0) return RGB(120, 180, 255);
    if (lstrcmpiA(type, "market") == 0) return RGB(140, 220, 140);
    if (lstrcmpiA(type, "ais") == 0) return RGB(180, 200, 255);
    return CLR_DIM;
}

void intel_paint_ticker(HDC dc, const RECT *rc, const char *desk_filter, int max_rows) {
    RECT r = *rc;
    wchar_t line[260], namew[56], titlew[200];
    int i, y, shown = 0, lh = 11;

    if (!dc || !rc || max_rows <= 0) return;
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    y = r.top;
    for (i = 0; i < g_row_n && shown < max_rows && y + lh <= r.bottom; i++) {
        const IntelRow *row = &g_rows[i];
        if (desk_filter && desk_filter[0] && lstrcmpiA(row->desk, desk_filter) != 0)
            continue;
        MultiByteToWideChar(CP_UTF8, 0, row->name, -1, namew, 56);
        MultiByteToWideChar(CP_UTF8, 0, row->title, -1, titlew, 200);
        SetTextColor(dc, CLR_DIM);
        wsprintfW(line, L"%.10ls %.70s", namew, titlew);
        TextOutW(dc, r.left, y, line, lstrlenW(line));
        y += lh;
        shown++;
    }
}

void intel_paint_events(HDC dc, const RECT *rc, int max_rows) {
    int i, y, shown = 0, lh = 11;
    wchar_t line[220], titlew[180];

    if (!dc || !rc || max_rows <= 0) return;
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    y = rc->top;
    for (i = 0; i < g_evt_n && shown < max_rows && y + lh <= rc->bottom; i++) {
        const IntelEvent *e = &g_evts[i];
        if (lstrcmpiA(e->type, "meta") == 0) continue;
        MultiByteToWideChar(CP_UTF8, 0, e->title, -1, titlew, 180);
        SetTextColor(dc, evt_color(e->type));
        wsprintfW(line, L"[%hs] %.72ls", e->severity, titlew);
        TextOutW(dc, rc->left, y, line, lstrlenW(line));
        y += lh;
        shown++;
    }
}

static void paint_sidebar(HDC dc, const RECT *rc) {
    int i, y;
    int lh = 14;
    wchar_t line[48];

    g_sidebar_rc = *rc;
    y = rc->top;
    for (i = 0; i < INTEL_CAT_N && y + lh <= rc->bottom; i++) {
        BOOL sel = (i == g_cat);
        wsprintfW(line, L"%-7ls %4d", G_CATS[i].label, g_cat_counts[i]);
        SetTextColor(dc, sel ? CLR_ACC : CLR_DIM);
        SelectObject(dc, fSm);
        TextOutW(dc, rc->left + (sel ? 0 : 4), y, line, lstrlenW(line));
        y += lh;
    }
}

static void paint_events(HDC dc, const RECT *rc) {
    int i, y = rc->top, lh = 12;
    wchar_t line[220], titlew[180];

    SelectObject(dc, fSm);
    for (i = 0; i < g_evt_n && y + lh <= rc->bottom; i++) {
        const IntelEvent *e = &g_evts[i];
        if (lstrcmpiA(e->type, "meta") == 0) continue;
        MultiByteToWideChar(CP_UTF8, 0, e->title, -1, titlew, 180);
        SetTextColor(dc, evt_color(e->type));
        wsprintfW(line, L"[%hs] %.75ls", e->severity, titlew);
        TextOutW(dc, rc->left, y, line, lstrlenW(line));
        y += lh;
    }
}

static void paint_headlines(HDC dc, const RECT *rc) {
    int vis = intel_desk_visible_count();
    int y = rc->top, lh = 12, row_h, shown = 0;
    int max_rows = (rc->bottom - rc->top) / lh;
    wchar_t line[300], namew[56], titlew[220];

    if (max_rows < 1) return;
    SelectObject(dc, fSm);
    for (row_h = 0; row_h < g_row_n; row_h++) {
        const IntelRow *row;
        if (!row_matches_cat(&g_rows[row_h], g_cat)) continue;
        if (shown < g_scroll) {
            shown++;
            continue;
        }
        if (shown - g_scroll >= max_rows) break;
        row = &g_rows[row_h];
        MultiByteToWideChar(CP_UTF8, 0, row->name, -1, namew, 56);
        MultiByteToWideChar(CP_UTF8, 0, row->title, -1, titlew, 220);
        SetTextColor(dc, CLR_DIM);
        wsprintfW(line, L"%.8hs %.12ls %.95s", row->ts + 5, namew, titlew);
        TextOutW(dc, rc->left, y, line, lstrlenW(line));
        y += lh;
        shown++;
    }
    (void)vis;
}

void intel_paint_page(HDC dc, const RECT *rc) {
    RECT r = *rc, side, mid, evt, inner;
    int w;
    wchar_t hdr[120];

    if (r.bottom <= r.top + 40) return;
    w = r.right - r.left;
    side = r;
    side.right = r.left + w * 12 / 100;
    evt = r;
    evt.left = r.right - w * 28 / 100;
    mid = r;
    mid.left = side.right + 6;
    mid.right = evt.left - 6;

    wsprintfW(hdr, L"INTEL  agg.%hs  %d feeds  %d headlines  R=refresh  [ / ] cat",
              intel_desk_built_at(),
              g_stats_feeds ? g_stats_feeds : 642,
              g_stats_heads ? g_stats_heads : g_row_n);
    ui_subheading(dc, &r, hdr);

    side.top += 14;
    mid.top += 14;
    evt.top += 14;

    ui_frame(dc, &side, L"CATEGORY");
    inner = ui_panel_body(&side);
    paint_sidebar(dc, &inner);

    ui_frame(dc, &mid, L"HEADLINES");
    inner = ui_panel_body(&mid);
    paint_headlines(dc, &inner);

    ui_frame(dc, &evt, L"LIVE EVENTS");
    inner = ui_panel_body(&evt);
    paint_events(dc, &inner);
}

int intel_desk_cat_hit(POINT pt, const RECT *sidebar) {
    int i, y0 = sidebar->top, lh = 14;
    (void)g_sidebar_rc;
    if (pt.x < sidebar->left || pt.x > sidebar->right) return -1;
    for (i = 0; i < INTEL_CAT_N; i++) {
        int y = y0 + i * lh;
        if (pt.y >= y && pt.y < y + lh) return i;
    }
    return -1;
}

int intel_desk_key(int vk) {
    if (vk == VK_UP) {
        intel_desk_scroll_delta(-3);
        return 1;
    }
    if (vk == VK_DOWN) {
        intel_desk_scroll_delta(3);
        return 1;
    }
    if (vk == VK_PRIOR) {
        intel_desk_scroll_delta(-12);
        return 1;
    }
    if (vk == VK_NEXT) {
        intel_desk_scroll_delta(12);
        return 1;
    }
    if (vk == VK_OEM_4) {
        intel_desk_set_category((g_cat + INTEL_CAT_N - 1) % INTEL_CAT_N);
        return 1;
    }
    if (vk == VK_OEM_6) {
        intel_desk_set_category((g_cat + 1) % INTEL_CAT_N);
        return 1;
    }
    if (vk == 'R' || vk == 'r') {
        data_kick_intel();
        return 1;
    }
    return 0;
}

int intel_desk_wheel(int delta) {
    intel_desk_scroll_delta(delta > 0 ? -4 : 4);
    return 1;
}
