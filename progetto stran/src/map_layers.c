#include "map_layers.h"
#include "keys.h"
#include <stdio.h>
#include <string.h>

static const MapLayerInfo g_layers[] = {
#include "map_layers_wm.inc"
};

static int g_n = (int)(sizeof(g_layers) / sizeof(g_layers[0]));

static int file_ok(const char *path) {
    DWORD a;
    if (!path || !path[0]) return 0;
    a = GetFileAttributesA(path);
    return (a != INVALID_FILE_ATTRIBUTES && !(a & FILE_ATTRIBUTE_DIRECTORY));
}

int map_layers_count(void) {
    return g_n;
}

const MapLayerInfo *map_layers_info(int idx) {
    if (idx < 0 || idx >= g_n) return NULL;
    return &g_layers[idx];
}

int map_layers_status(int idx) {
    const MapLayerInfo *L = map_layers_info(idx);
    int have_file, have_key, need_key, need_file;

    if (!L) return MAP_LAYER_ST_PLAN;

    need_key = L->key_id && L->key_id[0];
    need_file = L->data_file && L->data_file[0];
    have_key = need_key && keys_have(L->key_id);
    have_file = need_file && file_ok(L->data_file);

    /* Key file that IS the key (ais.key listed as data_file) */
    if (need_key && need_file && strstr(L->data_file, ".key")) {
        if (!have_key && !have_file)
            return MAP_LAYER_ST_NEEDKEY;
        if (L->desk_wired) return MAP_LAYER_ST_READY;
        return MAP_LAYER_ST_DATA;
    }

    if (need_key && !have_key) {
        /* opensky / aviationstack optional — still FREE if events exist */
        if (!strcmp(L->id, "opensky") || !strcmp(L->id, "flights") ||
            !strcmp(L->id, "fires") || !strcmp(L->id, "cyberThreats")) {
            if (file_ok("cache\\live\\events.json"))
                return L->desk_wired ? MAP_LAYER_ST_READY : MAP_LAYER_ST_FREE;
            return MAP_LAYER_ST_FREE;
        }
        return MAP_LAYER_ST_NEEDKEY;
    }

    if (need_file && !have_file)
        return MAP_LAYER_ST_NEEDFILE;

    if (!strcmp(L->kind, "PLANNED"))
        return MAP_LAYER_ST_PLAN;

    if (!need_key && !need_file)
        return L->desk_wired ? MAP_LAYER_ST_READY : MAP_LAYER_ST_FREE;

    if (L->desk_wired) return MAP_LAYER_ST_READY;
    return MAP_LAYER_ST_DATA;
}

void map_layers_status_label(int st, wchar_t *out, int cap) {
    const wchar_t *s = L"?";
    if (!out || cap < 8) return;
    switch (st) {
    case MAP_LAYER_ST_READY:    s = L"READY"; break;
    case MAP_LAYER_ST_DATA:     s = L"DATA"; break;
    case MAP_LAYER_ST_NEEDKEY:  s = L"NEED KEY"; break;
    case MAP_LAYER_ST_NEEDFILE: s = L"NEED FILE"; break;
    case MAP_LAYER_ST_FREE:     s = L"FREE OK"; break;
    case MAP_LAYER_ST_PLAN:     s = L"PLANNED"; break;
    }
    lstrcpynW(out, s, cap);
}

void map_layers_summary(wchar_t *buf, int cap) {
    int i, ready = 0, need = 0, plan = 0, free_n = 0;

    if (!buf || cap < 8) return;
    for (i = 0; i < g_n; i++) {
        int st = map_layers_status(i);
        if (st == MAP_LAYER_ST_READY || st == MAP_LAYER_ST_DATA) ready++;
        else if (st == MAP_LAYER_ST_NEEDKEY || st == MAP_LAYER_ST_NEEDFILE) need++;
        else if (st == MAP_LAYER_ST_FREE) free_n++;
        else plan++;
    }
    wsprintfW(buf, L"MAP layers=%d  ready/data=%d  free=%d  need=%d  planned=%d",
              g_n, ready, free_n, need, plan);
}
