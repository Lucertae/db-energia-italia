#include "chart.h"
#include "corr.h"
#include "fin.h"
#include "production.h"
#include <math.h>
#include <stdio.h>

static void norm_rect(RECT *r, int pad) {
    r->left += pad;
    r->top += pad;
    r->right -= pad;
    r->bottom -= pad;
}

void chart_sparkline(HDC dc, const RECT *rc, const DataSeries *s, COLORREF line, COLORREF live_c) {    RECT r = *rc;
    POINT pts[SER_POINTS];
    HPEN pen, grid_pen, live_pen, old_pen;
    HBRUSH dot;
    wchar_t lo_s[16], hi_s[16];
    int i, w, h, n, gy;
    float mn, mx, span;
    int px, py;

    if (!s || s->n < 2 || r.right <= r.left + 8 || r.bottom <= r.top + 8) return;
    norm_rect(&r, 3);
    w = r.right - r.left;
    h = r.bottom - r.top;
    n = s->n;
    mn = s->min_h;
    mx = s->max_h;
    span = mx - mn;
    if (span < 1e-6f) span = mx * 0.01f + 1e-6f;

    grid_pen = CreatePen(PS_SOLID, 1, CLR_GRID);
    old_pen = (HPEN)SelectObject(dc, grid_pen);
    for (i = 1; i <= 2; i++) {
        gy = r.bottom - (h * i) / 3;
        MoveToEx(dc, r.left, gy, NULL);
        LineTo(dc, r.right, gy);
    }
    SelectObject(dc, old_pen);
    DeleteObject(grid_pen);

    ui_fmt_wdouble(lo_s, 16, mn, mn >= 100.0f ? 0 : 1);
    ui_fmt_wdouble(hi_s, 16, mx, mx >= 100.0f ? 0 : 1);
    SetTextColor(dc, CLR_OFF);
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    TextOutW(dc, r.left, r.bottom - 10, lo_s, lstrlenW(lo_s));
    TextOutW(dc, r.right - 28, r.top, hi_s, lstrlenW(hi_s));

    for (i = 0; i < n; i++) {
        pts[i].x = r.left + (i * w) / (n - 1);
        pts[i].y = r.bottom - (int)((s->val[i] - mn) / span * (h - 1));
    }

    pen = CreatePen(PS_SOLID, 1, line);
    SelectObject(dc, pen);
    Polyline(dc, pts, n);
    SelectObject(dc, old_pen);
    DeleteObject(pen);

    if (s->live > 0.0f) {
        px = r.right;
        py = r.bottom - (int)((s->live - mn) / span * (h - 1));
        live_pen = CreatePen(PS_SOLID, 2, live_c);
        dot = CreateSolidBrush(live_c);
        SelectObject(dc, live_pen);
        SelectObject(dc, dot);
        Ellipse(dc, px - 3, py - 3, px + 3, py + 3);
        SelectObject(dc, GetStockObject(BLACK_PEN));
        SelectObject(dc, GetStockObject(BLACK_BRUSH));
        DeleteObject(live_pen);
        DeleteObject(dot);
    }
}

static int cell_decimals(const DataSeries *s) {
    if (!s) return 2;
    if (s->kind == SER_RATE) return 2;
    if (s->kind == SER_FX && series_last(s) > 50.0f) return 2;
    if (series_last(s) >= 10.0f) return 1;
    return 2;
}

void chart_series_cell(HDC dc, const RECT *rc, const DataSeries *s) {
    RECT band = *rc;
    RECT plot = *rc;
    RECT pct_rc;
    wchar_t cap[40];
    wchar_t num[20];
    float last, prev, pct;
    int dec, back;

    if (!s || s->n < 2) return;
    band.bottom = band.top + 14;
    plot.top = band.bottom + 2;
    FillRect(dc, &band, bBand);
    dec = cell_decimals(s);
    last = series_last(s);
    ui_fmt_wdouble(num, (int)(sizeof(num) / sizeof(num[0])), last, dec);
    wsprintfW(cap, L"%s  %s", s->label, num);
    ui_label_rect(dc, &band, cap, CLR_TXT, fSm);

    back = s->n > 22 ? 22 : s->n - 1;
    prev = s->val[s->n - 1 - back];
    if (prev > 0.0f) {
        wchar_t pct_s[16], badge[20];
        pct = (last - prev) / prev * 100.0f;
        ui_fmt_wdouble(pct_s, 16, pct >= 0.0f ? pct : -pct, 1);
        wsprintfW(badge, L"%s%s%%", pct >= 0.0f ? L"+" : L"-", pct_s);
        pct_rc = band;
        pct_rc.right -= 2;
        SetTextColor(dc, pct >= 0.0f ? CLR_UP : CLR_DN);
        SetBkMode(dc, TRANSPARENT);
        SelectObject(dc, fSm);
        DrawTextW(dc, badge, -1, &pct_rc, DT_RIGHT | DT_SINGLELINE | DT_NOPREFIX);
    }
    chart_sparkline(dc, &plot, s, CLR_LINE, CLR_ACC);
}

void chart_football(HDC dc, const RECT *rc, const DataSeries *s, const wchar_t *title) {    RECT r = *rc, tr, br;
    float mn, mx, cur, span;
    int x0, x1, xc, y;
    HPEN pen, old_pen;
    HBRUSH dot;
    wchar_t buf[48];

    if (!s || s->n < 2) return;
    mn = s->min_h;
    mx = s->max_h;
    cur = series_last(s);
    span = mx - mn;
    if (span < 1e-6f) span = 1.0f;

    tr = r;
    tr.bottom = tr.top + 14;
    ui_subheading(dc, &tr, title);

    br = r;
    br.top = tr.bottom + 2;
    y = (br.top + br.bottom) / 2;
    x0 = br.left + 36;
    x1 = br.right - 4;
    if (x1 <= x0 + 8) return;

    pen = CreatePen(PS_SOLID, 1, CLR_DIM);
    old_pen = (HPEN)SelectObject(dc, pen);
    MoveToEx(dc, x0, y, NULL);
    LineTo(dc, x1, y);
    SelectObject(dc, old_pen);
    DeleteObject(pen);

    xc = x0 + (int)((cur - mn) / span * (x1 - x0));
    dot = CreateSolidBrush(CLR_ACC);
    SelectObject(dc, dot);
    Ellipse(dc, xc - 4, y - 4, xc + 4, y + 4);
    SelectObject(dc, GetStockObject(BLACK_BRUSH));
    DeleteObject(dot);

    ui_fmt_wdouble(buf, 48, mn, 2);
    SetTextColor(dc, CLR_OFF);
    TextOutW(dc, br.left, y - 6, buf, lstrlenW(buf));
    ui_fmt_wdouble(buf, 48, mx, 2);
    TextOutW(dc, x1 - 28, y - 6, buf, lstrlenW(buf));
}

typedef struct {
    const char *id;
    int         x, y;
} NetNode;

static void draw_node_label(HDC dc, int x, int y, const wchar_t *lbl, int hub) {
    RECT tr = { x - 18, y - 8, x + 18, y + 8 };
    SetBkMode(dc, TRANSPARENT);
    SetTextColor(dc, hub ? CLR_BG : CLR_TXT);
    SelectObject(dc, fSm);
    DrawTextW(dc, (wchar_t *)lbl, -1, &tr, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
}

#define NET_N 9

char g_fx_hub[4] = "EUR";

static const char *NET_IDS[NET_N] = {
    "EUR", "USD", "JPY", "GBP", "BRL", "ZAR", "INR", "CNY", "MXN"
};

static struct {
    char id[4];
    RECT rc;
} g_net_hit[NET_N];
static int g_net_hit_n = 0;

int chart_fx_network_hit(POINT pt, char *out_id) {
    int i;

    for (i = 0; i < g_net_hit_n; i++) {
        if (PtInRect(&g_net_hit[i].rc, pt)) {
            if (out_id) lstrcpyA(out_id, g_net_hit[i].id);
            return 1;
        }
    }
    return 0;
}

/* tutte le serie in store sono EUR/X; EUR vale 1 per definizione */
static int net_leg(const SeriesStore *st, const char *id, float *last, float *prev) {
    DataSeries *d;

    if (id[0] == 'E' && id[1] == 'U' && id[2] == 'R') {
        *last = 1.0f;
        *prev = 1.0f;
        return 1;
    }
    d = series_get((SeriesStore *)st, id);
    if (!d || d->n < 2) return 0;
    *last = series_last(d);
    *prev = d->val[d->n - 2];
    return *last > 0.0f && *prev > 0.0f;
}

/* freccia piena con punta a distanza tip_off dal centro del nodo target */
static void net_arrow_head(HDC dc, int xa, int ya, int xb, int yb,
                           int tip_off, int size, COLORREF c) {
    double dx = xb - xa, dy = yb - ya, len, ux, uy, px, py, tx, ty;
    POINT tri[3];
    HBRUSH br, old_br;
    HPEN pen, old_pen;

    len = sqrt(dx * dx + dy * dy);
    if (len < 1.0) return;
    ux = dx / len;
    uy = dy / len;
    px = -uy;
    py = ux;
    tx = xb - ux * tip_off;
    ty = yb - uy * tip_off;

    tri[0].x = (LONG)(tx + 0.5);
    tri[0].y = (LONG)(ty + 0.5);
    tri[1].x = (LONG)(tx - ux * size + px * size * 0.55 + 0.5);
    tri[1].y = (LONG)(ty - uy * size + py * size * 0.55 + 0.5);
    tri[2].x = (LONG)(tx - ux * size - px * size * 0.55 + 0.5);
    tri[2].y = (LONG)(ty - uy * size - py * size * 0.55 + 0.5);

    br = CreateSolidBrush(c);
    pen = CreatePen(PS_SOLID, 1, c);
    old_br = (HBRUSH)SelectObject(dc, br);
    old_pen = (HPEN)SelectObject(dc, pen);
    Polygon(dc, tri, 3);
    SelectObject(dc, old_br);
    SelectObject(dc, old_pen);
    DeleteObject(br);
    DeleteObject(pen);
}

/*
 * chg = variazione cross j/i (ultimo vs penultimo giorno).
 * chg > 0 -> j si rafforza -> freccia verso j; chg < 0 -> verso i.
 * verde = rafforza, rosso = indebolisce (intensita = spessore).
 */
static void net_edge_style(float chg, int have, int is_focus,
                           COLORREF *c, int *w, int *arrow) {
    float m = chg >= 0.0f ? chg : -chg;

    *arrow = 0;
    if (!have || m < 0.0001f) {
        *c = CLR_GRID;
        *w = 1;
        return;
    }
    *c = chg >= 0.0f ? CLR_UP : CLR_DN;
    *arrow = 1;
    if (m >= 0.010f)
        *w = is_focus ? 4 : 2;
    else if (m >= 0.004f)
        *w = is_focus ? 3 : 2;
    else
        *w = is_focus ? 2 : 1;
}

static void net_draw_edge(HDC dc, const NetNode *ni, const NetNode *nj,
                          float chg, int have, int is_focus, int rr_i, int rr_j) {
    const NetNode *from, *to;
    COLORREF c;
    int tip_off, w, arrow;
    HPEN pen, old_pen;

    net_edge_style(chg, have, is_focus, &c, &w, &arrow);

    if (chg >= 0.0f) {
        from = ni;
        to = nj;
        tip_off = rr_j + 3;
    } else {
        from = nj;
        to = ni;
        tip_off = rr_i + 3;
    }

    pen = CreatePen(PS_SOLID, w, c);
    old_pen = (HPEN)SelectObject(dc, pen);
    MoveToEx(dc, from->x, from->y, NULL);
    LineTo(dc, to->x, to->y);
    SelectObject(dc, old_pen);
    DeleteObject(pen);

    if (arrow)
        net_arrow_head(dc, from->x, from->y, to->x, to->y,
                       tip_off, is_focus ? 10 : 6, c);
}

#define NET_LBL_MAX 40

typedef struct {
    wchar_t  txt[40];
    int      x, y, hw, hh, prio;
    COLORREF color;
} NetLbl;

typedef struct {
    NetLbl  lbl[NET_LBL_MAX];
    RECT    placed[NET_LBL_MAX];
    int     n;
} NetLblBuf;

static void net_lbl_reset(NetLblBuf *b) {
    b->n = 0;
}

static void net_lbl_rect(const NetLbl *l, RECT *rc) {
    rc->left = l->x - l->hw;
    rc->right = l->x + l->hw;
    rc->top = l->y - l->hh;
    rc->bottom = l->y + l->hh;
}

static int net_lbl_overlap(const RECT *a, const RECT *b, int pad) {
    return a->left < b->right + pad && a->right > b->left - pad &&
           a->top < b->bottom + pad && a->bottom > b->top - pad;
}

static int net_lbl_blocked(const NetLblBuf *b, const RECT *rc,
                           const NetNode *nodes, int n_nodes, int sel,
                           const RECT *bounds) {
    int i, rr;

    if (rc->left < bounds->left + 2 || rc->right > bounds->right - 2 ||
        rc->top < bounds->top + 2 || rc->bottom > bounds->bottom - 16)
        return 1;
    for (i = 0; i < b->n; i++) {
        if (net_lbl_overlap(rc, &b->placed[i], 4))
            return 1;
    }
    for (i = 0; i < n_nodes; i++) {
        RECT nr;

        rr = (i == sel) ? 18 : 13;
        nr.left = nodes[i].x - rr;
        nr.right = nodes[i].x + rr;
        nr.top = nodes[i].y - rr;
        nr.bottom = nodes[i].y + rr;
        if (net_lbl_overlap(rc, &nr, 4))
            return 1;
    }
    return 0;
}

static void net_lbl_add(NetLblBuf *b, const wchar_t *txt, int x0, int y0,
                        int hw, int hh, COLORREF color, int prio,
                        const NetNode *nodes, int n_nodes, int sel,
                        const RECT *bounds) {
    static const int OX[] = {
        0, 0, 12, -12, 18, -18, 0, 0, 24, -24, 8, -8, 0, 30, -30,
        14, -14, 0, 0, 20, -20, 10, -10, 0, 0, 16, -16
    };
    static const int OY[] = {
        0, -14, 14, 0, 0, -18, 18, -22, 22, -10, 10, -26, 26, 0, 0,
        -12, 12, -30, 30, -8, 8, -20, 20, -34, 34, 0, 0
    };
    NetLbl l;
    RECT rc;
    int k, ntry = (int)(sizeof(OX) / sizeof(OX[0]));

    (void)prio;
    if (b->n >= NET_LBL_MAX) return;
    lstrcpynW(l.txt, txt, (int)(sizeof(l.txt) / sizeof(l.txt[0])));
    l.hw = hw;
    l.hh = hh;
    l.color = color;

    for (k = 0; k < ntry; k++) {
        l.x = x0 + OX[k];
        l.y = y0 + OY[k];
        net_lbl_rect(&l, &rc);
        if (!net_lbl_blocked(b, &rc, nodes, n_nodes, sel, bounds)) {
            b->lbl[b->n] = l;
            b->placed[b->n] = rc;
            b->n++;
            return;
        }
    }
}

static void net_lbl_flush(HDC dc, const NetLblBuf *b) {
    int i;

    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    for (i = 0; i < b->n; i++) {
        const NetLbl *l = &b->lbl[i];
        RECT tr;

        tr.left = l->x - l->hw;
        tr.right = l->x + l->hw;
        tr.top = l->y - l->hh;
        tr.bottom = l->y + l->hh;
        SetTextColor(dc, l->color);
        DrawTextW(dc, l->txt, -1, &tr, DT_CENTER | DT_VCENTER | DT_SINGLELINE | DT_NOPREFIX);
    }
}

/* etichetta % mesh interna: anello 72-84% raggio, offset tangenziale */
static void net_ring_label_anchor(int cx, int cy, int rad, const NetNode *ni, const NetNode *nj,
                                  int pair_hash, int *x, int *y) {
    double mx, my, len, tx, ty, ring;
    int side;

    mx = (ni->x + nj->x) * 0.5 - cx;
    my = (ni->y + nj->y) * 0.5 - cy;
    len = sqrt(mx * mx + my * my);
    if (len < 1.0) {
        *x = cx;
        *y = cy;
        return;
    }
    ring = rad * (0.64 + 0.055 * (pair_hash % 4));
    tx = -my / len;
    ty = mx / len;
    side = (pair_hash & 4) ? 1 : -1;
    *x = cx + (int)(mx / len * ring + tx * side * 20.0 + 0.5);
    *y = cy + (int)(my / len * ring + ty * side * 20.0 + 0.5);
}

/* etichetta radiale oltre il nodo target (archi hub) */
static void net_hub_label_anchor(int cx, int cy, const NetNode *leaf, int leaf_i,
                                 int *x, int *y) {
    double ux, uy, len, tx, ty;
    int side;

    ux = leaf->x - cx;
    uy = leaf->y - cy;
    len = sqrt(ux * ux + uy * uy);
    if (len < 1.0) {
        *x = leaf->x;
        *y = leaf->y;
        return;
    }
    tx = -uy / len;
    ty = ux / len;
    side = (leaf_i & 1) ? 1 : -1;
    *x = leaf->x + (int)(ux / len * 32.0 + tx * side * 12.0 + 0.5);
    *y = leaf->y + (int)(uy / len * 32.0 + ty * side * 12.0 + 0.5);
}

void chart_fx_network(HDC dc, const RECT *rc, const SeriesStore *st) {
    NetNode nodes[NET_N];
    float leg_last[NET_N], leg_prev[NET_N];
    int leg_ok[NET_N];
    NetLblBuf labels;
    RECT r = *rc;
    int cx, cy, rad, i, j, sel = 0;
    HPEN old_pen;
    wchar_t lbl[8], cap[64];

    if (!st || r.right <= r.left + 40) return;
    g_net_hit_n = 0;
    net_lbl_reset(&labels);

    cx = (r.left + r.right) / 2;
    cy = (r.top + r.bottom) / 2 - 6;
    rad = (r.bottom - r.top) < (r.right - r.left)
        ? (r.bottom - r.top) / 2 - 40
        : (r.right - r.left) / 2 - 40;
    if (rad < 28) rad = 28;

    /* tutti i nodi sul cerchio, mesh completo */
    for (i = 0; i < NET_N; i++) {
        double ang = -1.5707963267948966 + i * 6.283185307179586 / NET_N;

        nodes[i].id = NET_IDS[i];
        nodes[i].x = cx + (int)(cos(ang) * rad);
        nodes[i].y = cy + (int)(sin(ang) * rad);
        leg_ok[i] = net_leg(st, NET_IDS[i], &leg_last[i], &leg_prev[i]);
        if (lstrcmpA(NET_IDS[i], g_fx_hub) == 0) sel = i;
    }

    old_pen = (HPEN)SelectObject(dc, GetStockObject(BLACK_PEN));

    /* passata 1: mesh di sfondo (28 archi) */
    for (i = 0; i < NET_N; i++) {
        for (j = i + 1; j < NET_N; j++) {
            float rate = 0.0f, chg = 0.0f;
            int have = 0;

            if (i == sel || j == sel) continue;
            if (leg_ok[i] && leg_ok[j]) {
                rate = leg_last[j] / leg_last[i];
                chg = rate / (leg_prev[j] / leg_prev[i]) - 1.0f;
                have = 1;
            }
            net_draw_edge(dc, &nodes[i], &nodes[j], chg, have, 0, 10, 10);
            (void)rate;
        }
    }

    /* passata 2: stella hub (8 archi in risalto) */
    for (j = 0; j < NET_N; j++) {
        float rate = 0.0f, chg = 0.0f;
        int have = 0;

        if (j == sel) continue;
        if (leg_ok[sel] && leg_ok[j]) {
            rate = leg_last[j] / leg_last[sel];
            chg = rate / (leg_prev[j] / leg_prev[sel]) - 1.0f;
            have = 1;
        }
        net_draw_edge(dc, &nodes[sel], &nodes[j], chg, have, 1, 14, 10);
        (void)rate;
    }
    SelectObject(dc, old_pen);

    /* etichette hub prima (priorita), poi mesh interna */
    for (j = 0; j < NET_N; j++) {
        float rate = 0.0f, chg = 0.0f;
        int have = 0, ax, ay;
        wchar_t rate_s[16], chg_s[16], txt[40];

        if (j == sel) continue;
        if (leg_ok[sel] && leg_ok[j]) {
            rate = leg_last[j] / leg_last[sel];
            chg = rate / (leg_prev[j] / leg_prev[sel]) - 1.0f;
            have = 1;
        }
        if (!have) continue;
        net_hub_label_anchor(cx, cy, &nodes[j], j, &ax, &ay);
        ui_fmt_wdouble(rate_s, 16, (double)rate, rate > 50.0f ? 1 : 3);
        ui_fmt_wdouble(chg_s, 16, chg >= 0.0f ? chg * 100.0 : -chg * 100.0, 2);
        wsprintfW(txt, L"%s %s%s%%", rate_s, chg >= 0.0f ? L"+" : L"-", chg_s);
        net_lbl_add(&labels, txt, ax, ay, 54, 7,
                    chg >= 0.0f ? CLR_UP : CLR_DN, 2,
                    nodes, NET_N, sel, &r);
    }

    for (i = 0; i < NET_N; i++) {
        for (j = i + 1; j < NET_N; j++) {
            float rate = 0.0f, chg = 0.0f;
            int have = 0, ax, ay;
            wchar_t chg_s[10], txt[16];
            float m;

            if (i == sel || j == sel) continue;
            if (leg_ok[i] && leg_ok[j]) {
                rate = leg_last[j] / leg_last[i];
                chg = rate / (leg_prev[j] / leg_prev[i]) - 1.0f;
                have = 1;
            }
            m = chg >= 0.0f ? chg : -chg;
            if (!have || m < 0.0001f) continue;
            net_ring_label_anchor(cx, cy, rad, &nodes[i], &nodes[j], i * 7 + j, &ax, &ay);
            ui_fmt_wdouble(chg_s, 10, m * 100.0, 1);
            wsprintfW(txt, L"%s%s%%", chg >= 0.0f ? L"+" : L"-", chg_s);
            net_lbl_add(&labels, txt, ax, ay, 18, 6,
                        chg >= 0.0f ? CLR_UP : CLR_DN, 1,
                        nodes, NET_N, sel, &r);
            (void)rate;
        }
    }

    net_lbl_flush(dc, &labels);

    for (i = 0; i < NET_N; i++) {
        int rr = (i == sel) ? 14 : 10;

        SelectObject(dc, i == sel ? bWhite : bGray);
        SelectObject(dc, GetStockObject(NULL_PEN));
        Ellipse(dc, nodes[i].x - rr, nodes[i].y - rr, nodes[i].x + rr, nodes[i].y + rr);
        lbl[0] = (wchar_t)nodes[i].id[0];
        lbl[1] = (wchar_t)nodes[i].id[1];
        lbl[2] = (wchar_t)nodes[i].id[2];
        lbl[3] = 0;
        draw_node_label(dc, nodes[i].x, nodes[i].y, lbl, i == sel);

        if (g_net_hit_n < NET_N) {
            g_net_hit[g_net_hit_n].id[0] = nodes[i].id[0];
            g_net_hit[g_net_hit_n].id[1] = nodes[i].id[1];
            g_net_hit[g_net_hit_n].id[2] = nodes[i].id[2];
            g_net_hit[g_net_hit_n].id[3] = 0;
            g_net_hit[g_net_hit_n].rc = (RECT){
                nodes[i].x - rr - 6, nodes[i].y - rr - 6,
                nodes[i].x + rr + 6, nodes[i].y + rr + 6
            };
            g_net_hit_n++;
        }
    }

    wsprintfW(cap, L"mesh %d valute  focus %hs  verde=rafforza  rosso=indebolisce  (click nodo)",
              NET_N, g_fx_hub);
    SetBkMode(dc, TRANSPARENT);
    SetTextColor(dc, CLR_OFF);
    SelectObject(dc, fSm);
    TextOutW(dc, r.left, r.bottom - 12, cap, lstrlenW(cap));
}

void chart_range_vol(HDC dc, const RECT *rc, const DataSeries **list, int n) {
    RECT r = *rc;
    int row_h, i, lbl_w = 62, val_w = 74, y;
    HPEN grid, old_pen;

    if (!list || n <= 0 || r.bottom <= r.top + 12) return;
    row_h = (r.bottom - r.top) / n;
    if (row_h < 13) row_h = 13;

    grid = CreatePen(PS_SOLID, 1, CLR_GRID);
    old_pen = (HPEN)SelectObject(dc, grid);

    for (i = 0; i < n; i++) {
        const DataSeries *s = list[i];
        int x0 = r.left + lbl_w, x1 = r.right - val_w, xc, y;
        float mn, mx, span, last;
        wchar_t txt[24], sd_s[12];
        HBRUSH dot;

        y = r.top + i * row_h + row_h / 2;
        if (y + 7 > r.bottom) break;
        if (!s || s->n < 10 || x1 <= x0 + 20) continue;
        mn = s->min_h;
        mx = s->max_h;
        last = series_last(s);
        span = mx - mn;
        if (span < 1e-9f) span = 1.0f;

        SetBkMode(dc, TRANSPARENT);
        SetTextColor(dc, CLR_DIM);
        SelectObject(dc, fSm);
        TextOutW(dc, r.left, y - 6, s->label, lstrlenW(s->label));

        SelectObject(dc, grid);
        MoveToEx(dc, x0, y, NULL);
        LineTo(dc, x1, y);

        xc = x0 + (int)((last - mn) / span * (x1 - x0));
        dot = CreateSolidBrush(CLR_ACC);
        SelectObject(dc, dot);
        Ellipse(dc, xc - 3, y - 3, xc + 3, y + 3);
        SelectObject(dc, GetStockObject(BLACK_BRUSH));
        DeleteObject(dot);

        {
            int crypto = (s->kind == SER_CRYPTO);
            float rv = fin_rv_ann_pct(s, 30, crypto);
            ui_fmt_wdouble(sd_s, 12, rv, 1);
            wsprintfW(txt, L"RV %s%%", sd_s);
            SetTextColor(dc, CLR_OFF);
            TextOutW(dc, x1 + 6, y - 6, txt, lstrlenW(txt));
        }
    }
    SelectObject(dc, old_pen);
    DeleteObject(grid);
}

#define EN_N 6
char g_en_hub[4] = "BRT";

static const char *EN_IDS[EN_N] = { "BRT", "WTI", "HUB", "TTF", "COA", "JKM" };

static int en_leg(const SeriesStore *st, const char *id, float *last, float *prev) {
    DataSeries *d = series_get((SeriesStore *)st, id);
    if (!d || d->n < 2) return 0;
    *last = series_last(d);
    *prev = d->val[d->n - 2];
    return *last > 0.0f && *prev > 0.0f;
}

void chart_energy_network(HDC dc, const RECT *rc, const SeriesStore *st) {
    NetNode nodes[EN_N];
    float leg_last[EN_N], leg_prev[EN_N];
    int leg_ok[EN_N];
    NetLblBuf labels;
    RECT r = *rc;
    int cx, cy, rad, i, j, sel = 0;
    HPEN old_pen;
    wchar_t lbl[8];

    if (!st || r.right <= r.left + 40) return;
    net_lbl_reset(&labels);
    cx = (r.left + r.right) / 2;
    cy = (r.top + r.bottom) / 2 - 4;
    rad = (r.bottom - r.top) < (r.right - r.left)
        ? (r.bottom - r.top) / 2 - 28 : (r.right - r.left) / 2 - 28;
    if (rad < 24) rad = 24;

    for (i = 0; i < EN_N; i++) {
        double ang = -1.5707963267948966 + i * 6.283185307179586 / EN_N;
        nodes[i].id = EN_IDS[i];
        nodes[i].x = cx + (int)(cos(ang) * rad);
        nodes[i].y = cy + (int)(sin(ang) * rad);
        leg_ok[i] = en_leg(st, EN_IDS[i], &leg_last[i], &leg_prev[i]);
        if (lstrcmpA(EN_IDS[i], g_en_hub) == 0) sel = i;
    }

    old_pen = (HPEN)SelectObject(dc, GetStockObject(BLACK_PEN));
    for (i = 0; i < EN_N; i++) {
        for (j = i + 1; j < EN_N; j++) {
            float chg = 0.0f;
            int have = 0;
            if (i == sel || j == sel) continue;
            if (leg_ok[i] && leg_ok[j]) {
                chg = (leg_last[j] / leg_last[i]) / (leg_prev[j] / leg_prev[i]) - 1.0f;
                have = 1;
            }
            net_draw_edge(dc, &nodes[i], &nodes[j], chg, have, 0, 10, 10);
        }
    }
    for (j = 0; j < EN_N; j++) {
        float chg = 0.0f;
        int have = 0;
        if (j == sel) continue;
        if (leg_ok[sel] && leg_ok[j]) {
            chg = (leg_last[j] / leg_last[sel]) / (leg_prev[j] / leg_prev[sel]) - 1.0f;
            have = 1;
        }
        net_draw_edge(dc, &nodes[sel], &nodes[j], chg, have, 1, 14, 10);
    }
    SelectObject(dc, old_pen);

    for (j = 0; j < EN_N; j++) {
        float rate = 0.0f, chg = 0.0f;
        int have = 0, ax, ay;
        wchar_t rate_s[16], chg_s[16], txt[32];
        if (j == sel) continue;
        if (leg_ok[sel] && leg_ok[j]) {
            rate = leg_last[j] / leg_last[sel];
            chg = rate / (leg_prev[j] / leg_prev[sel]) - 1.0f;
            have = 1;
        }
        if (!have) continue;
        net_hub_label_anchor(cx, cy, &nodes[j], j, &ax, &ay);
        ui_fmt_wdouble(rate_s, 16, (double)rate, rate > 50.0f ? 1 : 2);
        ui_fmt_wdouble(chg_s, 16, chg >= 0.0f ? chg * 100.0 : -chg * 100.0, 2);
        wsprintfW(txt, L"%s %s%s%%", rate_s, chg >= 0.0f ? L"+" : L"-", chg_s);
        net_lbl_add(&labels, txt, ax, ay, 48, 7,
                    chg >= 0.0f ? CLR_UP : CLR_DN, 2, nodes, EN_N, sel, &r);
    }
    net_lbl_flush(dc, &labels);

    for (i = 0; i < EN_N; i++) {
        int rr = (i == sel) ? 14 : 10;
        SelectObject(dc, i == sel ? bWhite : bGray);
        SelectObject(dc, GetStockObject(NULL_PEN));
        Ellipse(dc, nodes[i].x - rr, nodes[i].y - rr, nodes[i].x + rr, nodes[i].y + rr);
        lbl[0] = (wchar_t)nodes[i].id[0];
        lbl[1] = (wchar_t)nodes[i].id[1];
        lbl[2] = (wchar_t)nodes[i].id[2];
        lbl[3] = 0;
        draw_node_label(dc, nodes[i].x, nodes[i].y, lbl, i == sel);
    }
}

static COLORREF corr_rho_color(float rho) {
    int r, g, b;
    float t;

    if (rho >= 0.0f) {
        t = rho > 1.0f ? 1.0f : rho;
        r = (int)(40 + (220 - 40) * t);
        g = (int)(40 + (80 - 40) * t);
        b = 40;
    } else {
        t = rho < -1.0f ? 1.0f : -rho;
        r = (int)(40 + (200 - 40) * t);
        g = 40;
        b = (int)(40 + (60 - 40) * t);
    }
    return RGB(r, g, b);
}

void chart_corr_matrix(HDC dc, const RECT *rc, const SeriesStore *st,
                       const char ids[][4], int n_ids) {
    RECT r = *rc;
    int cell, i, j, x0, y0, lbl = 28;
    CorrPair cp;
    wchar_t txt[8];

    if (!st || n_ids <= 0 || r.right <= r.left + lbl + 8) return;
    {
        int cell_w = (r.right - r.left - lbl) / n_ids;
        int cell_h = (r.bottom - r.top - lbl) / n_ids;
        cell = cell_w < cell_h ? cell_w : cell_h;
    }
    if (cell < 10) cell = 10;
    if (cell > 24) cell = 24;
    y0 = r.top + lbl;

    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    for (j = 0; j < n_ids; j++) {
        SetTextColor(dc, CLR_DIM);
        txt[0] = (wchar_t)ids[j][0];
        txt[1] = (wchar_t)ids[j][1];
        txt[2] = (wchar_t)ids[j][2];
        txt[3] = 0;
        TextOutW(dc, r.left + lbl + j * cell + 2, r.top + 4, txt, 3);
        TextOutW(dc, r.left + 2, y0 + j * cell + 4, txt, 3);
    }

    for (i = 0; i < n_ids; i++) {
        for (j = 0; j < n_ids; j++) {
            RECT c;
            DataSeries *sa, *sb;
            float rho = (i == j) ? 1.0f : 0.0f;
            HBRUSH br;

            c.left = r.left + lbl + j * cell;
            c.top = y0 + i * cell;
            c.right = c.left + cell - 1;
            c.bottom = c.top + cell - 1;
            if (c.bottom > r.bottom) continue;

            if (i != j) {
                /* M[row i, col j] = corr( row_asset , col_asset ) */
                sa = series_get((SeriesStore *)st, ids[i]);
                sb = series_get((SeriesStore *)st, ids[j]);
                if (sa && sb) {
                    corr_pair_compute(sa, sb, &cp);
                    if (cp.ok) rho = cp.rho90;
                }
            }
            br = CreateSolidBrush(corr_rho_color(rho));
            FillRect(dc, &c, br);
            DeleteObject(br);

            if (cell >= 22) {
                wchar_t rs[8];
                ui_fmt_wdouble(rs, 8, rho, 2);
                SetTextColor(dc, fabsf(rho) > 0.45f ? CLR_BG : CLR_TXT);
                DrawTextW(dc, rs, -1, &c, DT_CENTER | DT_VCENTER | DT_SINGLELINE);
            }
        }
    }
}

void chart_corr_matrix_delta(HDC dc, const RECT *rc, const SeriesStore *st,
                             const char ids[][4], int n_ids) {
    RECT main, delta;
    int h;

    if (!st || n_ids <= 0) return;
    h = rc->bottom - rc->top;
    main = *rc;
    main.bottom = rc->top + h * 72 / 100;
    chart_corr_matrix(dc, &main, st, ids, n_ids);

    delta = *rc;
    delta.top = main.bottom + 4;
    ui_subheading(dc, &(RECT){ delta.left, delta.top, delta.right, delta.top + 12 },
                  L"\x0394\x03C1 30d-90d  (layer destabilizzazione)");
    delta.top += 14;
    if (delta.bottom <= delta.top + 8) return;

    {
        int cell, i, j, lbl = 28;
        int cell_w = (delta.right - delta.left - lbl) / n_ids;
        int cell_h = (delta.bottom - delta.top) / n_ids;
        int y0 = delta.top + lbl;
        CorrPair cp;

        cell = cell_w < cell_h ? cell_w : cell_h;
        if (cell < 6) cell = 6;
        if (cell > 14) cell = 14;

        for (i = 0; i < n_ids; i++) {
            for (j = 0; j < n_ids; j++) {
                RECT c;
                float dr = 0.0f;
                HBRUSH br;
                if (i == j) continue;
                c.left = delta.left + lbl + j * cell;
                c.top = y0 + i * cell;
                c.right = c.left + cell - 1;
                c.bottom = c.top + cell - 1;
                if (c.bottom > delta.bottom) continue;
                {
                    DataSeries *sa = series_get((SeriesStore *)st, ids[i]);
                    DataSeries *sb = series_get((SeriesStore *)st, ids[j]);
                    if (sa && sb) {
                        corr_pair_compute(sa, sb, &cp);
                        if (cp.ok) dr = cp.rho30 - cp.rho90;
                    }
                }
                br = CreateSolidBrush(corr_rho_color(dr));
                FillRect(dc, &c, br);
                DeleteObject(br);
            }
        }
    }
}

#define CRY_N 9
char g_crypto_hub[4] = "BTC";

static const char *CRY_NET[CRY_N] = {
    "BTC", "ETH", "SOL", "BNB", "XRP", "ADA", "DOT", "LNK", "AVX"
};

static struct { char id[4]; RECT rc; } g_crypto_hit[CRY_N];
static int g_crypto_hit_n = 0;

int chart_crypto_network_hit(POINT pt, char *out_id) {
    int i;
    for (i = 0; i < g_crypto_hit_n; i++) {
        if (PtInRect(&g_crypto_hit[i].rc, pt)) {
            if (out_id) lstrcpyA(out_id, g_crypto_hit[i].id);
            return 1;
        }
    }
    return 0;
}

void chart_crypto_network(HDC dc, const RECT *rc, const SeriesStore *st) {
    NetNode nodes[CRY_N];
    float leg_last[CRY_N], leg_prev[CRY_N];
    int leg_ok[CRY_N];
    NetLblBuf labels;
    RECT r = *rc;
    int cx, cy, rad, i, j, sel = 0;
    HPEN old_pen;
    wchar_t lbl[8], cap[72];

    if (!st || r.right <= r.left + 40) return;
    g_crypto_hit_n = 0;
    net_lbl_reset(&labels);
    cx = (r.left + r.right) / 2;
    cy = (r.top + r.bottom) / 2 - 4;
    rad = (r.bottom - r.top) < (r.right - r.left)
        ? (r.bottom - r.top) / 2 - 28 : (r.right - r.left) / 2 - 28;
    if (rad < 24) rad = 24;

    for (i = 0; i < CRY_N; i++) {
        double ang = -1.5707963267948966 + i * 6.283185307179586 / CRY_N;
        nodes[i].id = CRY_NET[i];
        nodes[i].x = cx + (int)(cos(ang) * rad);
        nodes[i].y = cy + (int)(sin(ang) * rad);
        leg_ok[i] = en_leg(st, CRY_NET[i], &leg_last[i], &leg_prev[i]);
        if (lstrcmpA(CRY_NET[i], g_crypto_hub) == 0) sel = i;
    }

    old_pen = (HPEN)SelectObject(dc, GetStockObject(BLACK_PEN));
    for (i = 0; i < CRY_N; i++) {
        for (j = i + 1; j < CRY_N; j++) {
            float chg = 0.0f;
            int have = 0;
            if (i == sel || j == sel) continue;
            if (leg_ok[i] && leg_ok[j]) {
                chg = (leg_last[j] / leg_last[i]) / (leg_prev[j] / leg_prev[i]) - 1.0f;
                have = 1;
            }
            net_draw_edge(dc, &nodes[i], &nodes[j], chg, have, 0, 10, 10);
        }
    }
    for (j = 0; j < CRY_N; j++) {
        float chg = 0.0f;
        int have = 0;
        if (j == sel) continue;
        if (leg_ok[sel] && leg_ok[j]) {
            chg = (leg_last[j] / leg_last[sel]) / (leg_prev[j] / leg_prev[sel]) - 1.0f;
            have = 1;
        }
        net_draw_edge(dc, &nodes[sel], &nodes[j], chg, have, 1, 14, 10);
    }
    SelectObject(dc, old_pen);

    for (j = 0; j < CRY_N; j++) {
        float rate = 0.0f, chg = 0.0f;
        int have = 0, ax, ay;
        wchar_t rate_s[16], chg_s[16], txt[32];
        if (j == sel) continue;
        if (leg_ok[sel] && leg_ok[j]) {
            rate = leg_last[j] / leg_last[sel];
            chg = rate / (leg_prev[j] / leg_prev[sel]) - 1.0f;
            have = 1;
        }
        if (!have) continue;
        net_hub_label_anchor(cx, cy, &nodes[j], j, &ax, &ay);
        ui_fmt_wdouble(rate_s, 16, (double)rate, rate > 50.0f ? 2 : 4);
        ui_fmt_wdouble(chg_s, 16, chg >= 0.0f ? chg * 100.0 : -chg * 100.0, 2);
        wsprintfW(txt, L"%s %s%s%%", rate_s, chg >= 0.0f ? L"+" : L"-", chg_s);
        net_lbl_add(&labels, txt, ax, ay, 48, 7,
                    chg >= 0.0f ? CLR_UP : CLR_DN, 2, nodes, CRY_N, sel, &r);
    }
    net_lbl_flush(dc, &labels);

    for (i = 0; i < CRY_N; i++) {
        int rr = (i == sel) ? 14 : 10;
        SelectObject(dc, i == sel ? bWhite : bGray);
        SelectObject(dc, GetStockObject(NULL_PEN));
        Ellipse(dc, nodes[i].x - rr, nodes[i].y - rr, nodes[i].x + rr, nodes[i].y + rr);
        lbl[0] = (wchar_t)nodes[i].id[0];
        lbl[1] = (wchar_t)nodes[i].id[1];
        lbl[2] = (wchar_t)nodes[i].id[2];
        lbl[3] = 0;
        draw_node_label(dc, nodes[i].x, nodes[i].y, lbl, i == sel);
        if (g_crypto_hit_n < CRY_N) {
            int rr2 = (i == sel) ? 16 : 12;
            g_crypto_hit[g_crypto_hit_n].id[0] = nodes[i].id[0];
            g_crypto_hit[g_crypto_hit_n].id[1] = nodes[i].id[1];
            g_crypto_hit[g_crypto_hit_n].id[2] = nodes[i].id[2];
            g_crypto_hit[g_crypto_hit_n].id[3] = 0;
            g_crypto_hit[g_crypto_hit_n].rc = (RECT){
                nodes[i].x - rr2, nodes[i].y - rr2,
                nodes[i].x + rr2, nodes[i].y + rr2
            };
            g_crypto_hit_n++;
        }
    }
    wsprintfW(cap, L"mesh %d hub %hs  click nodo  verde=rafforza  rosso=indebolisce",
              CRY_N, g_crypto_hub);
    SetBkMode(dc, TRANSPARENT);
    SetTextColor(dc, CLR_OFF);
    SelectObject(dc, fSm);
    TextOutW(dc, r.left, r.bottom - 12, cap, lstrlenW(cap));
}

#define TRN_N 6
char g_trans_hub[4] = "EUA";

static const char *TRN_IDS[TRN_N] = { "EUA", "GRN", "DIR", "BRT", "NGF", "COA" };

void chart_transition_network(HDC dc, const RECT *rc, const SeriesStore *st) {
    NetNode nodes[TRN_N];
    float leg_last[TRN_N], leg_prev[TRN_N];
    int leg_ok[TRN_N];
    NetLblBuf labels;
    RECT r = *rc;
    int cx, cy, rad, i, j, sel = 0;
    HPEN old_pen;
    wchar_t lbl[8], cap[72];

    if (!st || r.right <= r.left + 40) return;
    net_lbl_reset(&labels);
    cx = (r.left + r.right) / 2;
    cy = (r.top + r.bottom) / 2 - 4;
    rad = (r.bottom - r.top) < (r.right - r.left)
        ? (r.bottom - r.top) / 2 - 28 : (r.right - r.left) / 2 - 28;
    if (rad < 24) rad = 24;

    for (i = 0; i < TRN_N; i++) {
        double ang = -1.5707963267948966 + i * 6.283185307179586 / TRN_N;
        nodes[i].id = TRN_IDS[i];
        nodes[i].x = cx + (int)(cos(ang) * rad);
        nodes[i].y = cy + (int)(sin(ang) * rad);
        leg_ok[i] = en_leg(st, TRN_IDS[i], &leg_last[i], &leg_prev[i]);
        if (lstrcmpA(TRN_IDS[i], g_trans_hub) == 0) sel = i;
    }
    for (i = 0; i < TRN_N; i++)
        if (leg_ok[i]) break;
    if (i >= TRN_N) {
        SetBkMode(dc, TRANSPARENT);
        SetTextColor(dc, CLR_OFF);
        SelectObject(dc, fSm);
        TextOutW(dc, r.left, r.top + 20, L"attesa libero CSV (EUA,GRN,DIR...)", 34);
        return;
    }

    old_pen = (HPEN)SelectObject(dc, GetStockObject(BLACK_PEN));
    for (i = 0; i < TRN_N; i++) {
        for (j = i + 1; j < TRN_N; j++) {
            float chg = 0.0f;
            int have = 0;
            if (i == sel || j == sel) continue;
            if (leg_ok[i] && leg_ok[j]) {
                chg = (leg_last[j] / leg_last[i]) / (leg_prev[j] / leg_prev[i]) - 1.0f;
                have = 1;
            }
            net_draw_edge(dc, &nodes[i], &nodes[j], chg, have, 0, 10, 10);
        }
    }
    for (j = 0; j < TRN_N; j++) {
        float chg = 0.0f;
        int have = 0;
        if (j == sel) continue;
        if (leg_ok[sel] && leg_ok[j]) {
            chg = (leg_last[j] / leg_last[sel]) / (leg_prev[j] / leg_prev[sel]) - 1.0f;
            have = 1;
        }
        net_draw_edge(dc, &nodes[sel], &nodes[j], chg, have, 1, 14, 10);
    }
    SelectObject(dc, old_pen);

    for (j = 0; j < TRN_N; j++) {
        float rate = 0.0f, chg = 0.0f;
        int have = 0, ax, ay;
        wchar_t rate_s[16], chg_s[16], txt[32];
        if (j == sel) continue;
        if (leg_ok[sel] && leg_ok[j]) {
            rate = leg_last[j] / leg_last[sel];
            chg = rate / (leg_prev[j] / leg_prev[sel]) - 1.0f;
            have = 1;
        }
        if (!have) continue;
        net_hub_label_anchor(cx, cy, &nodes[j], j, &ax, &ay);
        ui_fmt_wdouble(rate_s, 16, (double)rate, rate > 50.0f ? 2 : 3);
        ui_fmt_wdouble(chg_s, 16, chg >= 0.0f ? chg * 100.0 : -chg * 100.0, 2);
        wsprintfW(txt, L"%s %s%s%%", rate_s, chg >= 0.0f ? L"+" : L"-", chg_s);
        net_lbl_add(&labels, txt, ax, ay, 48, 7,
                    chg >= 0.0f ? CLR_UP : CLR_DN, 2, nodes, TRN_N, sel, &r);
    }
    net_lbl_flush(dc, &labels);

    for (i = 0; i < TRN_N; i++) {
        int rr = (i == sel) ? 14 : 10;
        SelectObject(dc, i == sel ? bWhite : bGray);
        SelectObject(dc, GetStockObject(NULL_PEN));
        Ellipse(dc, nodes[i].x - rr, nodes[i].y - rr, nodes[i].x + rr, nodes[i].y + rr);
        lbl[0] = (wchar_t)nodes[i].id[0];
        lbl[1] = (wchar_t)nodes[i].id[1];
        lbl[2] = (wchar_t)nodes[i].id[2];
        lbl[3] = 0;
        draw_node_label(dc, nodes[i].x, nodes[i].y, lbl, i == sel);
    }
    wsprintfW(cap, L"transition hub %hs  carbon/clean/dirty/fossil", g_trans_hub);
    SetBkMode(dc, TRANSPARENT);
    SetTextColor(dc, CLR_OFF);
    SelectObject(dc, fSm);
    TextOutW(dc, r.left, r.bottom - 12, cap, lstrlenW(cap));
}

void chart_yield_curve(HDC dc, const RECT *rc, const SeriesStore *st) {
    static const struct { const char *id; int yr; const wchar_t *lbl; } PT[] = {
        { "U2",  2, L"2Y" }, { "U5",  5, L"5Y" },
        { "U10", 10, L"10Y" }, { "U30", 30, L"30Y" }
    };
    RECT r = *rc;
    POINT pts[4];
    float vals[4], mn, mx, span;
    const wchar_t *lbls[4];
    int i, n = 0, x0, x1, y0, y1, gy;
    HPEN pen, grid, old;
    HBRUSH dot;

    if (!st || r.right <= r.left + 60 || r.bottom <= r.top + 30) return;
    norm_rect(&r, 4);
    x0 = r.left + 28;
    x1 = r.right - 8;
    y0 = r.top + 6;
    y1 = r.bottom - 14;
    if (x1 <= x0 + 20 || y1 <= y0 + 10) return;

    mn = 1e9f;
    mx = -1e9f;
    for (i = 0; i < 4; i++) {
        const DataSeries *s = series_get((SeriesStore *)st, PT[i].id);
        if (!s || s->n < 1) continue;
        vals[n] = series_last(s);
        if (vals[n] < mn) mn = vals[n];
        if (vals[n] > mx) mx = vals[n];
        lbls[n] = PT[i].lbl;
        pts[n].x = x0 + (PT[i].yr - 2) * (x1 - x0) / 28;
        n++;
    }
    if (n < 2) {
        SetTextColor(dc, CLR_OFF);
        TextOutW(dc, r.left, r.top, L"curva: attesa U2/U5/U10/U30", 26);
        return;
    }
    span = mx - mn;
    if (span < 0.05f) span = 0.5f;
    for (i = 0; i < n; i++)
        pts[i].y = y1 - (int)((vals[i] - mn) / span * (y1 - y0 - 1));

    grid = CreatePen(PS_SOLID, 1, CLR_GRID);
    old = (HPEN)SelectObject(dc, grid);
    for (i = 1; i <= 2; i++) {
        gy = y1 - (y1 - y0) * i / 3;
        MoveToEx(dc, x0, gy, NULL);
        LineTo(dc, x1, gy);
    }
    SelectObject(dc, old);
    DeleteObject(grid);

    pen = CreatePen(PS_SOLID, 2, CLR_LINE);
    SelectObject(dc, pen);
    Polyline(dc, pts, n);
    SelectObject(dc, old);
    DeleteObject(pen);

    for (i = 0; i < n; i++) {
        wchar_t buf[16];
        dot = CreateSolidBrush(CLR_ACC);
        SelectObject(dc, dot);
        Ellipse(dc, pts[i].x - 3, pts[i].y - 3, pts[i].x + 3, pts[i].y + 3);
        DeleteObject(dot);
        ui_fmt_wdouble(buf, 16, vals[i], 2);
        SetTextColor(dc, CLR_DIM);
        TextOutW(dc, pts[i].x - 10, pts[i].y - 16, lbls[i], lstrlenW(lbls[i]));
        TextOutW(dc, pts[i].x - 12, pts[i].y + 4, buf, lstrlenW(buf));
    }
}

static int spread_align(const DataSeries *a, const DataSeries *b,
                        float *out, int cap, int mode) {
    int i = 0, j = 0, n = 0;

    if (!a || !b || !out || cap < 2) return 0;
    while (i < (int)a->n && j < (int)b->n && n < cap) {
        if (a->ymd[i] == b->ymd[j]) {
            float va = a->val[i], vb = b->val[j];
            if (va > 0.0f && vb > 0.0f) {
                out[n++] = mode ? va / vb : va - vb;
            }
            i++;
            j++;
        } else if (a->ymd[i] < b->ymd[j]) {
            i++;
        } else {
            j++;
        }
    }
    return n;
}

void chart_spread_ts(HDC dc, const RECT *rc, const DataSeries *a, const DataSeries *b,
                     int mode, const wchar_t *title) {
    static float sp[SER_POINTS];
    RECT r = *rc, tr, pr;
    POINT pts[SER_POINTS];
    float mn, mx, span;
    int n, i, w, h, win = 90;
    HPEN pen, old;

    if (!a || !b || r.right <= r.left + 20) return;
    n = spread_align(a, b, sp, SER_POINTS, mode);
    if (n < 3) return;
    if (n > win) {
        memmove(sp, sp + n - win, (size_t)win * sizeof(sp[0]));
        n = win;
    }

    tr = r;
    tr.bottom = tr.top + 12;
    ui_subheading(dc, &tr, title ? title : L"SPREAD");
    pr = r;
    pr.top += 14;
    norm_rect(&pr, 2);
    w = pr.right - pr.left;
    h = pr.bottom - pr.top;
    if (w < 8 || h < 8) return;

    mn = mx = sp[0];
    for (i = 1; i < n; i++) {
        if (sp[i] < mn) mn = sp[i];
        if (sp[i] > mx) mx = sp[i];
    }
    span = mx - mn;
    if (span < 1e-6f) span = fabsf(mx) * 0.02f + 1e-6f;
    for (i = 0; i < n; i++) {
        pts[i].x = pr.left + i * w / (n - 1);
        pts[i].y = pr.bottom - (int)((sp[i] - mn) / span * (h - 1));
    }
    pen = CreatePen(PS_SOLID, 1, CLR_LINE);
    old = (HPEN)SelectObject(dc, pen);
    Polyline(dc, pts, n);
    SelectObject(dc, old);
    DeleteObject(pen);
}

void chart_bar_last(HDC dc, const RECT *rc, const SeriesStore *st,
                    const char *ids[], const wchar_t *labels[], int n,
                    const wchar_t *unit) {
    RECT r = *rc;
    float vals[12], mx = 0.0f;
    const wchar_t *lbl[12];
    int i, cnt = 0, bar_w, x, y0, y1, h;

    if (!st || !ids || n <= 0 || r.bottom <= r.top + 20) return;
    if (n > 12) n = 12;
    for (i = 0; i < n; i++) {
        const DataSeries *s = series_get((SeriesStore *)st, ids[i]);
        if (!s || s->n < 1) continue;
        vals[cnt] = series_last(s);
        lbl[cnt] = labels ? labels[i] : NULL;
        if (vals[cnt] > mx) mx = vals[cnt];
        cnt++;
    }
    if (cnt < 1 || mx <= 0.0f) return;
    y0 = r.top + 14;
    y1 = r.bottom - 4;
    h = y1 - y0;
    bar_w = (r.right - r.left - 20) / cnt;
    if (bar_w < 12) bar_w = 12;
    x = r.left + 4;
    for (i = 0; i < cnt; i++) {
        int bh = (int)(vals[i] / mx * (h - 16));
        RECT bar = { x + 4, y1 - bh, x + bar_w - 4, y1 };
        wchar_t v[12];
        HBRUSH br = CreateSolidBrush(CLR_ACC);
        FillRect(dc, &bar, br);
        DeleteObject(br);
        ui_fmt_wdouble(v, 12, vals[i], vals[i] > 50.0f ? 0 : 1);
        SetTextColor(dc, CLR_DIM);
        SelectObject(dc, fSm);
        TextOutW(dc, x + 2, y1 - bh - 12, v, lstrlenW(v));
        if (lbl[i])
            TextOutW(dc, x + 2, y1 + 2, lbl[i], lstrlenW(lbl[i]));
        x += bar_w;
    }
    if (unit) {
        SetTextColor(dc, CLR_OFF);
        TextOutW(dc, r.left, r.top, unit, lstrlenW(unit));
    }
}

void chart_fuel_stack(HDC dc, const RECT *rc, const ProdCountry *p) {
    static const COLORREF FC[] = {
        RGB(220,220,120), RGB(180,220,255), RGB(100,160,220), RGB(200,180,255),
        RGB(255,200,120), RGB(140,140,140), RGB(180,160,140), RGB(160,200,160),
        RGB(120,120,120)
    };
    RECT r = *rc, bar, lr;
    float tot = 0.0f, x0;
    int f, w;
    wchar_t cap[48];

    if (!p || !p->have_gen || r.right <= r.left + 40) return;
    for (f = 0; f < FUEL_COUNT; f++) tot += p->gen[f];
    if (tot <= 0.0f) return;

    wsprintfW(cap, L"%s %u", p->iso, (unsigned)p->year);
    ui_subheading(dc, &(RECT){ r.left, r.top, r.right, r.top + 12 }, cap);
    bar = r;
    bar.top += 14;
    bar.bottom = bar.top + 14;
    w = bar.right - bar.left;
    x0 = (float)bar.left;
    for (f = 0; f < FUEL_COUNT; f++) {
        float frac = p->gen[f] / tot;
        int bw;
        HBRUSH br;
        if (p->gen[f] <= 0.0f) continue;
        bw = (int)(frac * w);
        if (bw < 1) bw = 1;
        lr = bar;
        lr.left = (LONG)x0;
        lr.right = lr.left + bw;
        br = CreateSolidBrush(FC[f]);
        FillRect(dc, &lr, br);
        DeleteObject(br);
        x0 += bw;
    }
    SetTextColor(dc, CLR_OFF);
    SelectObject(dc, fSm);
    wsprintfW(cap, L"%.0f TWh tot", tot);
    TextOutW(dc, bar.left, bar.bottom + 2, cap, lstrlenW(cap));
}

static COLORREF heat_color(float t) {
    int r, g, b;
    if (t < 0.0f) t = 0.0f;
    if (t > 1.0f) t = 1.0f;
    if (t < 0.5f) {
        r = (int)(40 + t * 2.0f * 180);
        g = (int)(40 + t * 2.0f * 180);
        b = (int)(80 + t * 2.0f * 120);
    } else {
        float u = (t - 0.5f) * 2.0f;
        r = (int)(220 + u * 35);
        g = (int)(220 - u * 120);
        b = (int)(200 - u * 160);
    }
    return RGB(r, g, b);
}

void chart_horizon(HDC dc, const RECT *rc, const DataSeries *s, const wchar_t *label,
                   COLORREF line, int rows) {
    RECT r = *rc, band, hdr;
    int w, h, i, ri, n, cw, ch;
    float mn, mx, span, last;
    wchar_t num[20];

    if (!s || s->n < 2 || r.right <= r.left + 4 || r.bottom <= r.top + 4) return;
    if (rows < 3) rows = 4;
    if (rows > 8) rows = 6;

    hdr = r;
    hdr.bottom = hdr.top + 12;
    last = series_last(s);
    ui_fmt_wdouble(num, 20, last, last >= 100.0f ? 1 : 2);
    {
        wchar_t cap[80];
        wsprintfW(cap, L"%s %s", label ? label : s->label, num);
        SetTextColor(dc, line);
        SetBkMode(dc, TRANSPARENT);
        SelectObject(dc, fSm);
        TextOutW(dc, hdr.left, hdr.top, cap, lstrlenW(cap));
        ui_stale_dot(dc, hdr.right - 8, hdr.top + 3, s->live > 0.0f ? 0 : 72);
    }

    band = r;
    band.top = hdr.bottom + 1;
    w = band.right - band.left;
    h = band.bottom - band.top;
    if (w < 8 || h < rows) return;

    n = s->n;
    mn = s->min_h;
    mx = s->max_h;
    span = mx - mn;
    if (span < 1e-6f) span = fabsf(mx) * 0.01f + 1e-6f;
    ch = h / rows;
    if (ch < 1) ch = 1;

    {
        HBRUSH br = CreateSolidBrush(line);
        int step, samples;

        if (!br) return;
        samples = w;
        if (samples > n) samples = n;
        if (samples < 2) samples = 2;
        step = (n - 1) / (samples - 1);
        if (step < 1) step = 1;
        for (i = 0; i < n; i += step) {
            int col = i * w / (n - 1);
            int row = rows - 1 - (int)((s->val[i] - mn) / span * (rows - 0.01f));
            RECT cell;
            if (row < 0) row = 0;
            if (row >= rows) row = rows - 1;
            cell.left = band.left + col;
            cell.right = cell.left + 2;
            if (cell.right > band.right) cell.right = band.right;
            cell.top = band.top + row * ch;
            cell.bottom = cell.top + ch;
            FillRect(dc, &cell, br);
        }
        DeleteObject(br);
    }

    if (s->live > 0.0f) {
        int col = band.right - 1;
        int row = rows - 1 - (int)((s->live - mn) / span * (rows - 0.01f));
        RECT cell;
        HBRUSH br;
        if (row < 0) row = 0;
        if (row >= rows) row = rows - 1;
        cell.left = col - 1;
        cell.right = col + 2;
        cell.top = band.top + row * ch;
        cell.bottom = cell.top + ch;
        br = CreateSolidBrush(CLR_ACC);
        FillRect(dc, &cell, br);
        DeleteObject(br);
    }
    (void)ri;
    (void)cw;
}

void chart_calendar_heatmap(HDC dc, const RECT *rc, const float *vals, int rows, int cols,
                            float vmin, float vmax, const wchar_t *title) {
    RECT r = *rc, plot;
    int cw, ch, c, hr;
    float span;

    if (!vals || rows <= 0 || cols <= 0 || r.right <= r.left + 8) return;
    if (title && title[0]) {
        ui_subheading(dc, &(RECT){ r.left, r.top, r.right, r.top + 12 }, title);
        r.top += 14;
    }
    plot = r;
    cw = (plot.right - plot.left) / cols;
    ch = (plot.bottom - plot.top) / rows;
    if (cw < 1) cw = 1;
    if (ch < 1) ch = 1;
    span = vmax - vmin;
    if (span < 1e-6f) span = 1.0f;

    for (hr = 0; hr < rows; hr++) {
        for (c = 0; c < cols; c++) {
            float v = vals[hr * cols + c];
            float t = (v - vmin) / span;
            RECT cell;
            HBRUSH cell_br;
            cell.left = plot.left + c * cw;
            cell.right = cell.left + cw - 1;
            cell.top = plot.top + hr * ch;
            cell.bottom = cell.top + ch - 1;
            cell_br = CreateSolidBrush(heat_color(t));
            if (cell_br) {
                FillRect(dc, &cell, cell_br);
                DeleteObject(cell_br);
            }
        }
    }
}

void chart_gauge(HDC dc, const RECT *rc, float val, float lo, float mid, float hi,
                 const wchar_t *label, const wchar_t *unit) {
    RECT r = *rc, bar;
    int x, w, fill;
    wchar_t line[64], v[16];
    COLORREF col;
    float span;

    if (r.right <= r.left + 20) return;
    ui_fmt_wdouble(v, 16, val, val >= 10.0f ? 1 : 2);
    wsprintfW(line, L"%s %s%s", label ? label : L"", v, unit ? unit : L"");
    SetTextColor(dc, CLR_TXT);
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    TextOutW(dc, r.left, r.top, line, lstrlenW(line));

    bar = r;
    bar.top += 13;
    bar.bottom = bar.top + 8;
    ui_fill(dc, &bar, bGray);
    span = hi - lo;
    if (span < 1e-6f) span = 1.0f;
    w = bar.right - bar.left;
    fill = (int)((val - lo) / span * w);
    if (fill < 0) fill = 0;
    if (fill > w) fill = w;
    if (val >= mid) col = CLR_DN;
    else if (val >= lo + (mid - lo) * 0.5f) col = RGB(255, 180, 80);
    else col = CLR_UP;
    if (fill > 0) {
        RECT f = bar;
        HBRUSH br = CreateSolidBrush(col);
        f.right = f.left + fill;
        ui_fill(dc, &f, br);
        DeleteObject(br);
    }
    x = bar.left + (int)((mid - lo) / span * w);
    if (x > bar.left && x < bar.right) {
        HPEN pen = CreatePen(PS_SOLID, 1, CLR_DIM);
        HPEN old = (HPEN)SelectObject(dc, pen);
        MoveToEx(dc, x, bar.top - 1, NULL);
        LineTo(dc, x, bar.bottom + 1);
        SelectObject(dc, old);
        DeleteObject(pen);
    }
}

void chart_bar_divergent(HDC dc, const RECT *rc, const wchar_t *labels[], const float *vals,
                         int n, float vmax) {
    RECT r = *rc;
    int i, lh = 13, y = r.top, mid, hw;

    if (!labels || !vals || n <= 0 || vmax < 1e-6f) return;
    if (r.right <= r.left + 48 || r.bottom <= r.top + lh) return;
    mid = (r.left + r.right) / 2;
    hw = (r.right - r.left) / 2 - 24;
    if (hw < 8) hw = 8;
    for (i = 0; i < n && y + lh <= r.bottom; i++) {
        float v = vals[i];
        int bw = (int)(fabsf(v) / vmax * hw);
        RECT bar;
        HBRUSH br;
        wchar_t num[12];
        SetTextColor(dc, CLR_DIM);
        SelectObject(dc, fSm);
        TextOutW(dc, r.left, y, labels[i], lstrlenW(labels[i]));
        ui_fmt_wdouble(num, 12, v, 1);
        if (v >= 0.0f) {
            bar.left = mid;
            bar.right = mid + bw;
            br = CreateSolidBrush(CLR_UP);
        } else {
            bar.left = mid - bw;
            bar.right = mid;
            br = CreateSolidBrush(CLR_DN);
        }
        bar.top = y + 2;
        bar.bottom = y + lh - 2;
        if (bw > 0 && br) FillRect(dc, &bar, br);
        if (br) DeleteObject(br);
        SetTextColor(dc, CLR_TXT);
        TextOutW(dc, r.right - 36, y, num, lstrlenW(num));
        y += lh;
    }
}

void chart_dual_spark(HDC dc, const RECT *rc, const DataSeries *a, const DataSeries *b,
                      COLORREF col_a, COLORREF col_b, const wchar_t *leg_a, const wchar_t *leg_b) {
    RECT r = *rc, leg;
    POINT pa[SER_POINTS], pb[SER_POINTS];
    HPEN pen_a, pen_b, grid_pen, old_pen;
    int i, w, h, na, nb, n, gy;
    float mn, mx, span;

    if (!a || !b || a->n < 2 || b->n < 2 || r.right <= r.left + 12 || r.bottom <= r.top + 16)
        return;
    norm_rect(&r, 3);
    w = r.right - r.left;
    h = r.bottom - r.top;
    na = a->n;
    nb = b->n;
    n = na < nb ? na : nb;
    if (n > SER_POINTS) n = SER_POINTS;
    mn = a->min_h < b->min_h ? a->min_h : b->min_h;
    mx = a->max_h > b->max_h ? a->max_h : b->max_h;
    span = mx - mn;
    if (span < 1e-6f) span = mx * 0.01f + 1e-6f;

    grid_pen = CreatePen(PS_SOLID, 1, CLR_GRID);
    old_pen = (HPEN)SelectObject(dc, grid_pen);
    for (i = 1; i <= 2; i++) {
        gy = r.bottom - (h * i) / 3;
        MoveToEx(dc, r.left, gy, NULL);
        LineTo(dc, r.right, gy);
    }
    SelectObject(dc, old_pen);
    DeleteObject(grid_pen);

    for (i = 0; i < n; i++) {
        int ia = a->n - n + i;
        int ib = b->n - n + i;
        pa[i].x = r.left + (i * w) / (n - 1);
        pb[i].x = pa[i].x;
        pa[i].y = r.bottom - (int)((a->val[ia] - mn) / span * (h - 1));
        pb[i].y = r.bottom - (int)((b->val[ib] - mn) / span * (h - 1));
    }

    pen_b = CreatePen(PS_SOLID, 1, col_b);
    SelectObject(dc, pen_b);
    Polyline(dc, pb, n);
    SelectObject(dc, old_pen);
    DeleteObject(pen_b);

    pen_a = CreatePen(PS_SOLID, 2, col_a);
    SelectObject(dc, pen_a);
    Polyline(dc, pa, n);
    SelectObject(dc, old_pen);
    DeleteObject(pen_a);

    leg = r;
    leg.bottom = leg.top + 11;
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    if (leg_a && leg_a[0]) {
        SetTextColor(dc, col_a);
        TextOutW(dc, leg.left, leg.top, leg_a, lstrlenW(leg_a));
    }
    if (leg_b && leg_b[0]) {
        SetTextColor(dc, col_b);
        TextOutW(dc, leg.left + 88, leg.top, leg_b, lstrlenW(leg_b));
    }
}

void chart_regime_bar(HDC dc, const RECT *rc, float score, const wchar_t *label) {
    RECT r = *rc, bar;
    int w, fill;
    COLORREF col;
    wchar_t cap[80];

    if (r.right <= r.left + 20) return;
    if (score < 0.0f) score = 0.0f;
    if (score > 100.0f) score = 100.0f;
    wsprintfW(cap, L"%s  regime %.0f", label ? label : L"", score);
    SetTextColor(dc, CLR_DIM);
    SelectObject(dc, fSm);
    TextOutW(dc, r.left, r.top, cap, lstrlenW(cap));
    bar = r;
    bar.top += 14;
    bar.bottom = bar.top + 8;
    ui_fill(dc, &bar, bGray);
    w = bar.right - bar.left;
    fill = (int)(score / 100.0f * w);
    if (score < 35.0f) col = CLR_UP;
    else if (score < 65.0f) col = CLR_TXT;
    else col = CLR_DN;
    if (fill > 0) {
        RECT f = bar;
        HBRUSH br = CreateSolidBrush(col);
        f.right = f.left + fill;
        ui_fill(dc, &f, br);
        DeleteObject(br);
    }
}
