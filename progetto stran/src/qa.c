#include "qa.h"
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define QA_MAX 32

typedef struct {
    char id[8];
    char status[12];
    int  age_h;
    int  gaps;
    char tier[12];
    int  n;
    int  score;
} QaRow;

static QaRow g_qa[QA_MAX];
static int g_qa_n;
static char g_harvest[220];

static int qa_row_cmp(const void *a, const void *b) {
    const QaRow *x = (const QaRow *)a;
    const QaRow *y = (const QaRow *)b;
    if (x->score > y->score) return -1;
    if (x->score < y->score) return 1;
    return y->gaps - x->gaps;
}

static int json_int_field(const char *obj, const char *key) {
    char pat[48];
    const char *p;
    wsprintfA(pat, "\"%s\":", key);
    p = strstr(obj, pat);
    if (!p) return 0;
    return atoi(p + strlen(pat));
}

static void build_harvest_line(void) {
    static char buf[8192];
    FILE *f;
    size_t n;
    int entsoe = 0, om = 0, id = 0, aep = 0, pde_n = 0, pit_n = 0;
    int i;

    g_harvest[0] = 0;
    f = _wfopen(L"cache\\spine\\modules\\entsoe_hourly_harvest.json", L"r");
    if (f) {
        n = fread(buf, 1, sizeof(buf) - 1, f);
        fclose(f);
        buf[n] = 0;
        entsoe = json_int_field(buf, "zones_ok");
    }
    f = _wfopen(L"cache\\spine\\modules\\om_hourly_harvest.json", L"r");
    if (f) {
        n = fread(buf, 1, sizeof(buf) - 1, f);
        fclose(f);
        buf[n] = 0;
        om = json_int_field(buf, "grid_points_ok");
    }
    f = _wfopen(L"cache\\spine\\modules\\epex_id_harvest.json", L"r");
    if (f) {
        n = fread(buf, 1, sizeof(buf) - 1, f);
        fclose(f);
        buf[n] = 0;
        id = json_int_field(buf, "desks_ok");
    }
    f = _wfopen(L"cache\\spine\\modules\\netztransparenz_aep_harvest.json", L"r");
    if (f) {
        n = fread(buf, 1, sizeof(buf) - 1, f);
        fclose(f);
        buf[n] = 0;
        aep = json_int_field(buf, "desks_ok");
    }
    for (i = 0; i < g_qa_n; i++) {
        if (lstrcmpiA(g_qa[i].id, "PDE") == 0) pde_n = g_qa[i].n;
        if (lstrcmpiA(g_qa[i].id, "PIT") == 0) pit_n = g_qa[i].n;
    }
    wsprintfA(g_harvest,
              "ENTSO-E hourly %d desks | OM grid %d pts | PDE n=%d PIT n=%d | ID %d | AEP %d",
              entsoe, om, pde_n, pit_n, id, aep);
}

static void parse_qa(const char *json) {
    const char *p, *obj;
    char block[640];
    g_qa_n = 0;
    p = strstr(json, "\"reports\"");
    if (!p) return;
    obj = strchr(p, '[');
    if (!obj) return;
    while (g_qa_n < QA_MAX && (obj = strstr(obj, "\"id\":")) != NULL) {
        const char *end = strchr(obj, '}');
        int len;
        QaRow *r;
        if (!end) break;
        len = (int)(end - obj + 1);
        if (len >= (int)sizeof(block)) len = (int)sizeof(block) - 1;
        memcpy(block, obj, (size_t)len);
        block[len] = 0;
        r = &g_qa[g_qa_n];
        memset(r, 0, sizeof(*r));
        {
            char pat[48];
            const char *q, *s;
            wsprintfA(pat, "\"id\":\"");
            q = strstr(block, pat);
            if (q) { q += 8; s = strchr(q, '"'); if (s) { int n = (int)(s-q); if (n>7)n=7; memcpy(r->id,q,n); r->id[n]=0; } }
        }
        {
            char pat[48];
            const char *q, *s;
            wsprintfA(pat, "\"status\":\"");
            q = strstr(block, pat);
            if (q) { q += 10; s = strchr(q, '"'); if (s) { int n = (int)(s-q); if (n>11)n=11; memcpy(r->status,q,n); r->status[n]=0; } }
        }
        {
            char pat[48];
            const char *q, *s;
            wsprintfA(pat, "\"tier\":\"");
            q = strstr(block, pat);
            if (q) { q += 8; s = strchr(q, '"'); if (s) { int n = (int)(s-q); if (n>11)n=11; memcpy(r->tier,q,n); r->tier[n]=0; } }
        }
        r->age_h = json_int_field(block, "age_h");
        r->gaps = json_int_field(block, "gaps_gt5d");
        r->n = json_int_field(block, "n");
        r->score = 0;
        if (lstrcmpiA(r->status, "stale") == 0) r->score += 100;
        else if (lstrcmpiA(r->status, "ok") != 0) r->score += 80;
        if (r->gaps > 10) r->score += 40;
        if (r->age_h > 168) r->score += 20;
        if (lstrcmpiA(r->tier, "critical") == 0) r->score += 10;
        g_qa_n++;
        obj = end + 1;
    }
    if (g_qa_n > 1)
        qsort(g_qa, (size_t)g_qa_n, sizeof(g_qa[0]), qa_row_cmp);
}

void qa_reload(void) {
    static char buf[65536];
    FILE *f;
    size_t n;
    g_qa_n = 0;
    g_harvest[0] = 0;
    f = _wfopen(L"cache\\spine\\modules\\qa_series.json", L"r");
    if (!f) return;
    n = fread(buf, 1, sizeof(buf) - 1, f);
    fclose(f);
    buf[n] = 0;
    parse_qa(buf);
    build_harvest_line();
}

void qa_paint_panel(HDC dc, const RECT *rc) {
    int y, lh = 13, i;
    wchar_t line[140];
    if (g_qa_n == 0) qa_reload();
    ui_subheading(dc, &(RECT){ rc->left, rc->top, rc->right, rc->top + 12 }, L"QA / HARVEST");
    y = rc->top + 14;
    {
        wchar_t hw[220];
        MultiByteToWideChar(CP_UTF8, 0, g_harvest, -1, hw, 220);
        SetTextColor(dc, (wcsstr(hw, L"ID 0") || wcsstr(hw, L"AEP 0")) ? CLR_DN : CLR_DIM);
        SelectObject(dc, fSm);
        TextOutW(dc, rc->left, y, hw, lstrlenW(hw));
        y += lh + 4;
    }
    ui_subheading(dc, &(RECT){ rc->left, y, rc->right, y + 12 }, L"serie stale/gap (critici primi)");
    y += 14;
    for (i = 0; i < g_qa_n && y + lh <= rc->bottom; i++) {
        const QaRow *r = &g_qa[i];
        COLORREF fg = CLR_DIM;
        if (lstrcmpiA(r->status, "stale") == 0) fg = RGB(255, 180, 80);
        else if (lstrcmpiA(r->status, "ok") != 0) fg = CLR_DN;
        else if (r->gaps > 5) fg = RGB(255, 180, 80);
        wsprintfW(line, L"%hs %-6hs n=%4d age %4dh gap %3d  %hs",
                  r->id, r->status, r->n, r->age_h, r->gaps, r->tier);
        SetTextColor(dc, fg);
        TextOutW(dc, rc->left, y, line, lstrlenW(line));
        ui_stale_dot(dc, rc->right - 10, y + 3, r->age_h);
        y += lh;
    }
    if (y + lh <= rc->bottom) {
        SetTextColor(dc, CLR_OFF);
        TextOutW(dc, rc->left, y, L"ID 0 / AEP 0 in rosso finche cache vuota", -1);
    }
}
