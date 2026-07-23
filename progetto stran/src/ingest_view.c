#include "ingest_view.h"
#include "keys_view.h"
#include "map_view.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <wchar.h>

#define ING_LINE      14
#define ING_BUF       (8 * 1024 * 1024)
#define ING_VIS_MAX   160
#define ING_BLOCK     2048
#define ING_GRP_MAX   2400
#define ING_AUTO_SEC  60
#define ING_COLS      2

typedef struct {
    char    id[48];
    char    section[8];
    char    status[20];
    char    tier[12];
    char    sector[16];
    char    layer[20];
    char    path[96];
    char    meta[200];
    char    origin[24];
    char    publisher[48];
    char    url[128];
    char    data_mode[12];
    char    map_kind[12];
    char    refresh_label[96];
    char    fonte[56];
    char    region[20]; /* EUROPE/ASIA/... or "-" if no geo tendina */
    int     age_h;
    int     max_age_h;
    int     refresh_sec;
    int     needs_map;
} IngestRow;

/* Default poll when manifest has null/missing refresh_sec (no on-demand left). */
static int default_refresh_for_section(const char *section) {
    if (!section || !section[0]) return 600;
    if (strcmp(section, "PIPE") == 0) return 60;
    if (strcmp(section, "API") == 0) return 300;
    if (strcmp(section, "RSS") == 0) return 900;
    if (strcmp(section, "SER") == 0) return 1800;
    if (strcmp(section, "REF") == 0) return 3600;
    return 600;
}

static int effective_refresh(const IngestRow *row) {
    if (row->refresh_sec > 0) return row->refresh_sec;
    return default_refresh_for_section(row->section);
}

static int wall_countdown(int refresh_sec) {
    DWORD now_s;
    if (refresh_sec <= 0) refresh_sec = 60;
    now_s = GetTickCount() / 1000u;
    return refresh_sec - (int)(now_s % (DWORD)refresh_sec);
}

typedef struct {
    char    name[56];
    char    key[96];    /* M: / R: / F: open-state keys */
    char    macro[16];
    char    region[20];
    int     kind;       /* 0=macro, 1=region, 2=fonte */
    int     parent;     /* -1 macro; macro idx for region; region|macro idx for fonte */
    int     first;
    int     count;
    int     child_n;
    int     open;
    int     refresh_sec;
    int     ok_n;
    int     warn_n;
    int     fail_n;
} IngestGroup;

/* traffic light: 1=ok, 2=warn (manca API/stale), 3=fail */
#define ING_HEALTH_OK   1
#define ING_HEALTH_WARN 2
#define ING_HEALTH_FAIL 3
#define CLR_ING_WARN    RGB(255, 180, 80)

/* flat paint slots: group header or row under open fonte */
typedef struct {
    int is_hdr;
    int gi;     /* group index */
    int ri;     /* row index in g_rows (if !is_hdr) */
} PaintSlot;

static IngestRow *g_rows = NULL;
static int g_n = 0;
static int *g_vis_rows = NULL; /* filtered row indices */
static int g_vis_n = 0;
static IngestGroup g_grp[ING_GRP_MAX];
static int g_grp_n = 0;
static PaintSlot g_slots[ING_GRP_MAX * 2];
static int g_slot_n = 0;
static RECT g_slot_rc[ING_VIS_MAX];
static int g_slot_map[ING_VIS_MAX]; /* slot index for visible paint line */
static int g_slot_vis = 0;
static int g_scroll = 0;
int g_ing_tab = 0;

static wchar_t g_ing_search[48];
static wchar_t g_hdr[360];
static char g_built[40];
static FILETIME g_manifest_ft;
static int g_manifest_ft_set;
static DWORD g_last_reload_tick;
static DWORD g_next_rebuild_tick;
static int g_rebuild_busy;
static int g_auto_sec = ING_AUTO_SEC;
static int g_countdown; /* seconds to next auto rebuild */

static const wchar_t *ING_TABS[ING_TAB_COUNT] = {
    L"KEYS", L"MAP", L"ALL", L"PIPE", L"API", L"REF", L"RSS", L"SER"
};
static const char *ING_TAB_SEC[ING_TAB_COUNT] = {
    "__KEYS__", "__MAP__", "", "PIPE", "API", "REF", "RSS", "SER"
};

static int is_keys_tab(void) {
    return g_ing_tab == 0;
}

static int is_map_tab(void) {
    return g_ing_tab == 1;
}

static void ing_wlower(wchar_t *s) {
    for (; *s; s++) {
        if (*s >= L'A' && *s <= L'Z') *s = (wchar_t)(*s - L'A' + L'a');
    }
}

static BOOL ing_wcontains(const wchar_t *hay, const wchar_t *needle) {
    wchar_t h[256], n[48];

    if (!needle || !needle[0]) return TRUE;
    lstrcpynW(h, hay, 256);
    lstrcpynW(n, needle, 48);
    ing_wlower(h);
    ing_wlower(n);
    return wcsstr(h, n) != NULL;
}

static BOOL row_matches_search(const IngestRow *row) {
    wchar_t buf[320];

    if (!g_ing_search[0]) return TRUE;
    wsprintfW(buf, L"%hs %hs %hs %hs %hs %hs %hs %hs %hs %hs %hs",
              row->id, row->section, row->status, row->tier, row->sector,
              row->layer, row->meta, row->origin, row->publisher,
              row->data_mode, row->fonte);
    if (ing_wcontains(buf, g_ing_search)) return TRUE;
    if (row->map_kind[0]) {
        wsprintfW(buf, L"%hs %hs", row->map_kind, row->refresh_label);
        if (ing_wcontains(buf, g_ing_search)) return TRUE;
    }
    if (row->url[0]) {
        wsprintfW(buf, L"%hs", row->url);
        if (ing_wcontains(buf, g_ing_search)) return TRUE;
    }
    if (row->path[0]) {
        wsprintfW(buf, L"%hs", row->path);
        if (ing_wcontains(buf, g_ing_search)) return TRUE;
    }
    return FALSE;
}

static const char *json_str_q(const char *obj, const char *key, char *out, int cap) {
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
    if (!q || (int)(q - p) >= cap) return NULL;
    memcpy(out, p, (size_t)(q - p));
    out[q - p] = 0;
    return out;
}

static int json_int(const char *obj, const char *key, int def) {
    char pat[48];
    const char *p;

    wsprintfA(pat, "\"%s\":", key);
    p = strstr(obj, pat);
    if (!p) return def;
    p += strlen(pat);
    while (*p == ' ') p++;
    if (strncmp(p, "null", 4) == 0) return -1;
    return atoi(p);
}

static int json_bool(const char *obj, const char *key, int def) {
    char pat[48];
    const char *p;

    wsprintfA(pat, "\"%s\":", key);
    p = strstr(obj, pat);
    if (!p) return def;
    p += strlen(pat);
    while (*p == ' ') p++;
    if (strncmp(p, "true", 4) == 0) return 1;
    if (strncmp(p, "false", 5) == 0) return 0;
    return def;
}

static void row_clear(IngestRow *r) {
    memset(r, 0, sizeof(*r));
    r->age_h = -1;
    r->max_age_h = -1;
    r->refresh_sec = -1;
    r->needs_map = -1;
}

static void fill_fonte(IngestRow *r) {
    if (r->publisher[0]) {
        lstrcpynA(r->fonte, r->publisher, (int)sizeof(r->fonte));
    } else if (r->origin[0]) {
        lstrcpynA(r->fonte, r->origin, (int)sizeof(r->fonte));
    } else if (r->meta[0]) {
        lstrcpynA(r->fonte, r->meta, (int)sizeof(r->fonte));
    } else {
        lstrcpynA(r->fonte, r->id[0] ? r->id : "ALTRO", (int)sizeof(r->fonte));
    }
    if (!r->sector[0])
        lstrcpynA(r->sector, "ALTRO", (int)sizeof(r->sector));
}

static int sector_uses_region(const char *sec) {
    if (!sec || !sec[0]) return 0;
    if (_stricmp(sec, "GEO") == 0) return 1;
    if (_stricmp(sec, "DEFENSE") == 0) return 1;
    if (_stricmp(sec, "MARITIME") == 0) return 1;
    if (_stricmp(sec, "CONFLICT") == 0) return 1;
    if (_stricmp(sec, "HUMANITARIAN") == 0) return 1;
    if (_stricmp(sec, "CLIMATE") == 0) return 1;
    if (_stricmp(sec, "ENERGY") == 0) return 1;
    return 0;
}

static void ing_alower(char *s) {
    for (; *s; s++) {
        if (*s >= 'A' && *s <= 'Z') *s = (char)(*s - 'A' + 'a');
    }
}

static void fill_region(IngestRow *r) {
    char blob[320];
    char low[320];

    if (!sector_uses_region(r->sector)) {
        lstrcpynA(r->region, "-", (int)sizeof(r->region));
        return;
    }
    wsprintfA(blob, "%s %s %s %s %s %s",
              r->layer, r->meta, r->publisher, r->origin, r->id, r->fonte);
    lstrcpynA(low, blob, (int)sizeof(low));
    ing_alower(low);

    if (strstr(low, "africa") || strstr(low, "nigeria") || strstr(low, "kenya") ||
        strstr(low, "sahel") || strstr(low, "maghreb"))
        lstrcpynA(r->region, "AFRICA", (int)sizeof(r->region));
    else if (strstr(low, "asia") || strstr(low, "china") || strstr(low, "japan") ||
             strstr(low, "india") || strstr(low, "korea") || strstr(low, "asean") ||
             strstr(low, "taiwan") || strstr(low, "pacific"))
        lstrcpynA(r->region, "ASIA", (int)sizeof(r->region));
    else if (strstr(low, "middle east") || strstr(low, "mena") || strstr(low, "gulf") ||
             strstr(low, "iran") || strstr(low, "iraq") || strstr(low, "israel") ||
             strstr(low, "levant") || strstr(low, "hormuz"))
        lstrcpynA(r->region, "MENA", (int)sizeof(r->region));
    else if (strstr(low, "europe") || strstr(low, "eu ") || strstr(low, "stran-eu") ||
             strstr(low, "nato") || strstr(low, "euronews") || strstr(low, "france") ||
             strstr(low, "italia") || strstr(low, "mediaset") || strstr(low, "ansa") ||
             strstr(low, "ukraine") || strstr(low, "kyiv") || strstr(low, "euobserv") ||
             strstr(low, "ecb") || strcmp(r->layer, "eu") == 0 ||
             strcmp(r->layer, "europe") == 0)
        lstrcpynA(r->region, "EUROPE", (int)sizeof(r->region));
    else if (strstr(low, "america") || strstr(low, "latam") || strstr(low, "brazil") ||
             strstr(low, "mexico") || strstr(low, "canada") || strstr(low, "us ") ||
             strstr(low, "united states") || strstr(low, "faa") ||
             strcmp(r->layer, "us") == 0 || strcmp(r->layer, "latam") == 0)
        lstrcpynA(r->region, "AMERICAS", (int)sizeof(r->region));
    else if (strstr(low, "maritime") || strstr(low, "chokepoint") || strstr(low, "ais") ||
             strstr(low, "portwatch") || strstr(low, "shipping"))
        lstrcpynA(r->region, "MARITIME", (int)sizeof(r->region));
    else
        lstrcpynA(r->region, "GLOBAL", (int)sizeof(r->region));
}

static void parse_entry_block(const char *block) {
    IngestRow *r;

    if (!g_rows || g_n < 0) return;
    if (g_n >= 100000) return;
    r = &g_rows[g_n];
    row_clear(r);
    json_str_q(block, "id", r->id, 48);
    json_str_q(block, "section", r->section, 8);
    json_str_q(block, "status", r->status, 20);
    json_str_q(block, "tier", r->tier, 12);
    json_str_q(block, "sector", r->sector, 16);
    json_str_q(block, "layer", r->layer, 20);
    json_str_q(block, "path", r->path, 96);
    json_str_q(block, "meta", r->meta, 200);
    json_str_q(block, "origin", r->origin, 24);
    json_str_q(block, "publisher", r->publisher, 48);
    if (!r->publisher[0])
        json_str_q(block, "platform", r->publisher, 48);
    json_str_q(block, "url", r->url, 128);
    json_str_q(block, "data_mode", r->data_mode, 12);
    json_str_q(block, "map_kind", r->map_kind, 12);
    json_str_q(block, "refresh_label", r->refresh_label, 96);
    r->age_h = json_int(block, "age_h", -1);
    r->max_age_h = json_int(block, "max_age_h", -1);
    r->refresh_sec = json_int(block, "refresh_sec", -1);
    if (strstr(block, "\"refresh_sec\": null") != NULL)
        r->refresh_sec = -1;
    r->needs_map = json_bool(block, "needs_map", -1);
    fill_fonte(r);
    fill_region(r);
    if (r->refresh_sec <= 0)
        r->refresh_sec = default_refresh_for_section(r->section);
    if (r->id[0]) g_n++;
}

static int cmp_macro_region_fonte(const void *a, const void *b) {
    int ia = *(const int *)a;
    int ib = *(const int *)b;
    int c = _stricmp(g_rows[ia].sector, g_rows[ib].sector);
    if (c) return c;
    c = _stricmp(g_rows[ia].region, g_rows[ib].region);
    if (c) return c;
    return _stricmp(g_rows[ia].fonte, g_rows[ib].fonte);
}

static void emit_fonte_slots(int fi) {
    int k;
    IngestGroup *fg = &g_grp[fi];
    if (g_slot_n >= (int)(sizeof(g_slots) / sizeof(g_slots[0]))) return;
    g_slots[g_slot_n].is_hdr = 1;
    g_slots[g_slot_n].gi = fi;
    g_slots[g_slot_n].ri = -1;
    g_slot_n++;
    if (!fg->open) return;
    for (k = 0; k < fg->count; k++) {
        int ri;
        if (g_slot_n >= (int)(sizeof(g_slots) / sizeof(g_slots[0]))) break;
        ri = g_vis_rows[fg->first + k];
        g_slots[g_slot_n].is_hdr = 0;
        g_slots[g_slot_n].gi = fi;
        g_slots[g_slot_n].ri = ri;
        g_slot_n++;
    }
}

static void rebuild_slots(void) {
    int g, i;

    g_slot_n = 0;
    for (g = 0; g < g_grp_n; g++) {
        IngestGroup *grp = &g_grp[g];
        if (grp->kind != 0) continue;
        if (g_slot_n >= (int)(sizeof(g_slots) / sizeof(g_slots[0]))) break;
        g_slots[g_slot_n].is_hdr = 1;
        g_slots[g_slot_n].gi = g;
        g_slots[g_slot_n].ri = -1;
        g_slot_n++;
        if (!grp->open) continue;
        for (i = g + 1; i < g_grp_n; i++) {
            IngestGroup *ch = &g_grp[i];
            if (ch->kind == 0) break;
            if (ch->kind == 1 && ch->parent == g) {
                /* region under macro */
                if (g_slot_n >= (int)(sizeof(g_slots) / sizeof(g_slots[0]))) break;
                g_slots[g_slot_n].is_hdr = 1;
                g_slots[g_slot_n].gi = i;
                g_slots[g_slot_n].ri = -1;
                g_slot_n++;
                if (!ch->open) continue;
                {
                    int j;
                    for (j = i + 1; j < g_grp_n; j++) {
                        IngestGroup *fg = &g_grp[j];
                        if (fg->kind == 0 || fg->kind == 1) break;
                        if (fg->parent != i) continue;
                        emit_fonte_slots(j);
                    }
                }
            } else if (ch->kind == 2 && ch->parent == g) {
                /* fonte direct under macro (no region) */
                emit_fonte_slots(i);
            }
        }
    }
    if (g_scroll > g_slot_n - 1) g_scroll = g_slot_n > 0 ? g_slot_n - 1 : 0;
    if (g_scroll < 0) g_scroll = 0;
}

/* Keep open state across rebuilds via key map */
static char g_open_names[ING_GRP_MAX][96];
static int g_open_flags[ING_GRP_MAX];
static int g_open_map_n;
static int g_macro_n;
static int g_region_n;

static void save_open_map(void) {
    int g;
    g_open_map_n = 0;
    for (g = 0; g < g_grp_n && g_open_map_n < ING_GRP_MAX; g++) {
        if (!g_grp[g].open) continue;
        lstrcpynA(g_open_names[g_open_map_n], g_grp[g].key, 96);
        g_open_flags[g_open_map_n] = 1;
        g_open_map_n++;
    }
}

static int was_open(const char *key) {
    int i;
    for (i = 0; i < g_open_map_n; i++) {
        if (_stricmp(g_open_names[i], key) == 0)
            return g_open_flags[i];
    }
    return 0;
}

static int health_level(const char *st) {
    if (!st || !st[0]) return 0;
    if (strcmp(st, "ok") == 0 || strcmp(st, "integrated") == 0 ||
        strcmp(st, "active") == 0)
        return ING_HEALTH_OK;
    if (strcmp(st, "fail") == 0 || strcmp(st, "missing") == 0)
        return ING_HEALTH_FAIL;
    if (strcmp(st, "optional_missing") == 0 || strcmp(st, "planned") == 0 ||
        strcmp(st, "available") == 0 || strcmp(st, "stale") == 0 ||
        strcmp(st, "partial") == 0 || strcmp(st, "blocked") == 0)
        return ING_HEALTH_WARN;
    if (strstr(st, "missing") != NULL)
        return ING_HEALTH_WARN; /* manca API / endpoint */
    if (strcmp(st, "optional") == 0 || strcmp(st, "disabled") == 0)
        return 0;
    return 0;
}

static COLORREF health_color(int level) {
    if (level == ING_HEALTH_OK) return CLR_UP;
    if (level == ING_HEALTH_WARN) return CLR_ING_WARN;
    if (level == ING_HEALTH_FAIL) return CLR_DN;
    return CLR_OFF;
}

static COLORREF group_health_color(const IngestGroup *grp) {
    if (grp->fail_n > 0) return CLR_DN;
    if (grp->warn_n > 0) return CLR_ING_WARN;
    if (grp->ok_n > 0) return CLR_UP;
    return CLR_OFF;
}

static void paint_health_dot(HDC dc, int x, int y, COLORREF c) {
    HBRUSH br = CreateSolidBrush(c);
    HBRUSH old = (HBRUSH)SelectObject(dc, br);
    Ellipse(dc, x, y, x + 7, y + 7);
    SelectObject(dc, old);
    DeleteObject(br);
}

static void accumulate_status(IngestGroup *grp, const IngestRow *row) {
    int er = effective_refresh(row);
    int lvl = health_level(row->status);
    if (grp->refresh_sec < 0 || er < grp->refresh_sec)
        grp->refresh_sec = er;
    if (lvl == ING_HEALTH_OK) grp->ok_n++;
    else if (lvl == ING_HEALTH_WARN) grp->warn_n++;
    else if (lvl == ING_HEALTH_FAIL) grp->fail_n++;
}

static void rebuild_visible_ex(void) {
    int i;
    const char *filt = ING_TAB_SEC[g_ing_tab];
    char prev_macro[16];
    char prev_region[20];
    char prev_fonte[56];
    int macro_gi = -1;
    int region_gi = -1;
    int fonte_gi = -1;

    if (is_keys_tab() || is_map_tab())
        return;

    save_open_map();
    g_vis_n = 0;
    g_grp_n = 0;
    g_macro_n = 0;
    g_region_n = 0;
    if (!g_vis_rows || !g_rows) return;

    for (i = 0; i < g_n && g_vis_n < 100000; i++) {
        if (filt[0] && strcmp(g_rows[i].section, filt) != 0)
            continue;
        if (!row_matches_search(&g_rows[i]))
            continue;
        g_vis_rows[g_vis_n++] = i;
    }
    qsort(g_vis_rows, (size_t)g_vis_n, sizeof(int), cmp_macro_region_fonte);

    prev_macro[0] = 0;
    prev_region[0] = 0;
    prev_fonte[0] = 0;
    for (i = 0; i < g_vis_n; i++) {
        const IngestRow *row = &g_rows[g_vis_rows[i]];
        IngestGroup *grp;
        char mkey[96], rkey[96], fkey[96];
        int use_reg = sector_uses_region(row->sector);
        int fonte_parent;

        if (_stricmp(row->sector, prev_macro) != 0) {
            if (g_grp_n >= ING_GRP_MAX) break;
            grp = &g_grp[g_grp_n];
            memset(grp, 0, sizeof(*grp));
            lstrcpynA(grp->name, row->sector, (int)sizeof(grp->name));
            lstrcpynA(grp->macro, row->sector, (int)sizeof(grp->macro));
            wsprintfA(mkey, "M:%s", row->sector);
            lstrcpynA(grp->key, mkey, (int)sizeof(grp->key));
            grp->kind = 0;
            grp->parent = -1;
            grp->first = i;
            grp->count = 0;
            grp->child_n = 0;
            grp->refresh_sec = -1;
            grp->open = g_ing_search[0] ? 1 : was_open(grp->key);
            macro_gi = g_grp_n;
            g_grp_n++;
            g_macro_n++;
            lstrcpynA(prev_macro, row->sector, (int)sizeof(prev_macro));
            prev_region[0] = 0;
            prev_fonte[0] = 0;
            region_gi = -1;
            fonte_gi = -1;
        }

        if (use_reg) {
            if (_stricmp(row->region, prev_region) != 0) {
                if (g_grp_n >= ING_GRP_MAX) break;
                grp = &g_grp[g_grp_n];
                memset(grp, 0, sizeof(*grp));
                lstrcpynA(grp->name, row->region, (int)sizeof(grp->name));
                lstrcpynA(grp->macro, row->sector, (int)sizeof(grp->macro));
                lstrcpynA(grp->region, row->region, (int)sizeof(grp->region));
                wsprintfA(rkey, "R:%s|%s", row->sector, row->region);
                lstrcpynA(grp->key, rkey, (int)sizeof(grp->key));
                grp->kind = 1;
                grp->parent = macro_gi;
                grp->first = i;
                grp->count = 0;
                grp->child_n = 0;
                grp->refresh_sec = -1;
                grp->open = g_ing_search[0] ? 1 : was_open(grp->key);
                region_gi = g_grp_n;
                g_grp_n++;
                g_region_n++;
                if (macro_gi >= 0)
                    g_grp[macro_gi].child_n++;
                lstrcpynA(prev_region, row->region, (int)sizeof(prev_region));
                prev_fonte[0] = 0;
                fonte_gi = -1;
            }
            fonte_parent = region_gi;
        } else {
            region_gi = -1;
            fonte_parent = macro_gi;
        }

        if (_stricmp(row->fonte, prev_fonte) != 0) {
            if (g_grp_n >= ING_GRP_MAX) break;
            grp = &g_grp[g_grp_n];
            memset(grp, 0, sizeof(*grp));
            lstrcpynA(grp->name, row->fonte, (int)sizeof(grp->name));
            lstrcpynA(grp->macro, row->sector, (int)sizeof(grp->macro));
            lstrcpynA(grp->region, row->region, (int)sizeof(grp->region));
            if (use_reg)
                wsprintfA(fkey, "F:%s|%s|%s", row->sector, row->region, row->fonte);
            else
                wsprintfA(fkey, "F:%s|%s", row->sector, row->fonte);
            lstrcpynA(grp->key, fkey, (int)sizeof(grp->key));
            grp->kind = 2;
            grp->parent = fonte_parent;
            grp->first = i;
            grp->count = 0;
            grp->refresh_sec = -1;
            grp->open = g_ing_search[0] ? 1 : was_open(grp->key);
            fonte_gi = g_grp_n;
            g_grp_n++;
            if (fonte_parent >= 0)
                g_grp[fonte_parent].child_n++;
            if (!use_reg && macro_gi >= 0)
                g_grp[macro_gi].child_n++;
            lstrcpynA(prev_fonte, row->fonte, (int)sizeof(prev_fonte));
        }

        if (fonte_gi < 0 || macro_gi < 0) continue;
        g_grp[fonte_gi].count++;
        g_grp[macro_gi].count++;
        if (use_reg && region_gi >= 0)
            g_grp[region_gi].count++;
        accumulate_status(&g_grp[fonte_gi], row);
        accumulate_status(&g_grp[macro_gi], row);
        if (use_reg && region_gi >= 0)
            accumulate_status(&g_grp[region_gi], row);
    }
    rebuild_slots();
}

static const char *row_detail(const IngestRow *row) {
    if (row->url[0]) return row->url;
    if (row->path[0]) return row->path;
    if (row->meta[0]) return row->meta;
    return row->id;
}

static void schedule_next_rebuild(void) {
    g_last_reload_tick = GetTickCount();
    g_next_rebuild_tick = g_last_reload_tick + (DWORD)(g_auto_sec * 1000);
    g_countdown = g_auto_sec;
}

static BOOL load_manifest(void) {
    static char *buf = NULL;
    FILE *f;
    long sz;
    const char *p, *obj, *entries;
    int total, pipe, api, ref, rss, ser, ok, fail;

    g_n = 0;
    if (!buf) {
        buf = (char *)malloc(ING_BUF);
        if (!buf) return FALSE;
    }
    if (!g_rows) {
        g_rows = (IngestRow *)malloc(sizeof(IngestRow) * 4096);
        g_vis_rows = (int *)malloc(sizeof(int) * 4096);
        if (!g_rows || !g_vis_rows) return FALSE;
    }
    f = fopen("cache\\ingest\\manifest.json", "rb");
    if (!f) {
        wsprintfW(g_hdr, L"manifest mancante — R per rebuild (build_ingest_manifest.py)");
        schedule_next_rebuild();
        return FALSE;
    }
    fseek(f, 0, SEEK_END);
    sz = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (sz <= 0 || sz >= ING_BUF - 1) {
        fclose(f);
        wsprintfW(g_hdr, L"manifest troppo grande (%ld byte)", sz);
        return FALSE;
    }
    if (fread(buf, 1, (size_t)sz, f) != (size_t)sz) {
        fclose(f);
        wsprintfW(g_hdr, L"manifest lettura incompleta (%ld byte)", sz);
        return FALSE;
    }
    buf[sz] = 0;
    fclose(f);

    json_str_q(buf, "built_at", g_built, 40);
    p = strstr(buf, "\"summary\"");
    total = p ? json_int(p, "total", 0) : 0;
    pipe = p ? json_int(p, "pipe", 0) : 0;
    api = p ? json_int(p, "api", 0) : 0;
    ref = p ? json_int(p, "ref", 0) : 0;
    rss = p ? json_int(p, "rss", 0) : 0;
    ser = p ? json_int(p, "ser", 0) : 0;
    ok = p ? json_int(p, "ok", 0) : 0;
    fail = p ? json_int(p, "fail", 0) : 0;

    if (total > 4096) {
        free(g_rows);
        free(g_vis_rows);
        g_rows = (IngestRow *)malloc(sizeof(IngestRow) * ((size_t)total + 64));
        g_vis_rows = (int *)malloc(sizeof(int) * ((size_t)total + 64));
        if (!g_rows || !g_vis_rows) return FALSE;
    }

    entries = strstr(buf, "\"entries\"");
    if (!entries) {
        wsprintfW(g_hdr, L"manifest senza array entries");
        return FALSE;
    }
    obj = strchr(entries, '[');
    if (!obj) return FALSE;
    while ((obj = strstr(obj, "\"id\"")) != NULL && g_n < total + 100) {
        const char *start, *end;
        char block[ING_BLOCK];
        int len;

        start = obj;
        while (start > buf && *start != '{') start--;
        end = strchr(obj, '}');
        if (!end) break;
        len = (int)(end - start + 1);
        if (len >= (int)sizeof(block)) len = (int)sizeof(block) - 1;
        memcpy(block, start, (size_t)len);
        block[len] = 0;
        parse_entry_block(block);
        obj = end + 1;
    }

    wsprintfW(g_hdr,
              L"INGEST %hs  %d voci  ok=%d fail=%d  PIPE=%d API=%d REF=%d RSS=%d SER=%d",
              g_built[0] ? g_built : "?", g_n, ok, fail, pipe, api, ref, rss, ser);
    {
        WIN32_FILE_ATTRIBUTE_DATA fa;
        if (GetFileAttributesExW(L"cache\\ingest\\manifest.json", GetFileExInfoStandard, &fa)) {
            g_manifest_ft = fa.ftLastWriteTime;
            g_manifest_ft_set = 1;
        }
    }
    rebuild_visible_ex();
    /* patch macro/fonte counts into header */
    wsprintfW(g_hdr,
              L"INGEST %hs  %d voci  %d macro · %d reg · %d fonti  ok=%d fail=%d  PIPE=%d API=%d REF=%d RSS=%d SER=%d",
              g_built[0] ? g_built : "?", g_n, g_macro_n, g_region_n,
              g_grp_n - g_macro_n - g_region_n,
              ok, fail, pipe, api, ref, rss, ser);
    schedule_next_rebuild();
    g_rebuild_busy = 0;
    return TRUE;
}

void ingest_view_force_rebuild(void) {
    if (g_rebuild_busy) return;
    g_rebuild_busy = 1;
    g_countdown = 0;
    if (desk_spawn_python(L"scripts\\desk_harvest\\build_ingest_manifest.py")) {
        /* poll will reload when mtime changes */
    } else {
        g_rebuild_busy = 0;
        schedule_next_rebuild();
    }
}

void ingest_view_init(void) {
    g_scroll = 0;
    /* Default ALL so UI shows WM panels immediately (not KEYS) */
    g_ing_tab = 2;
    g_ing_search[0] = 0;
    g_open_map_n = 0;
    g_rebuild_busy = 0;
    g_auto_sec = ING_AUTO_SEC;
    keys_view_init();
    map_view_init();
    ingest_view_reload();
}

void ingest_view_reload(void) {
    load_manifest();
}

void ingest_view_tab_next(int dir) {
    g_ing_tab += dir;
    if (g_ing_tab < 0) g_ing_tab = ING_TAB_COUNT - 1;
    if (g_ing_tab >= ING_TAB_COUNT) g_ing_tab = 0;
    g_scroll = 0;
    if (!is_keys_tab() && !is_map_tab())
        rebuild_visible_ex();
    else if (is_keys_tab())
        keys_view_clear_edit();
}

void ingest_view_char(wchar_t ch) {
    int n;

    if (is_keys_tab()) {
        keys_view_char(ch);
        return;
    }
    if (is_map_tab())
        return;
    n = lstrlenW(g_ing_search);
    if (ch == 8 || ch == 127) {
        if (n > 0) g_ing_search[n - 1] = 0;
    } else if (ch >= 32 && n < (int)(sizeof(g_ing_search) / sizeof(g_ing_search[0])) - 1) {
        g_ing_search[n] = ch;
        g_ing_search[n + 1] = 0;
    }
    g_scroll = 0;
    rebuild_visible_ex();
}

void ingest_view_clear_search(void) {
    if (is_keys_tab()) {
        keys_view_clear_edit();
        return;
    }
    if (is_map_tab())
        return;
    g_ing_search[0] = 0;
    g_scroll = 0;
    rebuild_visible_ex();
}

static COLORREF status_color(const char *st) {
    int lvl = health_level(st);
    if (lvl) return health_color(lvl);
    if (!st || !st[0]) return CLR_DIM;
    return CLR_DIM;
}

static RECT g_tab_rc[ING_TAB_COUNT];

static void paint_tabs(HDC dc, RECT *r) {
    int i, x, tw;

    tw = (r->right - r->left) / ING_TAB_COUNT - 2;
    if (tw < 36) tw = 36;
    x = r->left;
    for (i = 0; i < ING_TAB_COUNT; i++) {
        RECT cell = { x, r->top, x + tw, r->top + 16 };
        g_tab_rc[i] = cell;
        if (i == g_ing_tab) {
            FillRect(dc, &cell, bWhite);
            SetTextColor(dc, CLR_BG);
        } else {
            FrameRect(dc, &cell, GetStockObject(WHITE_BRUSH));
            SetTextColor(dc, CLR_DIM);
        }
        SetBkMode(dc, TRANSPARENT);
        SelectObject(dc, fSm);
        DrawTextW(dc, (wchar_t *)ING_TABS[i], -1, &cell,
                  DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX);
        x += tw + 2;
    }
    r->top += 18;
}

static int hit_ing_tab(POINT pt) {
    int i;
    for (i = 0; i < ING_TAB_COUNT; i++) {
        if (PtInRect(&g_tab_rc[i], pt))
            return i;
    }
    return -1;
}

static void paint_timer_bar(HDC dc, RECT *r) {
    wchar_t line[160];
    RECT bar = *r;
    int mm, ss;
    COLORREF col;

    bar.bottom = bar.top + 16;
    mm = g_countdown / 60;
    ss = g_countdown % 60;
    if (g_rebuild_busy) {
        col = CLR_ACC;
        lstrcpyW(line, L"LIVE  REBUILD in corso...  (attendi aggiornamento manifest)");
    } else {
        col = g_countdown <= 5 ? CLR_DN : CLR_UP;
        wsprintfW(line,
                  L"LIVE  next update %02d:%02d  auto=%ds  last=%hs  [F5]=rebuild ora  [+/-]=auto",
                  mm, ss, g_auto_sec, g_built[0] ? g_built : "?");
    }
    SetBkMode(dc, TRANSPARENT);
    SetTextColor(dc, col);
    SelectObject(dc, fSm);
    DrawTextW(dc, line, -1, &bar, DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX | DT_END_ELLIPSIS);
    r->top = bar.bottom + 2;
}

static void paint_search(HDC dc, RECT *r) {
    wchar_t line[80];
    RECT srch = *r;

    srch.bottom = srch.top + 16;
    wsprintfW(line, L"FILTER: %s_", g_ing_search);
    SetBkMode(dc, TRANSPARENT);
    SetTextColor(dc, CLR_ACC);
    SelectObject(dc, fSm);
    DrawTextW(dc, line, -1, &srch, DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX);
    r->top = srch.bottom + 4;
}

static void fmt_refresh(wchar_t *out, int cap, const IngestRow *row) {
    int sec = effective_refresh(row);
    int left = wall_countdown(sec);
    (void)cap;
    if (row->refresh_label[0])
        wsprintfW(out, L"%02d:%02d %hs", left / 60, left % 60, row->refresh_label);
    else
        wsprintfW(out, L"%02d:%02d / %ds", left / 60, left % 60, sec);
}

static void fmt_group_timer(wchar_t *out, int cap, const IngestGroup *grp) {
    int sec = grp->refresh_sec > 0 ? grp->refresh_sec : 600;
    int left = wall_countdown(sec);
    (void)cap;
    wsprintfW(out, L"%02d:%02d / %ds", left / 60, left % 60, sec);
}

static void paint_list(HDC dc, RECT *r) {
    int i, col, y0, vis_row, vis_total, start, gap, mid, col_w;
    wchar_t line[360], cnt[96];
    RECT col_rc[ING_COLS];

    gap = 8;
    mid = (r->left + r->right) / 2;
    col_w = (r->right - r->left - gap) / ING_COLS;
    col_rc[0].left = r->left;
    col_rc[0].right = r->left + col_w;
    col_rc[0].top = r->top;
    col_rc[0].bottom = r->bottom;
    col_rc[1].left = mid + gap / 2;
    col_rc[1].right = r->right;
    col_rc[1].top = r->top;
    col_rc[1].bottom = r->bottom;

    vis_row = (r->bottom - r->top - 30) / ING_LINE;
    if (vis_row < 1) vis_row = 1;
    vis_total = vis_row * ING_COLS;
    if (vis_total > ING_VIS_MAX) {
        vis_row = ING_VIS_MAX / ING_COLS;
        vis_total = vis_row * ING_COLS;
    }
    if (g_scroll < 0) g_scroll = 0;
    if (g_scroll > g_slot_n - vis_total && g_slot_n > vis_total)
        g_scroll = g_slot_n - vis_total;
    if (g_scroll < 0) g_scroll = 0;

    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    wsprintfW(cnt, L"%d macro · %d regioni · %d fonti · %d voci  %s  | 2 col",
              g_macro_n, g_region_n, g_grp_n - g_macro_n - g_region_n, g_vis_n,
              ING_TABS[g_ing_tab]);
    SetTextColor(dc, CLR_OFF);
    TextOutW(dc, r->left, r->top, cnt, lstrlenW(cnt));

    for (col = 0; col < ING_COLS; col++) {
        SetTextColor(dc, CLR_OFF);
        TextOutW(dc, col_rc[col].left, r->top + 14,
                 L"  · MACRO / REGIONE / FONTE          N OK W F  TIMER",
                 52);
        ui_hline(dc, col_rc[col].left, r->top + 14 + ING_LINE - 2,
                 col_rc[col].right, CLR_GRID);
    }

    g_slot_vis = 0;
    start = g_scroll;
    y0 = r->top + 14 + ING_LINE;

    for (col = 0; col < ING_COLS; col++) {
        int y = y0;
        for (i = 0; i < vis_row; i++) {
            int si = start + col * vis_row + i;
            PaintSlot *sl;
            RECT row_rc;
            wchar_t timer[40];

            if (si >= g_slot_n) break;
            sl = &g_slots[si];
            row_rc.left = col_rc[col].left;
            row_rc.right = col_rc[col].right;
            row_rc.top = y;
            row_rc.bottom = y + ING_LINE;
            if (g_slot_vis < ING_VIS_MAX) {
                g_slot_rc[g_slot_vis] = row_rc;
                g_slot_map[g_slot_vis] = si;
                g_slot_vis++;
            }

            if (sl->is_hdr) {
                IngestGroup *grp = &g_grp[sl->gi];
                RECT text_rc = row_rc;
                int dot_x;
                fmt_group_timer(timer, 40, grp);
                if (grp->kind == 0) {
                    SetTextColor(dc, CLR_ACC);
                    wsprintfW(line, L"%s %-18hs %2dC %3d %2d %2d %2d %-8s",
                              grp->open ? L"[-]" : L"[+]",
                              grp->name, grp->child_n, grp->count,
                              grp->ok_n, grp->warn_n, grp->fail_n, timer);
                    dot_x = row_rc.left;
                } else if (grp->kind == 1) {
                    SetTextColor(dc, CLR_ING_WARN);
                    wsprintfW(line, L" %s %-18hs %2dF %3d %2d %2d %2d %-8s",
                              grp->open ? L"[-]" : L"[+]",
                              grp->name, grp->child_n, grp->count,
                              grp->ok_n, grp->warn_n, grp->fail_n, timer);
                    dot_x = row_rc.left + 2;
                } else {
                    SetTextColor(dc, CLR_TXT);
                    wsprintfW(line, L"  %s %-18hs %3d %2d %2d %2d %-8s",
                              grp->open ? L"[-]" : L"[+]",
                              grp->name, grp->count,
                              grp->ok_n, grp->warn_n, grp->fail_n, timer);
                    dot_x = row_rc.left + 4;
                }
                FillRect(dc, &row_rc, bBand);
                paint_health_dot(dc, dot_x, row_rc.top + 3, group_health_color(grp));
                text_rc.left = row_rc.left + 10;
                DrawTextW(dc, line, -1, &text_rc,
                          DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS | DT_NOPREFIX);
            } else {
                const IngestRow *row = &g_rows[sl->ri];
                const char *detail = row_detail(row);
                RECT text_rc = row_rc;
                fmt_refresh(timer, 40, row);
                SetTextColor(dc, status_color(row->status));
                wsprintfW(line, L"   %-8hs %-16hs %-4hs %hs",
                          row->status, row->id, row->section, detail);
                paint_health_dot(dc, row_rc.left + 6, row_rc.top + 3,
                                 health_color(health_level(row->status)));
                text_rc.left = row_rc.left + 16;
                DrawTextW(dc, line, -1, &text_rc,
                          DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS | DT_NOPREFIX);
            }
            y += ING_LINE;
        }
    }

    {
        HPEN pen = CreatePen(PS_SOLID, 1, CLR_GRID);
        HPEN old = (HPEN)SelectObject(dc, pen);
        MoveToEx(dc, mid, y0 - 2, NULL);
        LineTo(dc, mid, r->bottom);
        SelectObject(dc, old);
        DeleteObject(pen);
    }
}

void ingest_view_paint(HDC dc, const RECT *rc) {
    RECT r = *rc, body, foot;
    wchar_t note[180];

    if (r.bottom <= r.top + 60) return;
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    SetTextColor(dc, CLR_DIM);
    TextOutW(dc, r.left, r.top, g_hdr, lstrlenW(g_hdr));
    r.top += 16;
    body = r;
    body.bottom = r.bottom - 16;
    paint_tabs(dc, &body);
    if (is_keys_tab()) {
        keys_view_paint(dc, &body);
        foot = r;
        foot.top = r.bottom - 14;
        SetTextColor(dc, CLR_OFF);
        lstrcpyW(note,
                 L"KEYS  verde=impostata  giallo=opt mancante  rosso=REQ mancante  | click MAP per layer");
        TextOutW(dc, r.left, foot.top, note, lstrlenW(note));
        return;
    }
    if (is_map_tab()) {
        map_view_paint(dc, &body);
        foot = r;
        foot.top = r.bottom - 14;
        SetTextColor(dc, CLR_OFF);
        lstrcpyW(note,
                 L"MAP  Enter su layer con key → KEYS  | coast/ais/weather=WIRED  altri=harvest/planned");
        TextOutW(dc, r.left, foot.top, note, lstrlenW(note));
        return;
    }
    paint_timer_bar(dc, &body);
    paint_search(dc, &body);
    paint_list(dc, &body);
    foot = r;
    foot.top = r.bottom - 14;
    SetTextColor(dc, CLR_OFF);
    wsprintfW(note,
              L"·verde=ok  ·giallo=manca API/blocked/stale  ·rosso=fail  | F5 rebuild  max_age tipico 48h");
    TextOutW(dc, r.left, foot.top, note, lstrlenW(note));
}

void ingest_view_tick(void) {
    DWORD now = GetTickCount();
    int left;

    if (g_next_rebuild_tick == 0)
        schedule_next_rebuild();

    if ((LONG)(g_next_rebuild_tick - now) <= 0) {
        g_countdown = 0;
        if (!g_rebuild_busy)
            ingest_view_force_rebuild();
        else
            schedule_next_rebuild();
    } else {
        left = (int)((g_next_rebuild_tick - now) / 1000);
        if (left < 0) left = 0;
        g_countdown = left;
    }
}

int ingest_view_poll(void) {
    FILETIME ft;
    WIN32_FILE_ATTRIBUTE_DATA fa;

    if (!GetFileAttributesExW(L"cache\\ingest\\manifest.json", GetFileExInfoStandard, &fa))
        return 0;
    ft = fa.ftLastWriteTime;
    if (!g_manifest_ft_set) {
        g_manifest_ft = ft;
        g_manifest_ft_set = 1;
        return 0;
    }
    if (ft.dwLowDateTime == g_manifest_ft.dwLowDateTime &&
        ft.dwHighDateTime == g_manifest_ft.dwHighDateTime)
        return 0;
    g_manifest_ft = ft;
    ingest_view_reload();
    return 1;
}

void ingest_view_scroll(int lines) {
    if (is_keys_tab()) {
        keys_view_scroll(lines);
        return;
    }
    if (is_map_tab()) {
        map_view_scroll(lines);
        return;
    }
    g_scroll += lines;
    if (g_scroll < 0) g_scroll = 0;
    if (g_scroll > g_slot_n - 1 && g_slot_n > 0) g_scroll = g_slot_n - 1;
}

static void toggle_group(int gi) {
    if (gi < 0 || gi >= g_grp_n) return;
    g_grp[gi].open = !g_grp[gi].open;
    rebuild_slots();
}

static void set_all_open(int open) {
    int g;
    for (g = 0; g < g_grp_n; g++)
        g_grp[g].open = open ? 1 : 0;
    rebuild_slots();
}

int ingest_view_hit(POINT pt) {
    int i, tab;

    tab = hit_ing_tab(pt);
    if (tab >= 0) {
        if (tab == g_ing_tab)
            return 1;
        g_ing_tab = tab;
        g_scroll = 0;
        if (is_keys_tab())
            keys_view_clear_edit();
        else
            rebuild_visible_ex();
        return 1;
    }

    if (is_keys_tab())
        return keys_view_hit(pt);
    if (is_map_tab())
        return map_view_hit(pt);
    for (i = 0; i < g_slot_vis; i++) {
        if (!PtInRect(&g_slot_rc[i], pt)) continue;
        {
            int si = g_slot_map[i];
            if (si < 0 || si >= g_slot_n) return 0;
            if (g_slots[si].is_hdr) {
                toggle_group(g_slots[si].gi);
                return 1;
            }
        }
    }
    return 0;
}

int ingest_view_key(int vk) {
    int first_hdr = -1;
    int i;

    if (vk == VK_OEM_COMMA) {
        ingest_view_tab_next(-1);
        return 1;
    }
    if (vk == VK_OEM_PERIOD) {
        ingest_view_tab_next(1);
        return 1;
    }
    if (is_keys_tab())
        return keys_view_key(vk);
    if (is_map_tab()) {
        int r = map_view_key(vk);
        if (r == 2) {
            int ki = map_view_selected_key_idx();
            g_ing_tab = 0;
            if (ki >= 0) {
                keys_view_select(ki);
                keys_view_edit_selected();
            }
            return 1;
        }
        return r ? 1 : 0;
    }

    switch (vk) {
    case VK_ESCAPE:
        if (!g_ing_search[0])
            return 0;
        ingest_view_clear_search();
        return 1;
    case VK_UP:   ingest_view_scroll(-5); return 1;
    case VK_DOWN: ingest_view_scroll(5); return 1;
    case VK_PRIOR: ingest_view_scroll(-20); return 1;
    case VK_NEXT:  ingest_view_scroll(20); return 1;
    case VK_HOME:  g_scroll = 0; return 1;
    case VK_END:   g_scroll = g_slot_n > ING_VIS_MAX ? g_slot_n - ING_VIS_MAX : 0; return 1;
    case VK_SPACE:
    case VK_RETURN:
        for (i = g_scroll; i < g_slot_n; i++) {
            if (g_slots[i].is_hdr) { first_hdr = i; break; }
        }
        if (first_hdr >= 0) {
            toggle_group(g_slots[first_hdr].gi);
            return 1;
        }
        return 0;
    case VK_OEM_4: /* [ */
        set_all_open(0);
        return 1;
    case VK_OEM_6: /* ] */
        set_all_open(1);
        return 1;
    case VK_F5:
        ingest_view_force_rebuild();
        return 1;
    case VK_OEM_PLUS:
    case VK_ADD:
        if (g_auto_sec < 600) g_auto_sec += 15;
        schedule_next_rebuild();
        return 1;
    case VK_OEM_MINUS:
    case VK_SUBTRACT:
        if (g_auto_sec > 15) g_auto_sec -= 15;
        schedule_next_rebuild();
        return 1;
    default:
        return 0;
    }
}

int ingest_view_wheel(int delta) {
    if (is_keys_tab())
        return keys_view_wheel(delta);
    if (is_map_tab())
        return map_view_wheel(delta);
    ingest_view_scroll(delta > 0 ? -5 : 5);
    return 1;
}
