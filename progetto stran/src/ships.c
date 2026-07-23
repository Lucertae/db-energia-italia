#include "ships.h"
#include "chokepoints.h"
#include "ingest_ais.h"
#include "world_map.h"
#include "map_canvas.h"
#include <process.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <winhttp.h>

#pragma comment(lib, "winhttp.lib")

#define AIS_HOST         L"stream.aisstream.io"
#define AIS_PATH         L"/v0/stream"
#define AIS_STALE_S      1200
#define AIS_RECV_MAX     65536
#define AIS_HASH_CAP     65536
#define AIS_HASH_MAX_PROBE 128
#define AIS_PURGE_EVERY  8192
#define SHIP_GRID_CELL   12
#define SHIP_GRID_MAX_W  200
#define SHIP_GRID_MAX_H  120
#define SHIP_HIT_R2      (10 * 10)

static ShipVessel g_ships[SHIP_MAX];
static uint32_t   g_hash_mmsi[AIS_HASH_CAP];
static uint32_t   g_hash_idx[AIS_HASH_CAP];
static BYTE       g_ais_recv[AIS_RECV_MAX];
static int16_t    g_grid_head[SHIP_GRID_MAX_W * SHIP_GRID_MAX_H];
static int16_t    g_grid_next[SHIP_MAX];
static int        g_grid_w, g_grid_h;
static MapCanvas  g_frame;
static int        g_ship_n;
static int        g_sel = -1;
static RECT       g_map_rc;
static CRITICAL_SECTION g_lock;
static volatile LONG g_run;
static HANDLE     g_thread;
static wchar_t    g_status[160] = L"AIS: init";
static volatile LONG g_msg_count;

static uint32_t epoch_sec(void) {
    FILETIME ft;
    ULARGE_INTEGER u;

    GetSystemTimeAsFileTime(&ft);
    u.LowPart = ft.dwLowDateTime;
    u.HighPart = ft.dwHighDateTime;
    return (uint32_t)((u.QuadPart - 116444736000000000ULL) / 10000000ULL);
}

static void hash_clear(void) {
    memset(g_hash_mmsi, 0, sizeof(g_hash_mmsi));
    memset(g_hash_idx, 0, sizeof(g_hash_idx));
}

static int hash_probe(uint32_t mmsi) {
    uint32_t p = mmsi % AIS_HASH_CAP;
    int steps = 0;

    while (g_hash_mmsi[p] != 0 && g_hash_mmsi[p] != mmsi) {
        p = (p + 1) % AIS_HASH_CAP;
        if (++steps >= AIS_HASH_MAX_PROBE) return -1;
    }
    return (int)p;
}

static void hash_rebuild(void) {
    int i;
    hash_clear();
    for (i = 0; i < g_ship_n; i++) {
        if (!g_ships[i].active || g_ships[i].mmsi == 0) continue;
        {
            int p = hash_probe(g_ships[i].mmsi);
            if (p < 0) continue;
            g_hash_mmsi[p] = g_ships[i].mmsi;
            g_hash_idx[p] = (uint32_t)i;
        }
    }
}

static void ships_purge_stale(void) {
    int i, now = (int)epoch_sec(), w = 0;

    EnterCriticalSection(&g_lock);
    for (i = 0; i < g_ship_n; i++) {
        if (g_ships[i].active && (now - (int)g_ships[i].seen) < AIS_STALE_S) {
            if (w != i) g_ships[w] = g_ships[i];
            w++;
        }
    }
    g_ship_n = w;
    if (g_sel >= g_ship_n) g_sel = -1;
    hash_rebuild();
    LeaveCriticalSection(&g_lock);
}

static void ship_upsert(uint32_t mmsi, float lat, float lon, float sog, float cog) {
    int slot, hp;
    uint32_t now = epoch_sec();

    if (mmsi == 0 || lat < -90.0f || lat > 90.0f || lon < -180.0f || lon > 180.0f) return;
    EnterCriticalSection(&g_lock);
    hp = hash_probe(mmsi);
    if (hp < 0) {
        LeaveCriticalSection(&g_lock);
        return;
    }
    if (g_hash_mmsi[hp] == mmsi) {
        slot = (int)g_hash_idx[hp];
    } else if (g_ship_n < SHIP_MAX) {
        slot = g_ship_n++;
        memset(&g_ships[slot], 0, sizeof(g_ships[slot]));
        g_ships[slot].mmsi = mmsi;
        g_hash_mmsi[hp] = mmsi;
        g_hash_idx[hp] = (uint32_t)slot;
    } else {
        int i, oldest = 0;
        for (i = 1; i < g_ship_n; i++)
            if (g_ships[i].seen < g_ships[oldest].seen) oldest = i;
        slot = oldest;
        if (g_ships[slot].mmsi) {
            int op = hash_probe(g_ships[slot].mmsi);
            if (op >= 0) g_hash_mmsi[op] = 0;
        }
        memset(&g_ships[slot], 0, sizeof(g_ships[slot]));
        g_ships[slot].mmsi = mmsi;
        g_hash_mmsi[hp] = mmsi;
        g_hash_idx[hp] = (uint32_t)slot;
    }
    g_ships[slot].lat = lat;
    g_ships[slot].lon = lon;
    g_ships[slot].sog = sog;
    g_ships[slot].cog = cog;
    g_ships[slot].seen = now;
    g_ships[slot].active = 1;
    LeaveCriticalSection(&g_lock);
}

static void parse_ais_message(const char *json) {
    uint32_t mmsi = 0;
    float lat = 0.0f, lon = 0.0f, sog = 0.0f, cog = 0.0f;
    LONG n;

    if (!json || strstr(json, "PositionReport") == NULL) return;
    if (!ingest_ais_json_uint(json, "UserID", &mmsi)) {
        if (!ingest_ais_json_uint(json, "MMSI", &mmsi)) return;
    }
    if (!ingest_ais_json_float(json, "Latitude", &lat)) return;
    if (!ingest_ais_json_float(json, "Longitude", &lon)) return;
    ingest_ais_json_float(json, "Sog", &sog);
    ingest_ais_json_float(json, "Cog", &cog);
    ship_upsert(mmsi, lat, lon, sog, cog);
    n = InterlockedIncrement(&g_msg_count);
    if ((n % AIS_PURGE_EVERY) == 0) ships_purge_stale();
}

static BOOL ais_send_subscribe(HINTERNET ws, const char *api_key) {
    char msg[512];
    DWORD n;

    wsprintfA(msg,
        "{\"APIKey\":\"%s\",\"BoundingBoxes\":[[[-90,-180],[90,180]]],"
        "\"FilterMessageTypes\":[\"PositionReport\"]}",
        api_key);
    n = (DWORD)strlen(msg);
    return WinHttpWebSocketSend(ws, WINHTTP_WEB_SOCKET_UTF8_MESSAGE_BUFFER_TYPE,
                                (PVOID)msg, n) == NO_ERROR;
}

static BOOL ais_session_once(const char *api_key) {
    HINTERNET ses = NULL, con = NULL, req = NULL, ws = NULL;
    BOOL ok = FALSE;
    DWORD opt = WINHTTP_FLAG_SECURE_PROTOCOL_TLS1_2;

    ses = WinHttpOpen(L"OPSDesk-AIS/1.0", WINHTTP_ACCESS_TYPE_AUTOMATIC_PROXY,
                      WINHTTP_NO_PROXY_NAME, WINHTTP_NO_PROXY_BYPASS, 0);
    if (!ses) goto done;
#ifdef WINHTTP_FLAG_SECURE_PROTOCOL_TLS1_3
    opt |= WINHTTP_FLAG_SECURE_PROTOCOL_TLS1_3;
#endif
    WinHttpSetOption(ses, WINHTTP_OPTION_SECURE_PROTOCOLS, &opt, sizeof(opt));
    con = WinHttpConnect(ses, AIS_HOST, INTERNET_DEFAULT_HTTPS_PORT, 0);
    if (!con) goto done;
    req = WinHttpOpenRequest(con, L"GET", AIS_PATH, NULL, WINHTTP_NO_REFERER,
                             WINHTTP_DEFAULT_ACCEPT_TYPES, WINHTTP_FLAG_SECURE);
    if (!req) goto done;
    if (!WinHttpSetOption(req, WINHTTP_OPTION_UPGRADE_TO_WEB_SOCKET, NULL, 0)) goto done;
    if (!WinHttpSendRequest(req, WINHTTP_NO_ADDITIONAL_HEADERS, 0,
                            WINHTTP_NO_REQUEST_DATA, 0, 0, 0)) goto done;
    if (!WinHttpReceiveResponse(req, NULL)) goto done;
    ws = WinHttpWebSocketCompleteUpgrade(req, 0);
    if (!ws) goto done;
    WinHttpCloseHandle(req);
    req = NULL;
    if (!ais_send_subscribe(ws, api_key)) goto done;
    wsprintfW(g_status, L"AIS live  stream.aisstream.io");
    while (InterlockedCompareExchange(&g_run, 1, 1) == 1) {
        DWORD read = 0;
        WINHTTP_WEB_SOCKET_BUFFER_TYPE typ;
        DWORD j;

        if (WinHttpWebSocketReceive(ws, g_ais_recv, sizeof(g_ais_recv) - 1, &read, &typ) != NO_ERROR)
            break;
        if (typ == WINHTTP_WEB_SOCKET_CLOSE_BUFFER_TYPE) break;
        if (read == 0) continue;
        g_ais_recv[read] = 0;
        for (j = 0; j + 32 < read; j++) {
            if (g_ais_recv[j] == '{' && strstr((char *)g_ais_recv + j, "PositionReport")) {
                parse_ais_message((char *)g_ais_recv + j);
                break;
            }
        }
        if (strstr((char *)g_ais_recv, "\"error\"")) break;
    }
    ok = TRUE;
done:
    if (ws) WinHttpWebSocketClose(ws, WINHTTP_WEB_SOCKET_SUCCESS_CLOSE_STATUS, NULL, 0);
    if (req) WinHttpCloseHandle(req);
    if (con) WinHttpCloseHandle(con);
    if (ses) WinHttpCloseHandle(ses);
    return ok;
}

static unsigned __stdcall ais_worker(void *arg) {
    char key[128];
    (void)arg;

    Sleep(500);
    while (InterlockedCompareExchange(&g_run, 1, 1) == 1) {
        if (!ingest_ais_load_key(key, sizeof(key))) {
            lstrcpyW(g_status, L"AIS: cache\\ais.key mancante");
            Sleep(5000);
            continue;
        }
        lstrcpyW(g_status, L"AIS connect...");
        if (!ais_session_once(key))
            lstrcpyW(g_status, L"AIS reconnect 15s...");
        Sleep(15000);
    }
    return 0;
}

void ships_init(void) {
    InitializeCriticalSection(&g_lock);
    memset(g_ships, 0, sizeof(g_ships));
    hash_clear();
    g_ship_n = 0;
    g_sel = -1;
    world_map_init();
    InterlockedExchange(&g_run, 1);
    g_thread = (HANDLE)_beginthreadex(NULL, 0, ais_worker, NULL, 0, NULL);
}

void ships_shutdown(void) {
    InterlockedExchange(&g_run, 0);
    if (g_thread) {
        WaitForSingleObject(g_thread, 3000);
        CloseHandle(g_thread);
        g_thread = NULL;
    }
    map_canvas_destroy(&g_frame);
    world_map_shutdown();
    DeleteCriticalSection(&g_lock);
}

int ships_count(void) {
    int n, i, now = (int)epoch_sec();
    EnterCriticalSection(&g_lock);
    n = 0;
    for (i = 0; i < g_ship_n; i++)
        if (g_ships[i].active && (now - (int)g_ships[i].seen) < AIS_STALE_S) n++;
    LeaveCriticalSection(&g_lock);
    return n;
}

int ships_count_in_bbox(float lat_min, float lat_max, float lon_min, float lon_max) {
    int i, n = 0, now = (int)epoch_sec();

    EnterCriticalSection(&g_lock);
    for (i = 0; i < g_ship_n; i++) {
        if (!g_ships[i].active || (now - (int)g_ships[i].seen) >= AIS_STALE_S) continue;
        if (g_ships[i].lat >= lat_min && g_ships[i].lat <= lat_max &&
            g_ships[i].lon >= lon_min && g_ships[i].lon <= lon_max)
            n++;
    }
    LeaveCriticalSection(&g_lock);
    return n;
}

int ships_selected(void) { return g_sel; }

void ships_set_selected(int i) {
    if (i < 0 || i >= g_ship_n) return;
    g_sel = i;
}

const ShipVessel *ships_get(int i) {
    if (i < 0 || i >= g_ship_n) return NULL;
    return &g_ships[i];
}

const wchar_t *ships_status_line(void) { return g_status; }

void map_project(float lat, float lon, const RECT *map, LONG *ox, LONG *oy) {
    int w = map->right - map->left;
    int h = map->bottom - map->top;
    int x, y;
    world_map_project_local(lat, lon, w, h, &x, &y);
    *ox = map->left + x;
    *oy = map->top + y;
}

static COLORREF ship_color(const ShipVessel *v, int selected) {
    if (selected) return RGB(255, 220, 80);
    if (v->sog >= 10.0f) return RGB(120, 210, 120);
    if (v->sog >= 4.0f)  return RGB(200, 200, 200);
    return RGB(120, 120, 120);
}

static void grid_reset(int mw, int mh) {
    g_grid_w = mw / SHIP_GRID_CELL;
    g_grid_h = mh / SHIP_GRID_CELL;
    if (g_grid_w < 1) g_grid_w = 1;
    if (g_grid_h < 1) g_grid_h = 1;
    if (g_grid_w > SHIP_GRID_MAX_W) g_grid_w = SHIP_GRID_MAX_W;
    if (g_grid_h > SHIP_GRID_MAX_H) g_grid_h = SHIP_GRID_MAX_H;
    memset(g_grid_head, -1, (size_t)g_grid_w * (size_t)g_grid_h * sizeof(g_grid_head[0]));
}

static void grid_insert(int slot, int px, int py) {
    int cx = px / SHIP_GRID_CELL;
    int cy = py / SHIP_GRID_CELL;
    int idx;

    if (cx < 0) cx = 0;
    if (cy < 0) cy = 0;
    if (cx >= g_grid_w) cx = g_grid_w - 1;
    if (cy >= g_grid_h) cy = g_grid_h - 1;
    idx = cy * g_grid_w + cx;
    g_grid_next[slot] = g_grid_head[idx];
    g_grid_head[idx] = (int16_t)slot;
}

static void grid_build_only(int mw, int mh, int now) {
    int i;

    grid_reset(mw, mh);
    for (i = 0; i < g_ship_n; i++) {
        int px, py;
        if (!g_ships[i].active || (now - (int)g_ships[i].seen) >= AIS_STALE_S) continue;
        world_map_project_local(g_ships[i].lat, g_ships[i].lon, mw, mh, &px, &py);
        grid_insert(i, px, py);
    }
}

static void grid_build_and_raster(int mw, int mh, int now, int sel) {
    int i;

    grid_reset(mw, mh);
    for (i = 0; i < g_ship_n; i++) {
        int px, py;
        COLORREF c;

        if (!g_ships[i].active || (now - (int)g_ships[i].seen) >= AIS_STALE_S) continue;
        world_map_project_local(g_ships[i].lat, g_ships[i].lon, mw, mh, &px, &py);
        grid_insert(i, px, py);
        c = ship_color(&g_ships[i], i == sel);
        map_canvas_plot(&g_frame, px, py, c);
    }
}

static int grid_pick(int lx, int ly, int mw, int mh, int now) {
    int cx = lx / SHIP_GRID_CELL;
    int cy = ly / SHIP_GRID_CELL;
    int best = -1, best_d = SHIP_HIT_R2 + 1;
    int dx, dy;

    if (lx < 0 || ly < 0) return -1;
    for (dy = -1; dy <= 1; dy++) {
        for (dx = -1; dx <= 1; dx++) {
            int gx = cx + dx, gy = cy + dy, idx, slot;
            if (gx < 0 || gy < 0 || gx >= g_grid_w || gy >= g_grid_h) continue;
            idx = gy * g_grid_w + gx;
            for (slot = g_grid_head[idx]; slot >= 0; slot = g_grid_next[slot]) {
                int px, py, ddx, ddy, d;
                if (!g_ships[slot].active || (now - (int)g_ships[slot].seen) >= AIS_STALE_S)
                    continue;
                world_map_project_local(g_ships[slot].lat, g_ships[slot].lon,
                                        mw, mh, &px, &py);
                ddx = lx - px;
                ddy = ly - py;
                d = ddx * ddx + ddy * ddy;
                if (d < best_d) { best_d = d; best = slot; }
            }
        }
    }
    return (best_d <= SHIP_HIT_R2) ? best : -1;
}

int ships_map_hit(POINT pt) {
    int now = (int)epoch_sec();
    int lx, ly, hit, mw, mh;

    if (!PtInRect(&g_map_rc, pt)) return -1;
    lx = pt.x - g_map_rc.left;
    ly = pt.y - g_map_rc.top;
    mw = g_map_rc.right - g_map_rc.left;
    mh = g_map_rc.bottom - g_map_rc.top;
    EnterCriticalSection(&g_lock);
    grid_build_only(mw, mh, now);
    hit = grid_pick(lx, ly, mw, mh, now);
    LeaveCriticalSection(&g_lock);
    return hit;
}

void ships_paint(HDC dc, const RECT *rc) {
    RECT r = *rc, map, side, top;
    wchar_t line[160];
    wchar_t lat_s[16], lon_s[16];
    int i, n, now = (int)epoch_sec(), tracked, mw, mh, sel;
    const MapCanvas *base;
    HPEN grid, old_pen;

    if (r.bottom <= r.top + 40) return;
    top = r;
    top.bottom = top.top + 14;
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    SetTextColor(dc, CLR_DIM);
    n = ships_count();
    EnterCriticalSection(&g_lock);
    tracked = g_ship_n;
    LeaveCriticalSection(&g_lock);
    wsprintfW(line, L"%s  |  %d attive / %d track  |  msg %ld",
              ships_status_line(), n, tracked, (long)g_msg_count);
    TextOutW(dc, top.left, top.top, line, lstrlenW(line));
    {
        int lng7 = 0, dlng = 0;
        chokepoints_lng_eu_stats(&lng7, &dlng);
        wsprintfW(line, L"  |  LNG tanker -> EU 7d: %d (%+d)", lng7, dlng);
        SetTextColor(dc, dlng >= 0 ? CLR_ACC : CLR_DN);
        TextOutW(dc, top.left + 520, top.top, line, lstrlenW(line));
    }
    r.top += 16;

    side.left = r.right - (r.right - r.left) * 38 / 100;
    side.right = r.right;
    side.top = r.top;
    side.bottom = r.bottom;
    map = r;
    map.right = side.left - 8;
    g_map_rc = map;

    ui_subheading(dc, &map, L"AIS MAP  (click nave)");
    map.top += 14;
    mw = map.right - map.left;
    mh = map.bottom - map.top;

    world_map_ensure(dc, &map);
    base = world_map_base();
    if (!map_canvas_resize(&g_frame, dc, mw, mh) || !base || !base->bits) return;
    {
        size_t src_bytes = (size_t)base->stride * (size_t)base->h;
        size_t dst_bytes = (size_t)g_frame.stride * (size_t)g_frame.h;
        if (src_bytes > dst_bytes) src_bytes = dst_bytes;
        memcpy(g_frame.bits, base->bits, src_bytes);
    }

    EnterCriticalSection(&g_lock);
    sel = g_sel;
    grid_build_and_raster(mw, mh, now, sel);
    LeaveCriticalSection(&g_lock);

    map_canvas_blit(dc, &g_frame, map.left, map.top);

    if (sel >= 0 && sel < g_ship_n) {
        int px, py;
        COLORREF c = RGB(255, 220, 80);
        EnterCriticalSection(&g_lock);
        if (g_ships[sel].active && (now - (int)g_ships[sel].seen) < AIS_STALE_S) {
            world_map_project_local(g_ships[sel].lat, g_ships[sel].lon, mw, mh, &px, &py);
            SetPixel(dc, map.left + px, map.top + py, c);
            SetPixel(dc, map.left + px + 1, map.top + py, c);
            SetPixel(dc, map.left + px - 1, map.top + py, c);
            SetPixel(dc, map.left + px, map.top + py + 1, c);
            SetPixel(dc, map.left + px, map.top + py - 1, c);
        }
        LeaveCriticalSection(&g_lock);
    }

    grid = CreatePen(PS_SOLID, 1, RGB(28, 36, 44));
    old_pen = (HPEN)SelectObject(dc, grid);
    MoveToEx(dc, map.left, map.top + mh / 2, NULL);
    LineTo(dc, map.right, map.top + mh / 2);
    MoveToEx(dc, map.left + mw / 2, map.top, NULL);
    LineTo(dc, map.left + mw / 2, map.bottom);
    SelectObject(dc, old_pen);
    DeleteObject(grid);

    ui_subheading(dc, &side, L"DETTAGLIO");
    side.top += 16;
    if (g_sel >= 0 && g_sel < g_ship_n) {
        ShipVessel v;
        EnterCriticalSection(&g_lock);
        v = g_ships[g_sel];
        LeaveCriticalSection(&g_lock);
        if (v.active) {
            ui_fmt_wdouble(lat_s, 16, v.lat, 4);
            ui_fmt_wdouble(lon_s, 16, v.lon, 4);
            ui_fmt_wdouble(line, 16, v.sog, 1);
            wsprintfW(line, L"MMSI %u", v.mmsi);
            SetTextColor(dc, CLR_ACC);
            TextOutW(dc, side.left, side.top, line, lstrlenW(line));
            side.top += 14;
            SetTextColor(dc, CLR_TXT);
            wsprintfW(line, L"LAT %s  LON %s", lat_s, lon_s);
            TextOutW(dc, side.left, side.top, line, lstrlenW(line));
            side.top += 14;
            ui_fmt_wdouble(lat_s, 16, v.sog, 1);
            ui_fmt_wdouble(lon_s, 16, v.cog, 0);
            wsprintfW(line, L"SOG %s kn  COG %s", lat_s, lon_s);
            TextOutW(dc, side.left, side.top, line, lstrlenW(line));
            side.top += 14;
            wsprintfW(line, L"age %ds", now - (int)v.seen);
            SetTextColor(dc, CLR_DIM);
            TextOutW(dc, side.left, side.top, line, lstrlenW(line));
        }
    } else {
        SetTextColor(dc, CLR_OFF);
        TextOutW(dc, side.left, side.top, L"click su una nave", 17);
    }

    side.top += 24;
    ui_subheading(dc, &side, L"ULTIME NAVI");
    side.top += 14;
    {
        int list_bottom = side.top + (side.bottom - side.top) * 45 / 100;
        EnterCriticalSection(&g_lock);
        for (i = g_ship_n - 1; i >= 0 && side.top + 14 < list_bottom; i--) {
        if (!g_ships[i].active || (now - (int)g_ships[i].seen) >= AIS_STALE_S) continue;
        ui_fmt_wdouble(lat_s, 16, g_ships[i].lat, 2);
        ui_fmt_wdouble(lon_s, 16, g_ships[i].lon, 2);
        SetTextColor(dc, i == g_sel ? CLR_ACC : CLR_DIM);
        wsprintfW(line, L"%u  %s,%s", g_ships[i].mmsi, lat_s, lon_s);
        TextOutW(dc, side.left, side.top, line, lstrlenW(line));
        side.top += 12;
    }
        LeaveCriticalSection(&g_lock);
    }

    {
        RECT cp_rc = side;
        cp_rc.top = side.top + 8;
        if (cp_rc.top + 40 < side.bottom)
            chokepoints_paint(dc, &cp_rc);
    }
}
