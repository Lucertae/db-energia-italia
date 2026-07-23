#include "world_map.h"
#include "map_canvas.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define WORLD_PT_MAX   8192
#define WORLD_SEG_MAX  512

static float g_lat[WORLD_PT_MAX];
static float g_lon[WORLD_PT_MAX];
static int   g_seg_start[WORLD_SEG_MAX];
static int   g_seg_len[WORLD_SEG_MAX];
static int   g_seg_n;
static int   g_pt_n;

static MapCanvas g_base;
static RECT      g_baked_rc;
static int       g_baked_ok;

void world_map_project_local(float lat, float lon, int w, int h, int *x, int *y) {
    if (w < 2) w = 2;
    if (h < 2) h = 2;
    *x = (int)((lon + 180.0f) * (float)(w - 1) / 360.0f);
    *y = (int)((90.0f - lat) * (float)(h - 1) / 180.0f);
    if (*x < 0) *x = 0;
    if (*y < 0) *y = 0;
    if (*x >= w) *x = w - 1;
    if (*y >= h) *y = h - 1;
}

const MapCanvas *world_map_base(void) {
    return g_baked_ok ? &g_base : NULL;
}

static void world_map_bake_coast(int w, int h) {
    HPEN pen, old_pen;
    int s;

    pen = CreatePen(PS_SOLID, 1, WORLD_COAST_RGB);
    old_pen = (HPEN)SelectObject(g_base.dc, pen);
    for (s = 0; s < g_seg_n; s++) {
        POINT pts[512];
        int start = g_seg_start[s];
        int len = g_seg_len[s];
        int off = 0;

        if (len < 2 || start < 0 || start + len > g_pt_n) continue;
        while (off < len - 1) {
            int chunk = len - off;
            int i;

            if (chunk > 512) chunk = 512;
            if (chunk < 2) break;
            for (i = 0; i < chunk; i++) {
                int idx = start + off + i;
                int px, py;
                world_map_project_local(g_lat[idx], g_lon[idx], w, h, &px, &py);
                pts[i].x = px;
                pts[i].y = py;
            }
            Polyline(g_base.dc, pts, chunk);
            off += chunk - 1;
        }
    }
    SelectObject(g_base.dc, old_pen);
    DeleteObject(pen);
}

void world_map_init(void) {
    char line[64];
    FILE *f;
    int cur_seg = -1;

    g_seg_n = 0;
    g_pt_n = 0;
    g_baked_ok = 0;
    memset(&g_baked_rc, 0, sizeof(g_baked_rc));
    CreateDirectoryW(L"cache", NULL);
    f = fopen("cache\\world_coast.csv", "r");
    if (!f) return;

    while (fgets(line, sizeof(line), f)) {
        float lat, lon;
        char *e;

        if (line[0] == '\n' || line[0] == '\r') {
            cur_seg = -1;
            continue;
        }
        lat = (float)strtod(line, &e);
        if (e == line) continue;
        while (*e == ',') e++;
        lon = (float)strtod(e, NULL);
        if (g_pt_n >= WORLD_PT_MAX) continue;
        if (cur_seg < 0) {
            if (g_seg_n >= WORLD_SEG_MAX) continue;
            cur_seg = g_seg_n++;
            g_seg_start[cur_seg] = g_pt_n;
            g_seg_len[cur_seg] = 0;
        }
        g_lat[g_pt_n] = lat;
        g_lon[g_pt_n] = lon;
        g_pt_n++;
        g_seg_len[cur_seg]++;
    }
    fclose(f);
}

void world_map_shutdown(void) {
    map_canvas_destroy(&g_base);
    g_baked_ok = 0;
}

void world_map_ensure(HDC ref_dc, const RECT *rc) {
    int w, h;

    if (!ref_dc || !rc) return;
    w = rc->right - rc->left;
    h = rc->bottom - rc->top;
    if (w < 4 || h < 4) return;
    if (g_baked_ok && EqualRect(&g_baked_rc, rc) && g_base.w == w && g_base.h == h)
        return;

    if (!map_canvas_resize(&g_base, ref_dc, w, h)) return;
    map_canvas_clear(&g_base, WORLD_OCEAN_RGB);
    if (g_seg_n > 0)
        world_map_bake_coast(w, h);
    g_baked_rc = *rc;
    g_baked_ok = 1;
}

void world_map_blit(HDC dc, const RECT *rc) {
    if (!g_baked_ok || !dc || !rc) return;
    map_canvas_blit(dc, &g_base, rc->left, rc->top);
}
