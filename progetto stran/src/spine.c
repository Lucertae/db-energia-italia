#include "spine.h"
#include "modules.h"
#include "chokepoints.h"
#include <stdio.h>
#include <string.h>

#define SPINE_MAX_SERIES  64
#define SPINE_MAX_SIGNALS 16
#define SPINE_MAX_LIVE    8
#define SPINE_BUF         (128 * 1024)

static SpineRow g_rows[SPINE_MAX_SERIES];
static int g_row_n;
static SpineSignal g_sigs[SPINE_MAX_SIGNALS];
static int g_sig_n;
static SpineLive g_live[SPINE_MAX_LIVE];
static int g_live_n;
static int g_ok, g_stale, g_missing;
static char g_brief[512];

static const char *json_str(const char *obj, const char *key, char *out, int cap) {
    char pat[48];
    const char *p, *q;

    if (!obj || !key || !out || cap < 2) return NULL;
    wsprintfA(pat, "\"%s\":\"", key);
    p = strstr(obj, pat);
    if (!p) return NULL;
    p += strlen(pat);
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
    return atoi(p + strlen(pat));
}

static void parse_summary(const char *json) {
    const char *p;

    g_ok = g_stale = g_missing = 0;
    p = strstr(json, "\"summary\"");
    if (!p) return;
    g_ok = json_int(p, "ok", 0);
    g_stale = json_int(p, "stale", 0);
    g_missing = json_int(p, "missing", 0);
}

static void parse_series_array(const char *json) {
    const char *p, *obj;
    char block[512];

    g_row_n = 0;
    p = strstr(json, "\"series\"");
    if (!p) return;
    p = strchr(p, '[');
    if (!p) return;
    obj = p;
    while (g_row_n < SPINE_MAX_SERIES && (obj = strstr(obj, "\"id\":")) != NULL) {
        const char *end = strchr(obj, '}');
        int len;

        if (!end || (p && obj > strstr(json, "\"pipelines\""))) break;
        len = (int)(end - obj + 1);
        if (len >= (int)sizeof(block)) len = (int)sizeof(block) - 1;
        memcpy(block, obj, (size_t)len);
        block[len] = 0;
        json_str(block, "id", g_rows[g_row_n].id, 16);
        json_str(block, "status", g_rows[g_row_n].status, 20);
        json_str(block, "tier", g_rows[g_row_n].tier, 12);
        g_rows[g_row_n].age_h = json_int(block, "age_h", -1);
        g_rows[g_row_n].max_age_h = json_int(block, "max_age_h", 48);
        g_row_n++;
        obj = end + 1;
    }
}

static void parse_live_array(const char *json) {
    const char *p, *obj;
    char block[512];

    g_live_n = 0;
    p = strstr(json, "\"signals_live\"");
    if (!p) return;
    obj = strchr(p, '[');
    if (!obj) return;
    while (g_live_n < SPINE_MAX_LIVE && (obj = strstr(obj, "\"id\":")) != NULL) {
        const char *end = strchr(obj, '}');
        int len;
        char alert_str[8];

        if (!end) break;
        len = (int)(end - obj + 1);
        if (len >= (int)sizeof(block)) len = (int)sizeof(block) - 1;
        memcpy(block, obj, (size_t)len);
        block[len] = 0;
        json_str(block, "id", g_live[g_live_n].id, 16);
        json_str(block, "msg", g_live[g_live_n].msg, 96);
        if (json_str(block, "alert", alert_str, 8) && (alert_str[0] == 't' || alert_str[0] == 'T'))
            g_live[g_live_n].alert = 1;
        else
            g_live[g_live_n].alert = strstr(block, "\"alert\":true") != NULL ? 1 : 0;
        g_live_n++;
        obj = end + 1;
    }
}

static void parse_signals_file(void) {
    wchar_t path[MAX_PATH];
    FILE *f;
    static char buf[16384];
    size_t n;
    const char *p, *obj;
    char block[512];

    g_sig_n = 0;
    wsprintfW(path, L"config\\signals.json");
    f = _wfopen(path, L"r");
    if (!f) return;
    n = fread(buf, 1, sizeof(buf) - 1, f);
    fclose(f);
    buf[n] = 0;

    p = strstr(buf, "\"signals\"");
    if (!p) return;
    obj = strchr(p, '[');
    if (!obj) return;
    while (g_sig_n < SPINE_MAX_SIGNALS && (obj = strstr(obj, "\"id\":")) != NULL) {
        const char *end = strchr(obj, '}');
        int len;
        char st[16];

        if (!end) break;
        len = (int)(end - obj + 1);
        if (len >= (int)sizeof(block)) len = (int)sizeof(block) - 1;
        memcpy(block, obj, (size_t)len);
        block[len] = 0;
        json_str(block, "id", g_sigs[g_sig_n].id, 16);
        json_str(block, "status", st, 16);
        json_str(block, "title", g_sigs[g_sig_n].title, 120);
        lstrcpynA(g_sigs[g_sig_n].status, st, 16);
        if (lstrcmpiA(st, "active") == 0 || lstrcmpiA(st, "watch") == 0)
            g_sig_n++;
        else
            g_sigs[g_sig_n].id[0] = 0;
        obj = end + 1;
    }
}

static BOOL spawn_python_bg(const wchar_t *script) {
    wchar_t cmd[640];
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;

    wsprintfW(cmd, L"cmd.exe /c python \"%s\"", script);
    memset(&si, 0, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    memset(&pi, 0, sizeof(pi));
    if (!CreateProcessW(NULL, cmd, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi))
        return FALSE;
    CloseHandle(pi.hThread);
    CloseHandle(pi.hProcess);
    return TRUE;
}

void spine_init(void) {
    g_brief[0] = 0;
    spine_reload();
}

void spine_spawn_build(void) {
    CreateDirectoryW(L"cache\\spine", NULL);
    spawn_python_bg(L"scripts\\spine_build.py");
}

int spine_reload(void) {
    wchar_t path[MAX_PATH];
    FILE *f;
    static char buf[SPINE_BUF];
    size_t n;

    g_row_n = 0;
    g_live_n = 0;
    g_ok = g_stale = g_missing = 0;
    g_brief[0] = 0;

    wsprintfW(path, L"cache\\spine\\status.json");
    f = _wfopen(path, L"r");
    if (f) {
        n = fread(buf, 1, sizeof(buf) - 1, f);
        fclose(f);
        buf[n] = 0;
        parse_summary(buf);
        parse_series_array(buf);
        parse_live_array(buf);
        json_str(buf, "brief", g_brief, (int)sizeof(g_brief));
    }

    parse_signals_file();
    modules_reload();
    return g_row_n;
}

void spine_get_summary(int *ok, int *stale, int *missing) {
    if (ok) *ok = g_ok;
    if (stale) *stale = g_stale;
    if (missing) *missing = g_missing;
}

const char *spine_brief(void) { return g_brief; }

int spine_series_count(void) { return g_row_n; }

const SpineRow *spine_series_get(int i) {
    if (i < 0 || i >= g_row_n) return NULL;
    return &g_rows[i];
}

int spine_signal_count(void) { return g_sig_n; }

const SpineSignal *spine_signal_get(int i) {
    if (i < 0 || i >= g_sig_n) return NULL;
    return &g_sigs[i];
}

int spine_live_count(void) { return g_live_n; }

const SpineLive *spine_live_get(int i) {
    if (i < 0 || i >= g_live_n) return NULL;
    return &g_live[i];
}

static COLORREF spine_status_color(const char *st) {
    if (!st) return CLR_DIM;
    if (lstrcmpiA(st, "ok") == 0) return CLR_UP;
    if (lstrcmpiA(st, "stale") == 0) return RGB(255, 180, 80);
    if (lstrcmpiA(st, "missing") == 0) return CLR_DN;
    return CLR_DIM;
}

void spine_paint_ops(HDC dc, RECT *body, int *y) {
    wchar_t line[220];
    wchar_t briefw[256];
    wchar_t cpbrief[160];
    int i, yy = *y;
    const int lh = 13;

    if (yy + lh > body->bottom) return;
    wsprintfW(line, L"SPINE  ok %d  stale %d  miss %d", g_ok, g_stale, g_missing);
    SetTextColor(dc, g_stale > 0 || g_missing > 0 ? RGB(255, 180, 80) : CLR_UP);
  SelectObject(dc, fLbl);
    TextOutW(dc, body->left, yy, line, lstrlenW(line));
    yy += lh + 2;

    for (i = 0; i < g_row_n && yy + lh <= body->bottom; i++) {
        const SpineRow *r = &g_rows[i];
        if (lstrcmpiA(r->tier, "critical") != 0) continue;
        if (lstrcmpiA(r->status, "ok") == 0) continue;
        wsprintfW(line, L"  ! %hs %hs %dh", r->id, r->status, r->age_h);
        SetTextColor(dc, spine_status_color(r->status));
        TextOutW(dc, body->left, yy, line, lstrlenW(line));
        yy += lh;
    }

    if (g_brief[0] && yy + lh <= body->bottom) {
        MultiByteToWideChar(CP_UTF8, 0, g_brief, -1, briefw, 256);
        SetTextColor(dc, CLR_DIM);
        SelectObject(dc, fSm);
        TextOutW(dc, body->left, yy, briefw, lstrlenW(briefw));
        yy += lh + 2;
    }

    chokepoints_brief(cpbrief, 160);
    if (cpbrief[0] && yy + lh <= body->bottom) {
        SetTextColor(dc, CLR_ACC);
        TextOutW(dc, body->left, yy, cpbrief, lstrlenW(cpbrief));
        yy += lh + 2;
    }

    for (i = 0; i < g_live_n && yy + lh <= body->bottom; i++) {
        const SpineLive *lv = &g_live[i];
        wchar_t msgw[120];
        MultiByteToWideChar(CP_UTF8, 0, lv->msg, -1, msgw, 120);
        wsprintfW(line, L"  %s %ls", lv->alert ? L"!!" : L"--", msgw);
        SetTextColor(dc, lv->alert ? CLR_DN : CLR_DIM);
        SelectObject(dc, fSm);
        TextOutW(dc, body->left, yy, line, lstrlenW(line));
        yy += lh;
    }

    for (i = 0; i < g_sig_n && yy + lh <= body->bottom; i++) {
        const SpineSignal *s = &g_sigs[i];
        wchar_t titlew[100];
        MultiByteToWideChar(CP_UTF8, 0, s->title, -1, titlew, 100);
        wsprintfW(line, L"  SIG %hs [%hs] %.60ls", s->id, s->status, titlew);
        SetTextColor(dc, lstrcmpiA(s->status, "active") == 0 ? CLR_ACC : CLR_DIM);
        TextOutW(dc, body->left, yy, line, lstrlenW(line));
        yy += lh;
    }

    *y = yy;
}
