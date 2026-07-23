#include "systemic.h"
#include "corr.h"
#include "fin.h"
#include <math.h>
#include <string.h>

static float series_chg_n(const DataSeries *s, int days) {
    int i, n;
    float last, prev;

    if (!s || s->n < 2) return 0.0f;
    n = s->n;
    last = s->val[n - 1];
    i = n - 1 - days;
    if (i < 0) i = 0;
    prev = s->val[i];
    if (prev <= 0.0f) return 0.0f;
    return (last - prev) / prev;
}

void systemic_compute(const SeriesStore *st, SystemicSnap *out) {
    static const char ENERGY_CRYPTO[][2][4] = {
        { "BTC", "BRT" }, { "BTC", "HUB" }, { "BTC", "TTF" },
        { "ETH", "BTC" }, { "BTC", "HYO" }, { "BTC", "XAU" },
        { "BTC", "CBE" }, { "BTC", "CVI" }, { "GPR", "VIX" }
    };
    DataSeries *vix, *hyo, *btc, *gpr, *cpu;
    float rho_sum = 0.0f;
    int rho_n = 0, i;

    if (!out) return;
    memset(out, 0, sizeof(*out));

    vix = series_get((SeriesStore *)st, "VIX");
    hyo = series_get((SeriesStore *)st, "HYO");
    btc = series_get((SeriesStore *)st, "BTC");
    gpr = series_get((SeriesStore *)st, "GPR");
    cpu = series_get((SeriesStore *)st, "CPU");

    if (vix && vix->n >= 20) out->vix_z = fin_level_zscore(vix, 90);
    if (hyo && hyo->n >= 6) out->hy_chg_5d = series_chg_n(hyo, 5) * 10000.0f;

    fin_yield_spread_bps(st, "U10", "U2", &out->curve_2s10s_bps);
    fin_yield_spread_bps(st, "U30", "U5", &out->curve_5s30s_bps);

    for (i = 0; i < (int)(sizeof(ENERGY_CRYPTO) / sizeof(ENERGY_CRYPTO[0])); i++) {
        DataSeries *sa = series_get((SeriesStore *)st, ENERGY_CRYPTO[i][0]);
        DataSeries *sb = series_get((SeriesStore *)st, ENERGY_CRYPTO[i][1]);
        CorrPair cp;

        if (!sa || !sb) continue;
        corr_pair_compute(sa, sb, &cp);
        if (!cp.ok) continue;
        rho_sum += fabsf(cp.rho90);
        rho_n++;
        if (fabsf(cp.rho90) > fabsf(out->hot_rho)) {
            out->hot_rho = cp.rho90;
            lstrcpynA(out->hot_a, ENERGY_CRYPTO[i][0], 4);
            lstrcpynA(out->hot_b, ENERGY_CRYPTO[i][1], 4);
        }
    }
    if (rho_n > 0) out->btc_energy_rho = rho_sum / (float)rho_n;

    out->stress = 0.0f;
    if (out->vix_z > 0.0f) out->stress += out->vix_z * 12.0f;
    if (gpr && gpr->n >= 20) {
        float gz = fin_level_zscore(gpr, 90);
        if (gz > 0.0f) out->stress += gz * 8.0f;
    }
    if (cpu && cpu->n >= 6) {
        float cpu_chg = series_chg_n(cpu, 22);
        if (cpu_chg > 0.0f) out->stress += cpu_chg * 120.0f;
    }
    if (out->hy_chg_5d > 0.0f) out->stress += out->hy_chg_5d * 0.8f;
    out->stress += out->btc_energy_rho * 25.0f;
    if (out->curve_2s10s_bps < 0.0f)
        out->stress += (-out->curve_2s10s_bps) * 0.15f;
    if (out->curve_5s30s_bps < -25.0f)
        out->stress += (-out->curve_5s30s_bps - 25.0f) * 0.08f;
    if (out->stress > 100.0f) out->stress = 100.0f;
    if (out->stress < 0.0f) out->stress = 0.0f;

    out->ok = (vix && vix->n >= 10) || (btc && btc->n >= 10);
}

void systemic_paint_banner(HDC dc, const RECT *rc, const SeriesStore *st) {
    SystemicSnap snap;
    RECT r = *rc, bar;
    wchar_t line[220], v[16], h[16], z[16];
    COLORREF col;
    int pct, bw;

    if (!st || r.right <= r.left + 40) return;
    systemic_compute(st, &snap);

    ui_subheading(dc, &(RECT){ r.left, r.top, r.right, r.top + 12 },
                  L"SISTEMICO  spillover energia-crypto-credit (letteratura 2023-26)");
    r.top += 14;

    pct = (int)(snap.stress + 0.5f);
    if (pct < 15) col = CLR_UP;
    else if (pct < 45) col = CLR_TXT;
    else if (pct < 70) col = CLR_OFF;
    else col = CLR_DN;

    bar = r;
    bar.bottom = bar.top + 10;
    ui_fill(dc, &bar, bGray);
    bw = (bar.right - bar.left) * pct / 100;
    if (bw > 0) {
        RECT fill = bar;
        HBRUSH br = CreateSolidBrush(col);
        fill.right = fill.left + bw;
        ui_fill(dc, &fill, br);
        DeleteObject(br);
    }

    ui_fmt_wdouble(z, 16, snap.vix_z, 2);
    ui_fmt_wdouble(h, 16, snap.hy_chg_5d, 0);
    ui_fmt_wdouble(v, 16, snap.btc_energy_rho, 2);
    wsprintfW(line,
        L"stress %d%%  VIX z=%s  HY \x0394 5d %s bp  mean|BTC-energy \x03C1|=%s  2s10s %+.0fbp",
        pct, z, h, v, snap.curve_2s10s_bps);
    ui_label_rect(dc, &(RECT){ r.left, bar.bottom + 4, r.right, r.bottom },
                  line, col, fSm);

    if (snap.hot_a[0]) {
        wchar_t extra[96], rs[12];
        ui_fmt_wdouble(rs, 12, snap.hot_rho, 2);
        wsprintfW(extra, L"  hot pair %hs-%hs \x03C1 90d=%s", snap.hot_a, snap.hot_b, rs);
        SetTextColor(dc, CLR_DIM);
        TextOutW(dc, r.left, r.bottom - 12, extra, lstrlenW(extra));
    }
}
