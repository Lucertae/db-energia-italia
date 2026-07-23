#include "forcing.h"
#include "sole.h"
#include "moon.h"
#include "lab.h"
#include "chart.h"
#include "data.h"
#include <stdio.h>
#include <string.h>

static const wchar_t *gic_level(float kp) {
    if (kp >= 7.0f) return L"ALTO";
    if (kp >= 5.0f) return L"MEDIO";
    return L"BASSO";
}

static void paint_storm_timeline(HDC dc, const RECT *rc) {
    float buf[90];
    DataSeries vix, pde;
    int i, n = 90;

    memset(buf, 0, sizeof(buf));
    if (data_series_snap("VIX", &vix) && vix.n > 1) {
        int start = vix.n > n ? vix.n - n : 0;
        int len = vix.n - start;
        if (len > n) len = n;
        for (i = 0; i < len; i++)
            buf[i] += vix.val[start + i] / 40.0f;
    }
    if (data_series_snap("PDE", &pde) && pde.n > 1) {
        int start = pde.n > n ? pde.n - n : 0;
        int len = pde.n - start;
        if (len > n) len = n;
        for (i = 0; i < len; i++)
            buf[i] += pde.val[start + i] / 300.0f;
    }
    chart_calendar_heatmap(dc, rc, buf, 6, 15, 0.0f, 2.5f, L"VIX+PDE overlay 90gg");
}

void forcing_paint(HDC dc, const RECT *rc) {
    SoleState sole_snap;
    const SoleState *ss;
    const MoonState *ms = moon_state();
    RECT r = *rc, left, right, lbot, rbot, lbot_in;
    int y, lh = 13;

    sole_copy(&sole_snap);
    ss = &sole_snap;

    left = r;
    left.right = r.left + (r.right - r.left) * 55 / 100;
    right = r;
    right.left = left.right + 8;
    lbot = left;
    lbot.top = left.top + (left.bottom - left.top) * 58 / 100;
    rbot = right;
    rbot.top = right.top + (right.bottom - right.top) * 48 / 100;

    ui_frame(dc, &left, L"SPACE WEATHER");
    {
        RECT inner = ui_panel_body(&left);
        inner.bottom = lbot.top - 6;
        y = inner.top;
        if (ss->space.ok) {
            wchar_t gic[64];
            wsprintfW(gic, L"Rischio grid GIC: %s  (Kp=%.1f)",
                      gic_level(ss->space.kp), ss->space.kp);
            SetTextColor(dc, ss->space.kp >= 7.0f ? CLR_DN :
                (ss->space.kp >= 5.0f ? RGB(255, 180, 80) : CLR_UP));
            SelectObject(dc, fLbl);
            TextOutW(dc, inner.left, y, gic, lstrlenW(gic));
            y += lh + 4;
            chart_gauge(dc, &(RECT){ inner.left, y, inner.right, y + 22 },
                        ss->space.kp, 0.0f, 5.0f, 9.0f, L"Kp", L"");
            y += 26;
            chart_gauge(dc, &(RECT){ inner.left, y, inner.right, y + 22 },
                        ss->space.dst, -200.0f, -50.0f, 0.0f, L"Dst", L" nT");
            y += 26;
            chart_gauge(dc, &(RECT){ inner.left, y, inner.right, y + 22 },
                        ss->space.bz_nt, -10.0f, 0.0f, 10.0f, L"Bz", L" nT");
            y += 26;
            chart_gauge(dc, &(RECT){ inner.left, y, inner.right, y + 22 },
                        ss->space.wind_kms, 300.0f, 500.0f, 800.0f, L"Vento solare", L" km/s");
            y += 28;
            if (ss->space.f107 > 0.0f) {
                chart_gauge(dc, &(RECT){ inner.left, y, inner.right, y + 22 },
                            ss->space.f107, 60.0f, 120.0f, 220.0f, L"F10.7", L" sfu");
                y += 26;
                chart_gauge(dc, &(RECT){ inner.left, y, inner.right, y + 22 },
                            ss->space.tsi_wm2, 1360.0f, 1361.0f, 1363.0f, L"TSI proxy", L" W/m2");
            }
        } else {
            SetTextColor(dc, CLR_OFF);
            TextOutW(dc, inner.left, y, L"space weather loading...", 24);
        }
    }

    ui_frame(dc, &lbot, L"STORICO 90gg  overlay visivo");
    lbot_in = ui_panel_body(&lbot);
    paint_storm_timeline(dc, &lbot_in);

    ui_frame(dc, &right, L"LUNA  forcing mareale");
    {
        RECT inner = ui_panel_body(&right);
        inner.bottom = rbot.top - 6;
        y = inner.top;
        if (ms) {
            RECT gauge = inner;
            SetTextColor(dc, CLR_TXT);
            SelectObject(dc, fSm);
            TextOutW(dc, inner.left, y, ms->name, lstrlenW(ms->name));
            y += lh;
            TextOutW(dc, inner.left, y, ms->line1, lstrlenW(ms->line1));
            y += lh;
            gauge.top = y + 4;
            gauge.bottom = gauge.top + 22;
            chart_gauge(dc, &gauge, (float)ms->illum, 0.0f, 0.5f, 1.0f, L"Illuminazione", L"");
            y = gauge.bottom + 8;
            TextOutW(dc, inner.left, y, ms->tidal_note, lstrlenW(ms->tidal_note));
            y += lh;
            TextOutW(dc, inner.left, y, ms->tide_pwr_note, lstrlenW(ms->tide_pwr_note));
            y += lh;
            {
                wchar_t tidal[64];
                wsprintfW(tidal, L"tidal gen stim UK/FR coef %.2f", ms->tidal_coef);
                TextOutW(dc, inner.left, y, tidal, lstrlenW(tidal));
            }
        } else {
            SetTextColor(dc, CLR_OFF);
            TextOutW(dc, inner.left, y, L"moon state pending", 18);
        }
    }

    ui_frame(dc, &rbot, L"IPOTESI IN TEST  (LAB gate)");
    {
        RECT inner = ui_panel_body(&rbot);
        int i, n;
        y = inner.top;
        n = lab_row_count();
        SetTextColor(dc, CLR_DIM);
        SelectObject(dc, fSm);
        for (i = 0; i < n && i < 2 && y + lh <= inner.bottom; i++) {
            wchar_t sum[220];
            lab_row_summary(i, sum, 220);
            TextOutW(dc, inner.left, y, sum, lstrlenW(sum));
            y += lh;
        }
        if (y + lh <= inner.bottom) {
            TextOutW(dc, inner.left, y,
                     L"LUN-01 illum->domanda notturna | raccolta dati | monitor sì trade no",
                     -1);
            y += lh;
        }
        if (y + lh <= inner.bottom) {
            SetTextColor(dc, CLR_OFF);
            TextOutW(dc, inner.left, y,
                     L"POV: forcing esogeno strumentato — catena causale dichiarata, gate LAB",
                     -1);
        }
    }
}
