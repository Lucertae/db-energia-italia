#include "data.h"
#include "ingest.h"
#include "ingest_entsoe.h"
#include "ingest_libero.h"
#include "keys.h"
#include "sources.h"
#include "histdb.h"
#include "fetch_pool.h"
#include "companies.h"
#include "production.h"
#include "countries.h"
#include "ships.h"
#include "chokepoints.h"
#include "ingest_intel.h"
#include "ingest_view.h"
#include "globe_view.h"
#include "intel.h"
#include "spine.h"
#include "sole.h"
#include "weather.h"
#include "arena.h"
#include "corr.h"
#include "crypto.h"
#include <process.h>
#include <stdlib.h>
#include <string.h>

#define DATA_ECB_URL     L"https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml"
#define DATA_FETCH_SEC   120
#define DATA_RETRY_SEC   20
#define DATA_HIST_SEC    (20 * 3600)
#define DATA_HIST_DAYS   1900
#define POOL_BODY_CAP    (96 * 1024)

static SigBus g_bus;
static SeriesStore g_store;
static CRITICAL_SECTION g_lock;
static wchar_t g_status[200];
static volatile LONG g_fetching;
static volatile LONG g_have_data;
static volatile LONG g_do_hist;
static volatile LONG g_do_co;
static volatile LONG g_do_prod;
static volatile LONG g_do_crypto;
static volatile LONG g_do_intel;
static uint32_t g_last_fetch;
static uint32_t g_last_attempt;
static uint32_t g_last_hist;
static uint32_t g_fx_pairs;
static uint32_t g_fred_ok;
static double g_ratio;
static double g_noise_bp;

static uint32_t epoch_sec(void) {
    FILETIME ft;
    ULARGE_INTEGER u;

    GetSystemTimeAsFileTime(&ft);
    u.LowPart = ft.dwLowDateTime;
    u.HighPart = ft.dwHighDateTime;
    return (uint32_t)((u.QuadPart - 116444736000000000ULL) / 10000000ULL);
}

static uint32_t today_ymd(void) {
    SYSTEMTIME st;

    GetSystemTime(&st);
    return (uint32_t)(st.wYear * 10000u + st.wMonth * 100u + st.wDay);
}

typedef struct {
    char id[4];
    double v;
} FxTick;

typedef struct {
    FxTick tick[64];
    int n;
} FxBatch;

static void push_scalar(const char *id, double v) {
    if (v > 0.0) sig_push(&g_bus, id, v, epoch_sec());
}

static void ecb_touch_series(const char *id, double v) {
    DataSeries *d;
    wchar_t lbl[14];

    wsprintfW(lbl, L"EUR/%hs", id);
    d = series_add(&g_store, id, lbl, SER_FX);
    if (!d) return;
    series_touch_day(d, today_ymd(), (float)v);
}

static int sources_fred_active(void) {
    int i, n = 0;

    for (i = 0; i < g_sources_n; i++)
        if (g_sources[i].backend == SRC_FRED && !(g_sources[i].flags & SRC_FLAG_DISABLED))
            n++;
    return n;
}

static void refresh_status(int ecb_ok, int fred_n, int hist_age_h) {
    double brt = sig_value(&g_bus, "BRT");
    wchar_t brt_s[16];

    if (!ecb_ok && fred_n == 0 && g_fred_ok == 0) {
        wsprintfW(g_status,
            L"DATA err HTTP %u  winerr %u  retry %us",
            ingest_last_status(), ingest_last_error(), DATA_RETRY_SEC);
        return;
    }
    ui_fmt_wdouble(brt_s, 16, brt, 1);
    {
        wchar_t kbuf[80];
        keys_status_line(kbuf, (int)(sizeof(kbuf) / sizeof(kbuf[0])));
        wsprintfW(g_status,
            L"ECB %u  FRED %u/%u  PWR %s  %dh  BRT %s  %s",
            g_fx_pairs, g_fred_ok, sources_fred_active(),
            keys_have("entsoe") ? L"live" : L"cache",
            hist_age_h, brt_s, kbuf);
    }

    {
        static const char PAIRS[][2][4] = {
            { "BRT", "WTI" }, { "TTF", "HUB" }, { "BRT", "VIX" },
            { "CPR", "BRT" }, { "BRT", "SPX" }, { "JKM", "TTF" },
            { "TTF", "PDE" }, { "BRT", "PDE" }, { "BTC", "BRT" },
            { "BTC", "HUB" }, { "BTC", "HYO" }, { "ETH", "BTC" }
        };
        char ca[4], cb[4];
        float rho;
        wchar_t extra[64], rs[12];

        if (corr_strongest(&g_store, PAIRS, 12, ca, cb, &rho)) {
            ui_fmt_wdouble(rs, 12, rho, 2);
            wsprintfW(extra, L"  |  max|\x03C1| %hs-%hs %s", ca, cb, rs);
            if (lstrlenW(g_status) + lstrlenW(extra) < (int)(sizeof(g_status) / sizeof(wchar_t)) - 1)
                lstrcatW(g_status, extra);
        }
    }
}

static void fx_collect(const char *iso3, double rate, void *ctx) {
    FxBatch *b = (FxBatch *)ctx;
    int i;

    if (b->n >= 64) return;
    i = b->n++;
    b->tick[i].id[0] = iso3[0];
    b->tick[i].id[1] = iso3[1];
    b->tick[i].id[2] = iso3[2];
    b->tick[i].id[3] = 0;
    b->tick[i].v = rate;
}

static void register_series_catalog(void) {
    static const struct { const char *id; const wchar_t *lbl; } CROSS[] = {
        { "USD", L"EUR/USD" }, { "JPY", L"EUR/JPY" }, { "GBP", L"EUR/GBP" },
        { "BRL", L"EUR/BRL" }, { "ZAR", L"EUR/ZAR" }, { "INR", L"EUR/INR" },
        { "CNY", L"EUR/CNY" }, { "MXN", L"EUR/MXN" },
        { "ENK", L"EUR/NOK" }, { "ESK", L"EUR/SEK" }, { "NZD", L"EUR/NZD" },
    };
    static const struct { const char *id; const wchar_t *lbl; } PWR[] = {
        { "PDE", L"PWR DE" }, { "PFR", L"PWR FR" }, { "PIT", L"PWR IT" },
        { "PNL", L"PWR NL" }, { "PPL", L"PWR PL" }, { "PNO", L"PWR NO" },
        { "PAT", L"PWR AT" },
    };
    int i;

    for (i = 0; i < g_sources_n; i++)
        series_add(&g_store, g_sources[i].id, g_sources[i].label, g_sources[i].ser_kind);
    for (i = 0; i < (int)(sizeof(CROSS) / sizeof(CROSS[0])); i++)
        series_add(&g_store, CROSS[i].id, CROSS[i].lbl, SER_FX);
    for (i = 0; i < (int)(sizeof(PWR) / sizeof(PWR[0])); i++)
        series_add(&g_store, PWR[i].id, PWR[i].lbl, SER_ENERGY);
}

/*
 * EUR crosses from FRED USD legs:
 *   quote_per_usd (BRL, ZAR, INR, CNY, MXN, JPY): EUR/X = X_per_USD * USD_per_EUR
 *   usd_per_quote (GBP): EUR/X = USD_per_EUR / USD_per_X
 * Aligned on matching dates (two-pointer over ascending ymd).
 * Must be called with g_lock held.
 */
static void derive_cross(const char *dst, const char *src, int usd_per_quote) {
    static uint32_t ymd[SER_POINTS];
    static float val[SER_POINTS];
    DataSeries *eur = series_get(&g_store, "EUF");
    DataSeries *leg = series_get(&g_store, src);
    int i = 0, j = 0, n = 0;
    float live;

    if (!eur || eur->n < 2) return;

    if (strcmp(dst, "USD") == 0) {
        series_load(&g_store, "USD", eur->ymd, eur->val, eur->n, eur->live);
        return;
    }
    if (!leg || leg->n < 2) return;

    while (i < eur->n && j < leg->n && n < SER_POINTS) {
        if (eur->ymd[i] == leg->ymd[j]) {
            ymd[n] = eur->ymd[i];
            val[n] = usd_per_quote ? eur->val[i] / leg->val[j]
                                   : leg->val[j] * eur->val[i];
            n++;
            i++;
            j++;
        } else if (eur->ymd[i] < leg->ymd[j]) {
            i++;
        } else {
            j++;
        }
    }
    if (n < 2) return;
    live = usd_per_quote ? eur->live / leg->live : leg->live * eur->live;
    series_load(&g_store, dst, ymd, val, n, live);
}

static void derive_all_crosses(void) {
    derive_cross("USD", "EUF", 0);
    derive_cross("JPY", "JPF", 0);
    derive_cross("BRL", "BRF", 0);
    derive_cross("ZAR", "ZAF", 0);
    derive_cross("INR", "INF", 0);
    derive_cross("CNY", "CNF", 0);
    derive_cross("MXN", "MXF", 0);
    derive_cross("GBP", "GBF", 1);
    derive_cross("NZD", "NZF", 1);
    derive_cross("ENK", "NOK", 0);
    derive_cross("ESK", "SEK", 0);
}

static int hist_apply_id(const char *id, const char *body, size_t len) {
    static uint32_t ymd[SER_POINTS];
    static float val[SER_POINTS];
    float live = 0.0f;
    double last = 0.0;
    int n;

    n = ingest_fred_hist(body, len, ymd, val, SER_POINTS);
    if (n <= 0) return 0;
    if (ingest_fred_last(body, len, &last))
        live = (float)last;
    EnterCriticalSection(&g_lock);
    series_load(&g_store, id, ymd, val, n, live);
    if (live > 0.0f) push_scalar(id, live);
    LeaveCriticalSection(&g_lock);
    return 1;
}

static int hist_apply_csv(const SourceDef *def, const char *body, size_t len) {
    return hist_apply_id(def->id, body, len);
}

static int local_power_load(void) {
    static const char *IDS[] = {
        "PDE", "PFR", "PIT", "PNL", "PPL", "PNO", "PAT", "HAS", "XAU"
    };
    static char body[INGEST_BODY_MAX];
    int i, ok = 0;
    size_t len;

    for (i = 0; i < (int)(sizeof(IDS) / sizeof(IDS[0])); i++) {
        if (histdb_load(IDS[i], body, sizeof(body), &len, 0) &&
            hist_apply_id(IDS[i], body, len))
            ok++;
    }
    return ok;
}

static int libero_apply_all(void) {
    static const char *IDS[] = {
        "CBE", "EMI", "CVI", "FEE", "DIF", "REV", "HAS", "BVL", "MCP",
        "GPR", "CPU", "EUA", "GRN", "DIR", "NGF"
    };
    static char body[INGEST_BODY_MAX];
    int i, ok = 0;
    size_t len;

    for (i = 0; i < (int)(sizeof(IDS) / sizeof(IDS[0])); i++) {
        if (histdb_load(IDS[i], body, sizeof(body), &len, 0) &&
            hist_apply_id(IDS[i], body, len))
            ok++;
    }
    return ok;
}

static int hist_refresh(IngestSession *sess) {
    static char body[INGEST_BODY_MAX];
    const SourceDef **need = NULL;
    char *bodies = NULL;
    wchar_t url[512];
    size_t len;
    int i, k, off, nneed = 0, ok = 0;

    histdb_init();

    for (i = 0; i < g_sources_n; i++) {
        const SourceDef *def = &g_sources[i];

        if (def->backend != SRC_FRED || (def->flags & SRC_FLAG_DISABLED) || !def->fred_id)
            continue;
        if (histdb_load(def->id, body, sizeof(body), &len, DATA_HIST_SEC) &&
            hist_apply_csv(def, body, len)) {
            ok++;
            continue;
        }
        nneed++;
    }

    if (nneed > 0) {
        need = (const SourceDef **)malloc((size_t)nneed * sizeof(need[0]));
        bodies = (char *)malloc((size_t)nneed * POOL_BODY_CAP);
        if (need && bodies) {
            int j = 0;
            for (i = 0; i < g_sources_n; i++) {
                const SourceDef *def = &g_sources[i];
                if (def->backend != SRC_FRED || (def->flags & SRC_FLAG_DISABLED) || !def->fred_id)
                    continue;
                if (histdb_load(def->id, body, sizeof(body), &len, DATA_HIST_SEC) &&
                    hist_apply_csv(def, body, len))
                    continue;
                need[j++] = def;
            }
            for (off = 0; off < nneed; off += FETCH_POOL_MAX) {
                FetchPool pool;
                int batch = nneed - off;

                if (batch > FETCH_POOL_MAX) batch = FETCH_POOL_MAX;
                fetch_pool_init(&pool);
                for (k = 0; k < batch; k++) {
                    ingest_fred_url(need[off + k]->fred_id, DATA_HIST_DAYS, url,
                                    (int)(sizeof(url) / sizeof(url[0])));
                    fetch_pool_add(&pool, url, bodies + (size_t)(off + k) * POOL_BODY_CAP,
                                   POOL_BODY_CAP);
                }
                fetch_pool_run(&pool, sess);
                for (k = 0; k < batch; k++) {
                    FetchSlot *slot = &pool.slot[k];
                    const SourceDef *def = need[off + k];

                    if (slot->ok && hist_apply_csv(def, slot->body, slot->len)) {
                        histdb_save(def->id, slot->body, slot->len);
                        ok++;
                        continue;
                    }
                    if (histdb_load(def->id, body, sizeof(body), &len, 0) &&
                        hist_apply_csv(def, body, len))
                        ok++;
                }
            }
        }
        free(need);
        free(bodies);
    }

    for (i = 0; i < g_sources_n; i++) {
        const SourceDef *def = &g_sources[i];

        if (def->backend != SRC_EIA || (def->flags & SRC_FLAG_DISABLED))
            continue;
        if (histdb_load(def->id, body, sizeof(body), &len, 0) &&
            hist_apply_id(def->id, body, len))
            ok++;
    }
    return ok;
}

static unsigned __stdcall fetch_worker(void *arg) {
    static char body[INGEST_BODY_MAX];
    FxBatch fx = { 0 };
    size_t len = 0;
    int pairs = 0, i, hist_n = -1, ecb_ok = 0, hist_age_h;
    IngestSession *sess;
    uint32_t ts;

    (void)arg;
    arena_reset();
    ts = epoch_sec();
    g_last_attempt = ts;

    sess = ingest_session_open();
    if (!sess) {
        EnterCriticalSection(&g_lock);
        wsprintfW(g_status, L"DATA err: WinHTTP init %u", GetLastError());
        LeaveCriticalSection(&g_lock);
        PostMessageW(g_hwnd, WM_APP_DATA_READY, 0, 0);
        InterlockedExchange(&g_fetching, 0);
        return 0;
    }

    if (InterlockedCompareExchange(&g_do_hist, 0, 1) == 1) {
        hist_n = hist_refresh(sess);
        if (hist_n > 0) {
            g_fred_ok = (uint32_t)hist_n;
            g_last_hist = epoch_sec();
        } else {
            g_last_hist = epoch_sec() - DATA_HIST_SEC + 900;
        }
        if (ingest_entsoe_have_key())
            ingest_entsoe_refresh(sess);
        local_power_load();
    }

    {
        int lr;
        lr = ingest_libero_refresh(LIBERO_REFRESH_SEC);
        lr += libero_apply_all();
        if (lr > 0 && hist_n <= 0)
            hist_n = lr;
        else if (lr > 0)
            hist_n += lr;
    }

    if (ingest_session_get(sess, DATA_ECB_URL, body, sizeof(body), &len)) {
        pairs = ingest_ecb_fx(body, len, fx_collect, &fx);
        ecb_ok = pairs > 0;
    }
    ingest_session_close(sess);

    EnterCriticalSection(&g_lock);
    derive_all_crosses();
    if (ecb_ok) {
        for (i = 0; i < fx.n; i++) {
            push_scalar(fx.tick[i].id, fx.tick[i].v);
            ecb_touch_series(fx.tick[i].id, fx.tick[i].v);
        }
        g_fx_pairs = (uint32_t)pairs;
    }
    if (ecb_ok || hist_n > 0)
        g_last_fetch = ts;
    sig_stats(&g_bus, &g_ratio, &g_noise_bp);
    hist_age_h = g_last_hist ? (int)((epoch_sec() - g_last_hist) / 3600) : -1;
    refresh_status(ecb_ok, hist_n > 0 ? hist_n : 0, hist_age_h);
    LeaveCriticalSection(&g_lock);

    if (InterlockedExchange(&g_do_co, 0)) companies_refresh();
    if (InterlockedExchange(&g_do_prod, 0)) production_refresh();
    if (InterlockedExchange(&g_do_crypto, 0)) crypto_refresh();

    if (InterlockedExchange(&g_do_intel, 0)) {
        ingest_intel_refresh(PORTWATCH_REFRESH_SEC, INTEL_REFRESH_SEC);
        spine_spawn_build();
    }

    spine_reload();

    EnterCriticalSection(&g_lock);
    crypto_merge_series(&g_store);
    if (ecb_ok || g_fred_ok > 0)
        InterlockedExchange(&g_have_data, 1);
    LeaveCriticalSection(&g_lock);

    PostMessageW(g_hwnd, WM_APP_DATA_READY, 0, 0);
    InterlockedExchange(&g_fetching, 0);
    return 0;
}

static void schedule_fetch(void) {
    uintptr_t h;

    if (InterlockedCompareExchange(&g_fetching, 1, 0) != 0) return;
    h = _beginthreadex(NULL, 0, fetch_worker, NULL, 0, NULL);
    if (h) CloseHandle((HANDLE)h);
    else InterlockedExchange(&g_fetching, 0);
}

void data_init(void) {
    InitializeCriticalSection(&g_lock);
    sig_bus_init(&g_bus);
    series_init(&g_store);
    register_series_catalog();
    companies_init();
    production_init();
    production_refresh();
    countries_init();
    chokepoints_init();
    spine_init();
    ingest_view_init();
    globe_view_init();
    intel_desk_reload();
    ships_init();
    sole_init();
    weather_init();
    crypto_init();
    lstrcpyW(g_status, L"DATA loading (ECB live + FRED 5y)...");
    InterlockedExchange(&g_do_hist, 1);
    InterlockedExchange(&g_do_co, 0);
    InterlockedExchange(&g_do_prod, 1);
    InterlockedExchange(&g_do_crypto, 1);
    InterlockedExchange(&g_do_intel, 1);
    schedule_fetch();
}

void data_shutdown(void) {
    weather_shutdown();
    sole_shutdown();
    ships_shutdown();
    DeleteCriticalSection(&g_lock);
}

void data_on_ready(void) {
    static int once;

    spine_reload();
    intel_desk_reload();
    ingest_view_reload();
    if (!once) {
        once = 1;
        InterlockedExchange(&g_do_co, 1);
        InterlockedExchange(&g_do_prod, 1);
        InterlockedExchange(&g_do_crypto, 1);
        schedule_fetch();
    }
    InvalidateRect(g_hwnd, NULL, FALSE);
}

void data_tick(void) {
    uint32_t now = epoch_sec();
    uint32_t interval;
    int need_hist;

    interval = g_have_data ? DATA_FETCH_SEC : DATA_RETRY_SEC;
    need_hist = !g_last_hist || (now - g_last_hist) >= DATA_HIST_SEC;
    if (!need_hist && g_last_attempt && (now - g_last_attempt) < interval) return;
    if (need_hist)
        InterlockedExchange(&g_do_hist, 1);
    if (g_have_data && (now % 900u) < 2u)
        InterlockedExchange(&g_do_co, 1);
    if (g_have_data && (now % 3600u) < 2u)
        InterlockedExchange(&g_do_prod, 1);
    if (g_have_data && (now % 300u) < 2u)
        InterlockedExchange(&g_do_crypto, 1);
    if (g_have_data && (now % 300u) < 2u)
        InterlockedExchange(&g_do_intel, 1);
    schedule_fetch();
}

void data_kick_intel(void) {
    InterlockedExchange(&g_do_intel, 1);
    schedule_fetch();
}

double data_sig(const char *id) {
    double v;

    EnterCriticalSection(&g_lock);
    v = sig_value(&g_bus, id);
    LeaveCriticalSection(&g_lock);
    return v;
}

BOOL data_series_snap(const char *id, DataSeries *out) {
    DataSeries *d;
    BOOL ok = FALSE;

    if (!out) return FALSE;
    EnterCriticalSection(&g_lock);
    d = series_get(&g_store, id);
    if (d) {
        *out = *d;
        ok = TRUE;
    }
    LeaveCriticalSection(&g_lock);
    return ok;
}

void data_store_read(void (*fn)(const SeriesStore *, void *), void *ctx) {
    if (!fn) return;
    EnterCriticalSection(&g_lock);
    fn(&g_store, ctx);
    LeaveCriticalSection(&g_lock);
}

void data_paint_lines(HDC dc, int x, int y, int w, int max_y) {
    RECT line_rc;
    wchar_t buf[120];
    wchar_t u[16], b[16], t[16], r[16];
    const int lh = 15;
    double usd, brt, ttf, u10;

    if (y + lh > max_y) return;
    usd = data_sig("USD");
    brt = data_sig("BRT");
    ttf = data_sig("TTF");
    u10 = data_sig("U10");

    line_rc = (RECT){ x, y, x + w, y + lh };
    if (usd > 0.0) {
        ui_fmt_wdouble(u, 16, usd, 4);
        ui_fmt_wdouble(b, 16, brt, 1);
        ui_fmt_wdouble(t, 16, ttf, 1);
        ui_fmt_wdouble(r, 16, u10, 2);
        wsprintfW(buf, L"LIVE  EUR/USD %s  BRENT %s  TTF %s  US10Y %s%%", u, b, t, r);
    } else
        lstrcpyW(buf, L"MARKET loading...");
    ui_label_rect(dc, &line_rc, buf, CLR_DIM, fLbl);
}

void data_paint_footer(HDC dc, const RECT *rc) {
    wchar_t line[200];

    EnterCriticalSection(&g_lock);
    lstrcpyW(line, g_status);
    LeaveCriticalSection(&g_lock);
    ui_label_rect(dc, rc, line, CLR_DIM, fMono);
}

const SigBus *data_bus(void) {
    return &g_bus;
}

const wchar_t *data_status(void) {
    return g_status;
}
