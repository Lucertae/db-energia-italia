#include "keys_view.h"
#include "keys.h"
#include <stdio.h>
#include <string.h>

#define KV_LINE 16
#define KV_VIS  40

static int g_sel;
static int g_scroll;
static int g_editing;
static char g_edit[KEYS_MAX_VALUE];
static wchar_t g_msg[120];
static RECT g_row_rc[KV_VIS];
static int g_row_idx[KV_VIS];
static int g_row_n;

void keys_view_init(void) {
    g_sel = 0;
    g_scroll = 0;
    g_editing = 0;
    g_edit[0] = 0;
    g_msg[0] = 0;
    keys_apply_all();
}

static void mask_value(const char *raw, wchar_t *out, int cap) {
    int n = (int)strlen(raw);
    int i, show;

    if (!raw || !raw[0]) {
        lstrcpyW(out, L"(vuota)");
        return;
    }
    if (n <= 6) {
        for (i = 0; i < n && i < cap - 1; i++)
            out[i] = L'*';
        out[i] = 0;
        return;
    }
    show = 4;
    if (show > n) show = n;
    for (i = 0; i < n - show && i < cap - 1; i++)
        out[i] = L'*';
    for (; i < n && i < cap - 1; i++)
        out[i] = (wchar_t)(unsigned char)raw[i];
    out[i] = 0;
}

static void begin_edit(int idx) {
    char cur[KEYS_MAX_VALUE];

    if (idx < 0 || idx >= keys_count()) return;
    g_sel = idx;
    g_editing = 1;
    g_edit[0] = 0;
    if (keys_load(idx, cur, (int)sizeof(cur)) > 0)
        lstrcpynA(g_edit, cur, (int)sizeof(g_edit));
    lstrcpyW(g_msg, L"EDIT: digita valore  Enter=salva  Esc=annulla  Del=cancella file");
}

static void commit_edit(void) {
    const KeyInfo *k;

    if (!g_editing) return;
    k = keys_info(g_sel);
    if (!k) return;
    if (keys_save(g_sel, g_edit)) {
        wsprintfW(g_msg, L"OK salvata %hs → %hs (+ env %hs)",
                  k->id, k->file, k->env);
    } else {
        wsprintfW(g_msg, L"ERRORE salvataggio %hs", k->id);
    }
    g_editing = 0;
    g_edit[0] = 0;
}

static void cancel_edit(void) {
    g_editing = 0;
    g_edit[0] = 0;
    lstrcpyW(g_msg, L"");
}

void keys_view_clear_edit(void) {
    cancel_edit();
}

int keys_view_editing(void) {
    return g_editing;
}

void keys_view_select(int idx) {
    if (idx < 0 || idx >= keys_count()) return;
    g_sel = idx;
    cancel_edit();
}

void keys_view_edit_selected(void) {
    begin_edit(g_sel);
}

void keys_view_paint(HDC dc, const RECT *rc) {
    RECT r = *rc;
    wchar_t line[420], sum[80], mask[80];
    int i, y, vis, n, start;
    char val[KEYS_MAX_VALUE];

    if (r.bottom <= r.top + 40) return;
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);

    keys_summary(sum, (int)(sizeof(sum) / sizeof(sum[0])));
    SetTextColor(dc, CLR_ACC);
    {
        const wchar_t *hdr = L"API KEYS — inserisci le chiavi necessarie al desk / harvest";
        TextOutW(dc, r.left, r.top, hdr, lstrlenW(hdr));
    }
    r.top += 14;
    SetTextColor(dc, CLR_DIM);
    TextOutW(dc, r.left, r.top, sum, lstrlenW(sum));
    r.top += 14;
    SetTextColor(dc, CLR_OFF);
    {
        const wchar_t *help =
            L"click / UP DOWN seleziona  Enter=edit  Esc=annulla  Del=rimuovi  digita+Enter=salva";
        TextOutW(dc, r.left, r.top, help, lstrlenW(help));
    }
    r.top += 16;
    ui_hline(dc, r.left, r.top, r.right, CLR_GRID);
    r.top += 4;

    n = keys_count();
    vis = (r.bottom - r.top - 20) / KV_LINE;
    if (vis < 1) vis = 1;
    if (vis > KV_VIS) vis = KV_VIS;
    if (g_sel < 0) g_sel = 0;
    if (g_sel >= n) g_sel = n - 1;
    if (g_scroll > g_sel) g_scroll = g_sel;
    if (g_scroll < g_sel - vis + 1) g_scroll = g_sel - vis + 1;
    if (g_scroll < 0) g_scroll = 0;
    start = g_scroll;

    g_row_n = 0;
    y = r.top;
    for (i = 0; i < vis && start + i < n; i++) {
        int idx = start + i;
        const KeyInfo *k = keys_info(idx);
        RECT row;
        int have;
        COLORREF st;

        if (!k) break;
        have = keys_have_idx(idx);
        if (have)
            st = CLR_UP;
        else if (k->required)
            st = CLR_DN;
        else
            st = RGB(255, 180, 80);

        row.left = r.left;
        row.right = r.right;
        row.top = y;
        row.bottom = y + KV_LINE;
        if (g_row_n < KV_VIS) {
            g_row_rc[g_row_n] = row;
            g_row_idx[g_row_n] = idx;
            g_row_n++;
        }

        if (idx == g_sel)
            FillRect(dc, &row, bBand);

        keys_load(idx, val, (int)sizeof(val));
        if (g_editing && idx == g_sel) {
            int el = (int)strlen(g_edit);
            wchar_t eb[KEYS_MAX_VALUE + 4];
            int j;
            for (j = 0; j < el && j < KEYS_MAX_VALUE - 1; j++)
                eb[j] = (wchar_t)(unsigned char)g_edit[j];
            eb[j] = L'_';
            eb[j + 1] = 0;
            SetTextColor(dc, CLR_ACC);
            wsprintfW(line, L"> %-10hs %-28hs  EDIT: %s",
                      k->id, k->env, eb);
        } else {
            mask_value(val, mask, 80);
            SetTextColor(dc, st);
            wsprintfW(line, L"%c %-10hs %-22hs %-8hs %s %-28hs %s",
                      have ? L'+' : L'-',
                      k->id,
                      k->label,
                      k->sector,
                      k->required ? L"REQ" : L"opt",
                      k->env,
                      mask);
        }
        DrawTextW(dc, line, -1, &row,
                  DT_LEFT | DT_VCENTER | DT_SINGLELINE | DT_END_ELLIPSIS | DT_NOPREFIX);
        y += KV_LINE;
    }

    r.top = y + 6;
    if (g_sel >= 0 && g_sel < n) {
        const KeyInfo *k = keys_info(g_sel);
        if (k) {
            SetTextColor(dc, CLR_DIM);
            wsprintfW(line, L"file: %hs    portal: %hs", k->file, k->portal);
            TextOutW(dc, r.left, r.top, line, lstrlenW(line));
            r.top += 14;
        }
    }
    if (g_msg[0]) {
        SetTextColor(dc, CLR_ACC);
        TextOutW(dc, r.left, r.top, g_msg, lstrlenW(g_msg));
    }
}

void keys_view_scroll(int lines) {
    int n = keys_count();
    g_sel += lines;
    if (g_sel < 0) g_sel = 0;
    if (g_sel >= n) g_sel = n > 0 ? n - 1 : 0;
}

int keys_view_wheel(int delta) {
    keys_view_scroll(delta > 0 ? -1 : 1);
    return 1;
}

int keys_view_hit(POINT pt) {
    int i;
    for (i = 0; i < g_row_n; i++) {
        if (PtInRect(&g_row_rc[i], pt)) {
            if (g_row_idx[i] == g_sel && !g_editing)
                begin_edit(g_sel);
            else {
                g_sel = g_row_idx[i];
                cancel_edit();
            }
            return 1;
        }
    }
    return 0;
}

void keys_view_char(wchar_t ch) {
    int n;

    if (!g_editing) return;
    n = (int)strlen(g_edit);
    if (ch == 8 || ch == 127) {
        if (n > 0) g_edit[n - 1] = 0;
        return;
    }
    if (ch < 32 || ch > 126) return;
    if (n >= KEYS_MAX_VALUE - 1) return;
    g_edit[n] = (char)ch;
    g_edit[n + 1] = 0;
}

int keys_view_key(int vk) {
    switch (vk) {
    case VK_ESCAPE:
        if (g_editing) {
            cancel_edit();
            return 1;
        }
        return 0;
    case VK_UP:
        if (g_editing) return 1;
        keys_view_scroll(-1);
        return 1;
    case VK_DOWN:
        if (g_editing) return 1;
        keys_view_scroll(1);
        return 1;
    case VK_PRIOR:
        if (g_editing) return 1;
        keys_view_scroll(-10);
        return 1;
    case VK_NEXT:
        if (g_editing) return 1;
        keys_view_scroll(10);
        return 1;
    case VK_HOME:
        if (g_editing) return 1;
        g_sel = 0;
        return 1;
    case VK_END:
        if (g_editing) return 1;
        g_sel = keys_count() - 1;
        if (g_sel < 0) g_sel = 0;
        return 1;
    case VK_RETURN:
        if (g_editing) {
            commit_edit();
            return 1;
        }
        begin_edit(g_sel);
        return 1;
    case VK_DELETE:
        if (g_editing) {
            /* clear edit buffer only if empty → clear key; else backspace last */
            if (g_edit[0]) {
                g_edit[0] = 0;
                return 1;
            }
        }
        {
            const KeyInfo *k = keys_info(g_sel);
            keys_clear(g_sel);
            g_editing = 0;
            g_edit[0] = 0;
            if (k)
                wsprintfW(g_msg, L"rimossa %hs", k->id);
        }
        return 1;
    default:
        return 0;
    }
}
