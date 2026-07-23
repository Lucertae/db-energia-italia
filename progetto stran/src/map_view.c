#include "map_view.h"
#include "map_layers.h"
#include "keys.h"
#include <string.h>

#define MV_LINE 15
#define MV_VIS  36

static int g_sel;
static int g_scroll;
static RECT g_row_rc[MV_VIS];
static int g_row_idx[MV_VIS];
static int g_row_n;
static wchar_t g_msg[140];

void map_view_init(void) {
    g_sel = 0;
    g_scroll = 0;
    g_msg[0] = 0;
}

static COLORREF st_color(int st) {
    switch (st) {
    case MAP_LAYER_ST_READY:    return CLR_UP;
    case MAP_LAYER_ST_DATA:     return RGB(160, 200, 255);
    case MAP_LAYER_ST_FREE:     return RGB(160, 200, 160);
    case MAP_LAYER_ST_NEEDKEY:  return CLR_DN;
    case MAP_LAYER_ST_NEEDFILE: return RGB(255, 180, 80);
    default:                    return CLR_OFF;
    }
}

void map_view_paint(HDC dc, const RECT *rc) {
    RECT r = *rc;
    wchar_t line[460], sum[100], stlbl[24];
    int i, y, vis, n, start;

    if (r.bottom <= r.top + 40) return;
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);

    map_layers_summary(sum, (int)(sizeof(sum) / sizeof(sum[0])));
    SetTextColor(dc, CLR_ACC);
    {
        const wchar_t *hdr = L"MAP LAYERS — dati e API per i layer delle mapper";
        TextOutW(dc, r.left, r.top, hdr, lstrlenW(hdr));
    }
    r.top += 14;
    SetTextColor(dc, CLR_DIM);
    TextOutW(dc, r.left, r.top, sum, lstrlenW(sum));
    r.top += 14;
    SetTextColor(dc, CLR_OFF);
    {
        const wchar_t *help =
            L"READY=su desk  DATA=file ok  FREE=API pubblica  NEED KEY=inserisci in KEYS  Enter=vai a key";
        TextOutW(dc, r.left, r.top, help, lstrlenW(help));
    }
    r.top += 16;
    ui_hline(dc, r.left, r.top, r.right, CLR_GRID);
    r.top += 4;

    n = map_layers_count();
    vis = (r.bottom - r.top - 36) / MV_LINE;
    if (vis < 1) vis = 1;
    if (vis > MV_VIS) vis = MV_VIS;
    if (g_sel < 0) g_sel = 0;
    if (g_sel >= n) g_sel = n > 0 ? n - 1 : 0;
    if (g_scroll > g_sel) g_scroll = g_sel;
    if (g_scroll < g_sel - vis + 1) g_scroll = g_sel - vis + 1;
    if (g_scroll < 0) g_scroll = 0;
    start = g_scroll;

    g_row_n = 0;
    y = r.top;
    for (i = 0; i < vis && start + i < n; i++) {
        int idx = start + i;
        const MapLayerInfo *L = map_layers_info(idx);
        RECT row;
        int st;
        const char *file_s;
        const char *key_s;

        if (!L) break;
        st = map_layers_status(idx);
        map_layers_status_label(st, stlbl, 24);
        file_s = (L->data_file && L->data_file[0]) ? L->data_file : "-";
        key_s = (L->key_id && L->key_id[0]) ? L->key_id : "-";

        row.left = r.left;
        row.right = r.right;
        row.top = y;
        row.bottom = y + MV_LINE;
        if (g_row_n < MV_VIS) {
            g_row_rc[g_row_n] = row;
            g_row_idx[g_row_n] = idx;
            g_row_n++;
        }
        if (idx == g_sel)
            FillRect(dc, &row, bBand);

        SetTextColor(dc, st_color(st));
        wsprintfW(line, L"%-9s %-8hs %-22hs key:%-10hs %hs",
                  stlbl, L->kind, L->label, key_s, file_s);
        DrawTextW(dc, line, -1, &row,
                  DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS | DT_NOPREFIX);
        y += MV_LINE;
    }

    r.top = y + 6;
    if (g_sel >= 0 && g_sel < n) {
        const MapLayerInfo *L = map_layers_info(g_sel);
        if (L) {
            SetTextColor(dc, CLR_DIM);
            wsprintfW(line, L"%hs: %hs  | desk=%s",
                      L->id, L->note, L->desk_wired ? L"WIRED" : L"harvest/planned");
            TextOutW(dc, r.left, r.top, line, lstrlenW(line));
            r.top += 14;
        }
    }
    if (g_msg[0]) {
        SetTextColor(dc, CLR_ACC);
        TextOutW(dc, r.left, r.top, g_msg, lstrlenW(g_msg));
    }
}

void map_view_scroll(int lines) {
    int n = map_layers_count();
    g_sel += lines;
    if (g_sel < 0) g_sel = 0;
    if (g_sel >= n) g_sel = n > 0 ? n - 1 : 0;
}

int map_view_wheel(int delta) {
    map_view_scroll(delta > 0 ? -1 : 1);
    return 1;
}

int map_view_selected_key_idx(void) {
    const MapLayerInfo *L = map_layers_info(g_sel);
    if (!L || !L->key_id || !L->key_id[0]) return -1;
    return keys_find(L->key_id);
}

int map_view_hit(POINT pt) {
    int i;
    for (i = 0; i < g_row_n; i++) {
        if (PtInRect(&g_row_rc[i], pt)) {
            g_sel = g_row_idx[i];
            return 1;
        }
    }
    return 0;
}

int map_view_key(int vk) {
    switch (vk) {
    case VK_UP:    map_view_scroll(-1); return 1;
    case VK_DOWN:  map_view_scroll(1); return 1;
    case VK_PRIOR: map_view_scroll(-10); return 1;
    case VK_NEXT:  map_view_scroll(10); return 1;
    case VK_HOME:  g_sel = 0; return 1;
    case VK_END:
        g_sel = map_layers_count() - 1;
        if (g_sel < 0) g_sel = 0;
        return 1;
    case VK_RETURN: {
        int ki = map_view_selected_key_idx();
        if (ki >= 0) {
            /* ingest_view switches to KEYS — signal via msg; caller handles tab */
            wsprintfW(g_msg, L"Apri tab KEYS e seleziona id collegato (Enter)");
            return 2; /* special: jump to keys */
        }
        lstrcpyW(g_msg, L"Nessuna API key per questo layer (fonte pubblica o planned)");
        return 1;
    }
    default:
        return 0;
    }
}
