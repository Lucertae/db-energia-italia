#include "sig.h"
#include "modules.h"
#include "spine.h"
#include <stdio.h>
#include <string.h>

#define SIG_HIST 12

typedef struct {
    char id[24];
    char stage[24];
    char block[96];
    char age[16];
} SigCard;

static SigCard g_pipe[16];
static int g_pipe_n;
static char g_last_reject[96];
static char g_next_cand[96];
static int g_promoted;

static void parse_modules_index(void) {
    static char buf[65536];
    FILE *f;
    size_t n;
    const char *p, *obj;
    char block[640];

    g_pipe_n = 0;
    g_promoted = 0;
    lstrcpyA(g_last_reject, "PWR-01-v2 (hit<52%)");
    lstrcpyA(g_next_cand, "v2+multigrid+ID-AEP");

    f = _wfopen(L"cache\\spine\\modules_index.json", L"r");
    if (!f) return;
    n = fread(buf, 1, sizeof(buf) - 1, f);
    fclose(f);
    buf[n] = 0;

    p = strstr(buf, "\"modules\"");
    if (!p) return;
    obj = strchr(p, '[');
    if (!obj) return;

    while (g_pipe_n < 16 && (obj = strstr(obj, "\"module\":")) != NULL) {
        const char *end = strchr(obj, '}');
        SigCard *c;
        char mod[32], msg[120], skipped[8];
        int len, is_skip, is_bt;

        if (!end) break;
        len = (int)(end - obj + 1);
        if (len >= (int)sizeof(block)) len = (int)sizeof(block) - 1;
        memcpy(block, obj, (size_t)len);
        block[len] = 0;

        mod[0] = msg[0] = skipped[0] = 0;
        {
            char pat[48];
            const char *q, *r;
            wsprintfA(pat, "\"module\":\"");
            q = strstr(block, pat);
            if (q) {
                q += strlen(pat);
                r = strchr(q, '"');
                if (r && (int)(r - q) < 32) {
                    memcpy(mod, q, (size_t)(r - q));
                    mod[r - q] = 0;
                }
            }
        }
        {
            char pat[48];
            const char *q, *r;
            wsprintfA(pat, "\"message\":\"");
            q = strstr(block, pat);
            if (q) {
                q += strlen(pat);
                r = strchr(q, '"');
                if (r && (int)(r - q) < 120) {
                    memcpy(msg, q, (size_t)(r - q));
                    msg[r - q] = 0;
                }
            }
        }
        is_skip = strstr(block, "\"skipped\":true") != NULL;
        is_bt = strstr(mod, "backtest") != NULL || strstr(mod, "pwr") != NULL;
        if (is_skip || !mod[0]) { obj = end + 1; continue; }

        c = &g_pipe[g_pipe_n];
        lstrcpynA(c->id, mod, 24);
        if (is_bt) {
            if (strstr(msg, "FAIL"))
                lstrcpyA(c->stage, "respinto");
            else if (strstr(msg, "PASS"))
                lstrcpyA(c->stage, "promosso");
            else
                lstrcpyA(c->stage, "backtest");
        } else if (strstr(mod, "harvest") || strstr(mod, "om_"))
            lstrcpyA(c->stage, "raccolta");
        else
            lstrcpyA(c->stage, "ipotesi");
        lstrcpynA(c->block, msg, 96);
        lstrcpyA(c->age, "today");
        g_pipe_n++;
        obj = end + 1;
    }
}

void sig_reload(void) {
    parse_modules_index();
}

void sig_paint(HDC dc, const RECT *rc) {
    RECT r = *rc, prom, pipe, hist;
    int y, lh = 13, i;
    wchar_t line[220];
    int col, col_w;

    if (g_pipe_n == 0) sig_reload();

    prom = r;
    prom.bottom = r.top + lh * 4 + 16;
    ui_frame(dc, &prom, L"PROMOSSI");
    {
        RECT pin = ui_panel_body(&prom);
        int y = pin.top;
        wsprintfW(line, L"%d promossi | ultimo reject: %hs | prossimo: %hs",
                  g_promoted, g_last_reject, g_next_cand);
        ui_label_rect(dc, &pin, line, g_promoted ? CLR_UP : CLR_DIM, fSm);
        y += lh + 2;
        SetTextColor(dc, CLR_OFF);
        SelectObject(dc, fSm);
        TextOutW(dc, pin.left, y,
                 L"POV: il vuoto e voluto — nessun segnale passa il LAB finche cond IC non regge",
                 -1);
    }

    pipe = r;
    pipe.top = prom.bottom + 8;
    pipe.bottom = r.bottom - lh * 10;
    ui_frame(dc, &pipe, L"PIPELINE  ipotesi -> dati -> backtest -> verdict");
    {
        static const wchar_t *COLS[4] = { L"IPOTESI", L"DATI", L"BACKTEST", L"VERDICT" };
        RECT inner = ui_panel_body(&pipe);
        int col_w, col, card_y[4];
        col_w = (inner.right - inner.left) / 4;
        y = inner.top;
        for (i = 0; i < 4; i++) {
            SetTextColor(dc, CLR_OFF);
            SelectObject(dc, fSm);
            TextOutW(dc, inner.left + i * col_w, y, COLS[i], lstrlenW(COLS[i]));
            card_y[i] = y + lh + 4;
        }
        y += lh + 4;
        for (i = 0; i < g_pipe_n; i++) {
            const SigCard *c = &g_pipe[i];
            wchar_t msgw[96], idw[32];
            COLORREF fg = CLR_DIM;
            RECT col_rc;
            if (!strcmp(c->stage, "ipotesi")) col = 0;
            else if (!strcmp(c->stage, "raccolta")) col = 1;
            else if (!strcmp(c->stage, "backtest")) col = 2;
            else col = 3;
            if (card_y[col] + lh * 2 > inner.bottom) continue;
            if (!strcmp(c->stage, "promosso")) fg = CLR_UP;
            else if (!strcmp(c->stage, "respinto")) fg = CLR_DN;
            else fg = CLR_TXT;
            col_rc.left = inner.left + col * col_w;
            col_rc.right = col_rc.left + col_w - 4;
            col_rc.top = card_y[col];
            col_rc.bottom = col_rc.top + lh * 2;
            FillRect(dc, &col_rc, bBand);
            MultiByteToWideChar(CP_UTF8, 0, c->id, -1, idw, 32);
            MultiByteToWideChar(CP_UTF8, 0, c->block, -1, msgw, 96);
            SetTextColor(dc, fg);
            TextOutW(dc, col_rc.left + 2, col_rc.top, idw, lstrlenW(idw));
            SetTextColor(dc, CLR_OFF);
            TextOutW(dc, col_rc.left + 2, col_rc.top + lh, msgw,
                     (int)wcslen(msgw) > 22 ? 22 : (int)wcslen(msgw));
            card_y[col] += lh * 2 + 4;
        }
    }

    hist = r;
    hist.top = pipe.bottom + 8;
    ui_frame(dc, &hist, L"STORICO ALERT  ex-post");
    {
        RECT hin = ui_panel_body(&hist);
        y = hin.top;
        SetTextColor(dc, CLR_OFF);
        SelectObject(dc, fSm);
        if (spine_live_count() > 0) {
            for (i = 0; i < spine_live_count() && i < 6 && y + lh <= hin.bottom; i++) {
                const SpineLive *lv = spine_live_get(i);
                wchar_t msgw[100];
                MultiByteToWideChar(CP_UTF8, 0, lv->msg, -1, msgw, 100);
                wsprintfW(line, L"%hs | %ls | ex-post: pending", lv->id, msgw);
                SetTextColor(dc, lv->alert ? CLR_DN : CLR_DIM);
                TextOutW(dc, hin.left, y, line, lstrlenW(line));
                y += lh;
            }
        } else {
            int wn = modules_wind_delta_count();
            for (i = 0; i < SIG_HIST && y + lh <= hin.bottom; i++) {
                if (wn > 0) {
                    const WindDeltaRow *w = modules_wind_delta_get(i % wn);
                    wsprintfW(line, L"PWR-01-v2 %hs d_norm=%.2f | spread ex-post: log pending",
                              w->desk, w->delta_norm);
                } else {
                    wsprintfW(line, L"-- alert log vuoto — emetti da MET wind-delta");
                }
                TextOutW(dc, hin.left, y, line, lstrlenW(line));
                y += lh;
            }
        }
    }
}
