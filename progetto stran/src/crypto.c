#include "crypto.h"
#include "ingest_crypto.h"
#include "ingest.h"
#include "corr.h"
#include "data.h"
#include "chart.h"
#include "glossary.h"
#include <math.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    const char *id;
    const wchar_t *name;
    const char *bin;
    const char *krk;
} CryDef;

static const CryDef CRY_DEF[] = {
    { "BTC", L"Bitcoin",   "BTCUSDT",  "XXBTZUSD" },
    { "ETH", L"Ethereum",  "ETHUSDT",  "XETHZUSD" },
    { "SOL", L"Solana",    "SOLUSDT",  "SOLUSD"   },
    { "BNB", L"BNB",       "BNBUSDT",  "BNBUSD"   },
    { "XRP", L"Ripple",    "XRPUSDT",  "XRPUSD"   },
    { "ADA", L"Cardano",   "ADAUSDT",  "ADAUSD"   },
    { "DOT", L"Polkadot",  "DOTUSDT",  "DOTUSD"   },
    { "LNK", L"Chainlink", "LINKUSDT", "LINKUSD"  },
    { "AVX", L"Avalanche", "AVAXUSDT", "AVAXUSD"  },
    { "MAT", L"Polygon",   "POLUSDT",  "MATICUSD" },
    { "DOG", L"Dogecoin",  "DOGEUSDT", "XDGUSD"   },
    { "LTC", L"Litecoin",  "LTCUSDT",  "XLTCZUSD" },
    { "UDC", L"USD Coin",  "USDCUSDT", NULL       },
};

static CryptoQuote g_cry[CRY_MAX];
static int g_cry_n;

void crypto_init(void) {
    int i, n = (int)(sizeof(CRY_DEF) / sizeof(CRY_DEF[0]));

    if (n > CRY_MAX) n = CRY_MAX;
    g_cry_n = n;
    memset(g_cry, 0, sizeof(g_cry));
    for (i = 0; i < n; i++) {
        lstrcpynA(g_cry[i].id, CRY_DEF[i].id, 4);
        lstrcpynW(g_cry[i].name, CRY_DEF[i].name, 16);
        lstrcpynA(g_cry[i].binance, CRY_DEF[i].bin, 16);
        if (CRY_DEF[i].krk)
            lstrcpynA(g_cry[i].kraken, CRY_DEF[i].krk, 16);
    }
}

int crypto_count(void) { return g_cry_n; }

const CryptoQuote *crypto_get(int i) {
    if (i < 0 || i >= g_cry_n) return NULL;
    return &g_cry[i];
}

static BOOL crypto_cache_stale(const wchar_t *path, uint32_t max_age_sec) {
    WIN32_FILE_ATTRIBUTE_DATA fa;
    FILETIME now_ft;
    ULARGE_INTEGER now_u, wt_u;

    if (!GetFileAttributesExW(path, GetFileExInfoStandard, &fa))
        return TRUE;
    GetSystemTimeAsFileTime(&now_ft);
    now_u.LowPart = now_ft.dwLowDateTime;
    now_u.HighPart = now_ft.dwHighDateTime;
    wt_u.LowPart = fa.ftLastWriteTime.dwLowDateTime;
    wt_u.HighPart = fa.ftLastWriteTime.dwHighDateTime;
    if (now_u.QuadPart <= wt_u.QuadPart) return FALSE;
    return (now_u.QuadPart - wt_u.QuadPart) / 10000000ULL > (ULONGLONG)max_age_sec;
}

static void crypto_hist_fetch(const char *desk_id, const char *bin_sym) {
    static char body[262144];
    wchar_t path[MAX_PATH];
    FILE *f;
    int n;

    if (!desk_id || !bin_sym || lstrcmpA(bin_sym, "USDCUSDT") == 0) return;
    CreateDirectoryW(L"cache\\crypto", NULL);
    wsprintfW(path, L"cache\\crypto\\%hs.csv", desk_id);
    f = _wfopen(path, L"r");
    if (f) {
        fclose(f);
        if (!crypto_cache_stale(path, 86400))
            return;
    }

    n = ingest_binance_klines(bin_sym, 400, body, sizeof(body));
    if (n < 10) return;
    f = _wfopen(path, L"w");
    if (!f) return;
    fwrite(body, 1, strlen(body), f);
    fclose(f);
}

void crypto_merge_series(SeriesStore *st) {
    int i;

    if (!st) return;
    for (i = 0; i < g_cry_n; i++) {
        static char body[262144];
        static uint32_t ymd[SER_POINTS];
        static float val[SER_POINTS];
        wchar_t path[MAX_PATH];
        size_t len = 0;
        FILE *f;
        int n;

        if (lstrcmpA(g_cry[i].id, "UDC") == 0) continue;
        wsprintfW(path, L"cache\\crypto\\%hs.csv", g_cry[i].id);
        f = _wfopen(path, L"r");
        if (!f) continue;
        len = fread(body, 1, sizeof(body) - 1, f);
        fclose(f);
        body[len] = 0;
        n = ingest_fred_hist(body, len, ymd, val, SER_POINTS);
        if (n < 3) continue;
        series_add(st, g_cry[i].id, g_cry[i].name, SER_CRYPTO);
        series_load(st, g_cry[i].id, ymd, val, n,
                    g_cry[i].have ? g_cry[i].usd_binance : val[n - 1]);
        if (g_cry[i].have) {
            SYSTEMTIME utc;
            uint32_t td;
            GetSystemTime(&utc);
            td = (uint32_t)(utc.wYear * 10000u + utc.wMonth * 100u + utc.wDay);
            series_touch_day(series_get(st, g_cry[i].id), td, g_cry[i].usd_binance);
        }
    }
}

void crypto_refresh(void) {
    int i;
    static int hist_once;

    if (g_cry_n <= 0) crypto_init();

    for (i = 0; i < g_cry_n; i++) {
        CryptoVenueTick bn = { 0 }, kr = { 0 };
        float mid;

        g_cry[i].have = 0;
        g_cry[i].basis_bps = 0.0f;
        if (ingest_binance_ticker(g_cry[i].binance, &bn) && bn.ok) {
            g_cry[i].usd_binance = bn.usd;
            g_cry[i].chg_24h = bn.chg_pct;
            g_cry[i].vol_quote = bn.vol_usd;
            g_cry[i].have = 1;
        }
        if (g_cry[i].kraken[0] &&
            ingest_kraken_ticker(g_cry[i].kraken, &kr) && kr.ok) {
            g_cry[i].usd_kraken = kr.usd;
            if (g_cry[i].usd_binance > 0.0f) {
                mid = (g_cry[i].usd_binance + kr.usd) * 0.5f;
                if (mid > 0.0f)
                    g_cry[i].basis_bps =
                        (g_cry[i].usd_binance - kr.usd) / mid * 10000.0f;
            }
        }
        if (lstrcmpA(g_cry[i].id, "UDC") == 0 && g_cry[i].have)
            g_cry[i].basis_bps = (g_cry[i].usd_binance - 1.0f) * 10000.0f;
        g_cry[i].have_funding = 0;
        if (lstrcmpA(g_cry[i].id, "BTC") == 0 || lstrcmpA(g_cry[i].id, "ETH") == 0) {
            float fr = 0.0f;
            if (ingest_binance_funding(g_cry[i].binance, &fr)) {
                g_cry[i].funding_pct = fr;
                g_cry[i].have_funding = 1;
            }
        }
    }

    if (!hist_once) {
        hist_once = 1;
        for (i = 0; i < g_cry_n; i++)
            crypto_hist_fetch(g_cry[i].id, g_cry[i].binance);
    } else {
        for (i = 0; i < g_cry_n; i++) {
            wchar_t path[MAX_PATH];
            wsprintfW(path, L"cache\\crypto\\%hs.csv", g_cry[i].id);
            if (crypto_cache_stale(path, 86400))
                crypto_hist_fetch(g_cry[i].id, g_cry[i].binance);
        }
    }
}

static const CryptoQuote *crypto_quote_id(const char *id) {
    int i;
    for (i = 0; i < g_cry_n; i++)
        if (lstrcmpA(g_cry[i].id, id) == 0) return &g_cry[i];
    return NULL;
}

static void crypto_spread_eth_btc(const SeriesStore *st, float *ratio, float *chg) {
    DataSeries *e = series_get((SeriesStore *)st, "ETH");
    DataSeries *b = series_get((SeriesStore *)st, "BTC");
    const CryptoQuote *eq = crypto_quote_id("ETH");
    const CryptoQuote *bq = crypto_quote_id("BTC");
    float eb, bb;

    if (e && b && e->n >= 2 && b->n >= 2 && series_last(b) > 0.0f) {
        if (ratio) *ratio = series_last(e) / series_last(b);
        if (chg) {
            float rt = series_last(e) / series_last(b);
            float rp = e->val[e->n - 2] / b->val[b->n - 2];
            *chg = rp > 0.0f ? (rt - rp) / rp : 0.0f;
        }
        return;
    }
    if (eq && bq && eq->have && bq->have && bq->usd_binance > 0.0f) {
        eb = eq->usd_binance;
        bb = bq->usd_binance;
        if (ratio) *ratio = eb / bb;
        if (chg && eq->chg_24h != 0.0f && bq->chg_24h != 0.0f)
            *chg = (1.0f + eq->chg_24h / 100.0f) / (1.0f + bq->chg_24h / 100.0f) - 1.0f;
        return;
    }
    if (ratio) *ratio = 0.0f;
    if (chg) *chg = 0.0f;
}

static int signal_row_fit(RECT *row, const RECT *bound) {
    if (row->top >= bound->bottom - 14) return 0;
    if (row->bottom > bound->bottom) row->bottom = bound->bottom;
    return 1;
}

static void paint_macro_rho(HDC dc, RECT *row, const RECT *bound, const SeriesStore *st,
                            const char *a, const char *b, const wchar_t *label) {
    DataSeries *sa = series_get((SeriesStore *)st, a);
    DataSeries *sb = series_get((SeriesStore *)st, b);
    CorrPair cp;
    wchar_t line[96], v[16], beta[16];

    if (!signal_row_fit(row, bound)) return;
    if (!sa || !sb || sa->n < 10 || sb->n < 10) return;
    corr_pair_compute(sa, sb, &cp);
    if (!cp.ok) return;
    ui_fmt_wdouble(v, 16, cp.rho90, 2);
    ui_fmt_wdouble(beta, 16, cp.beta90, 2);
    wsprintfW(line, L"%s  \x03C1 90d = %s   \x03B2(A|B) = %s", label, v, beta);
    ui_label_rect(dc, row, line, CLR_DIM, fSm);
    row->top += 15;
    row->bottom += 15;
}

static void paint_crypto_signals(HDC dc, RECT r, const SeriesStore *st) {
    wchar_t line[120], v[16], c[16], tag[24];
    RECT row, start;
    float sp, ch;
    int i, best_i = -1, drew = 0;
    float best_abs = 0.0f;
    DataSeries eth, btc;

    ui_subheading(dc, &(RECT){ r.left, r.top, r.right, r.top + 12 },
                  L"SEGNALI VERI  (soglie retail quantificate)");
    row = r;
    row.top += 14;
    row.bottom = row.top + 14;
    start = row;

    for (i = 0; i < g_cry_n; i++) {
        if (!g_cry[i].have || !g_cry[i].kraken[0]) continue;
        if (lstrcmpA(g_cry[i].id, "UDC") == 0) continue;
        if (fabsf(g_cry[i].basis_bps) > best_abs) {
            best_abs = fabsf(g_cry[i].basis_bps);
            best_i = i;
        }
    }
    if (best_i >= 0) {
        COLORREF col = CLR_TXT;
        lstrcpyW(tag, L"REGIME");
        if (fabsf(g_cry[best_i].basis_bps) >= 25.0f) {
            col = CLR_ACC;
            lstrcpyW(tag, L"ACTIONABLE");
        } else if (fabsf(g_cry[best_i].basis_bps) >= 12.0f) {
            col = CLR_OFF;
            lstrcpyW(tag, L"WATCH");
        }
        ui_fmt_wdouble(v, 16, g_cry[best_i].basis_bps, 1);
        wsprintfW(line, L"CEX basis %hs  %s bp  [%s]",
                  g_cry[best_i].id, v, tag);
        ui_label_rect(dc, &row, line, col, fSm);
        row.top += 15;
        row.bottom += 15;
        drew = 1;
        if (!signal_row_fit(&row, &r)) return;
        wsprintfW(line, L"  Binance-Kraken  fee~10bp/lato  soglia arb 25bp");
        ui_label_rect(dc, &row, line, CLR_DIM, fSm);
        row.top += 15;
        row.bottom += 15;
    }

    crypto_spread_eth_btc(st, &sp, &ch);
    if (sp > 0.0f && signal_row_fit(&row, &r)) {
        drew = 1;
        ui_fmt_wdouble(v, 16, sp, 5);
        ui_fmt_wdouble(c, 16, ch * 100.0f, 2);
        wsprintfW(line, L"ETH/BTC  %s  d %s%%  [risk-on alt beta]", v, c);
        ui_label_rect(dc, &row, line, CLR_TXT, fSm);
        if (data_series_snap("ETH", &eth) && data_series_snap("BTC", &btc) && eth.n >= 10) {
            CorrPair cp;
            corr_pair_compute(&eth, &btc, &cp);
            if (cp.ok) {
                row.top += 15;
                row.bottom += 15;
                ui_fmt_wdouble(v, 16, cp.rho90, 2);
                ui_fmt_wdouble(c, 16, cp.beta90, 2);
                wsprintfW(line, L"  \x03C1 90d = %s   \x03B2 = %s", v, c);
                ui_label_rect(dc, &row, line, CLR_DIM, fSm);
            }
        }
        row.top += 15;
        row.bottom += 15;
    }

    {
        const CryptoQuote *btc = crypto_quote_id("BTC");
        const CryptoQuote *eth = crypto_quote_id("ETH");
        if (btc && btc->have_funding && signal_row_fit(&row, &r)) {
            drew = 1;
            COLORREF col = CLR_TXT;
            lstrcpyW(tag, L"REGIME");
            if (fabsf(btc->funding_pct) >= 0.03f) {
                col = CLR_ACC;
                lstrcpyW(tag, L"ACTIONABLE");
            } else if (fabsf(btc->funding_pct) >= 0.01f) {
                col = CLR_OFF;
                lstrcpyW(tag, L"WATCH");
            }
            ui_fmt_wdouble(v, 16, btc->funding_pct, 4);
            wsprintfW(line, L"Funding BTC  %s%% /8h  [%s]  longs pay shorts if +",
                      v, tag);
            ui_label_rect(dc, &row, line, col, fSm);
            row.top += 15;
            row.bottom += 15;
        }
        if (eth && eth->have_funding && signal_row_fit(&row, &r)) {
            drew = 1;
            COLORREF col = CLR_TXT;
            lstrcpyW(tag, L"REGIME");
            if (fabsf(eth->funding_pct) >= 0.03f) {
                col = CLR_ACC;
                lstrcpyW(tag, L"ACTIONABLE");
            } else if (fabsf(eth->funding_pct) >= 0.01f) {
                col = CLR_OFF;
                lstrcpyW(tag, L"WATCH");
            }
            ui_fmt_wdouble(v, 16, eth->funding_pct, 4);
            wsprintfW(line, L"Funding ETH  %s%% /8h  [%s]", v, tag);
            ui_label_rect(dc, &row, line, col, fSm);
            row.top += 15;
            row.bottom += 15;
        }
    }

    {
        const CryptoQuote *udc = crypto_quote_id("UDC");
        if (udc && udc->have && signal_row_fit(&row, &r)) {
            drew = 1;
            COLORREF col = CLR_TXT;
            lstrcpyW(tag, L"OK");
            if (fabsf(udc->basis_bps) >= 15.0f) {
                col = CLR_ACC;
                lstrcpyW(tag, L"ACTIONABLE");
            } else if (fabsf(udc->basis_bps) >= 8.0f) {
                col = CLR_OFF;
                lstrcpyW(tag, L"WATCH");
            }
            ui_fmt_wdouble(v, 16, udc->basis_bps, 1);
            wsprintfW(line, L"USDC depeg  %s bp  [%s]", v, tag);
            ui_label_rect(dc, &row, line, col, fSm);
            row.top += 15;
            row.bottom += 15;
        }
    }

    paint_macro_rho(dc, &row, &r, st, "BTC", "BRT", L"BTC vs Brent");
    paint_macro_rho(dc, &row, &r, st, "BTC", "CBE", L"BTC vs CBECI");
    paint_macro_rho(dc, &row, &r, st, "BTC", "CVI", L"BTC vs vol index");
    paint_macro_rho(dc, &row, &r, st, "GRN", "DIR", L"clean vs dirty");
    paint_macro_rho(dc, &row, &r, st, "GPR", "VIX", L"geopol vs fear");

    if (!drew && row.top == start.top) {
        ui_label_rect(dc, &row, L"attesa dati live / cache...", CLR_OFF, fSm);
    }
}

static void paint_cex_table(HDC dc, RECT tbl) {
    int y, i, row_h = 15;
    const wchar_t *hdr[7] = { L"COIN", L"BIN", L"KRK", L"BASIS", L"24h", L"FUND", L"FLAG" };
    static const int OFF[7] = { 0, 48, 108, 168, 228, 278, 338 };

    ui_subheading(dc, &(RECT){ tbl.left, tbl.top, tbl.right, tbl.top + 12 },
                  L"CEX LIVE");
    y = tbl.top + 14;
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    for (i = 0; i < 7; i++) {
        SetTextColor(dc, CLR_DIM);
        TextOutW(dc, tbl.left + OFF[i], y, hdr[i], lstrlenW(hdr[i]));
    }
    y += row_h + 2;
    ui_hline(dc, tbl.left, y - 2, tbl.right, CLR_GRID);

    for (i = 0; i < g_cry_n; i++) {
        const CryptoQuote *c = &g_cry[i];
        wchar_t nm[8], bn[14], kr[14], bs[10], ch[10], fd[10], flag[12];
        COLORREF row_c;

        if (y + row_h > tbl.bottom) break;
        if (!c->have) continue;

        nm[0] = (wchar_t)c->id[0];
        nm[1] = (wchar_t)c->id[1];
        nm[2] = (wchar_t)c->id[2];
        nm[3] = 0;
        ui_fmt_wdouble(bn, 14, c->usd_binance, c->usd_binance > 100.0f ? 0 : 3);
        if (c->usd_kraken > 0.0f)
            ui_fmt_wdouble(kr, 14, c->usd_kraken, c->usd_kraken > 100.0f ? 0 : 3);
        else
            lstrcpyW(kr, L"-");
        ui_fmt_wdouble(bs, 10, c->basis_bps, 1);
        ui_fmt_wdouble(ch, 10, c->chg_24h, 2);
        if (c->have_funding)
            ui_fmt_wdouble(fd, 10, c->funding_pct, 3);
        else
            lstrcpyW(fd, L"-");
        if (fabsf(c->basis_bps) >= 25.0f)
            lstrcpyW(flag, L"ARB");
        else if (fabsf(c->basis_bps) >= 12.0f)
            lstrcpyW(flag, L"watch");
        else
            lstrcpyW(flag, L"-");

        row_c = c->chg_24h >= 0.0f ? CLR_TXT : CLR_DN;
        if (fabsf(c->basis_bps) >= 25.0f) row_c = CLR_ACC;
        SetTextColor(dc, row_c);
        TextOutW(dc, tbl.left + OFF[0], y, nm, lstrlenW(nm));
        TextOutW(dc, tbl.left + OFF[1], y, bn, lstrlenW(bn));
        TextOutW(dc, tbl.left + OFF[2], y, kr, lstrlenW(kr));
        TextOutW(dc, tbl.left + OFF[3], y, bs, lstrlenW(bs));
        TextOutW(dc, tbl.left + OFF[4], y, ch, lstrlenW(ch));
        TextOutW(dc, tbl.left + OFF[5], y, fd, lstrlenW(fd));
        TextOutW(dc, tbl.left + OFF[6], y, flag, lstrlenW(flag));
        y += row_h;
    }
}

void crypto_paint_page(HDC dc, const RECT *rc, const SeriesStore *macro) {
    RECT r = *rc, net, bot, sig, tbl, sparks, cell;
    static const char *SPK[6] = { "BTC", "ETH", "SOL", "BNB", "XRP", "CVI" };
    int i, w3, spark_h = 92;
    DataSeries snap;

    if (g_cry_n <= 0) crypto_init();

    {
        RECT gloss = r;
        gloss.left = gloss.right - 228;
        r.right = gloss.left - 8;
        gloss_paint_panel(dc, &gloss, PAGE_RISK);
    }

    ui_subheading(dc, &(RECT){ r.left, r.top, r.right, r.top + 12 },
                  L"CRYPTO NETWORK");
    r.top += 14;
    net = r;
    net.bottom = r.top + (r.bottom - r.top) * 48 / 100;
    if (macro)
        chart_crypto_network(dc, &net, macro);

    bot = r;
    bot.top = net.bottom + 8;
    bot.bottom -= spark_h;
    sig = bot;
    sig.right = bot.left + (bot.right - bot.left) / 2 - 4;
    tbl = bot;
    tbl.left = sig.right + 8;
    paint_crypto_signals(dc, sig, macro);
    paint_cex_table(dc, tbl);

    sparks = r;
    sparks.top = r.bottom - spark_h;
    w3 = (sparks.right - sparks.left) / 3;
    for (i = 0; i < 6; i++) {
        cell.left = sparks.left + (i % 3) * w3;
        cell.right = sparks.left + (i % 3 + 1) * w3 - 4;
        cell.top = sparks.top + (i / 3) * 44;
        cell.bottom = cell.top + 40;
        if (data_series_snap(SPK[i], &snap) && snap.n >= 3)
            chart_series_cell(dc, &cell, &snap);
    }
    gloss_paint_footer(dc, &(RECT){ r.left, r.bottom - 14, r.right, r.bottom }, PAGE_RISK);
}
