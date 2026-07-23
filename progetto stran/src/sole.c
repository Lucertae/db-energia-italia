#include "sole.h"
#include "ingest_sole.h"
#include "ingest_inet.h"
#include "pages.h"
#include "time.h"
#include <process.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

#define SOLE_BODY_MAX    (128 * 1024)
#define SOLE_SPACE_SEC   900
#define SOLE_ATMO_SEC    600
#define SOLE_TOA_SCALE   3.14159265358979 * 6371000.0 * 6371000.0

static const wchar_t *SOLE_URL_KP =
    L"https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json";
static const wchar_t *SOLE_URL_DST =
    L"https://services.swpc.noaa.gov/products/kyoto-dst.json";
static const wchar_t *SOLE_URL_WIND =
    L"https://services.swpc.noaa.gov/products/summary/solar-wind-speed.json";
static const wchar_t *SOLE_URL_MAG =
    L"https://services.swpc.noaa.gov/products/summary/solar-wind-mag-field.json";
static const wchar_t *SOLE_URL_F107 =
    L"https://services.swpc.noaa.gov/products/summary/10cm-flux.json";
static const wchar_t *SOLE_URL_XRAY =
    L"https://services.swpc.noaa.gov/json/goes/primary/xray-flares-latest.json";
static const wchar_t *SOLE_URL_ACE =
    L"https://services.swpc.noaa.gov/text/ace-swepam.txt";

static const struct {
    int clk;
    const wchar_t *abbr;
    double lat;
    double lon;
} SOLE_HUBS[SOLE_HUB_N] = {
    { I_LON, L"LON", 51.5072, -0.1276 },
    { I_NYC, L"NYC", 40.7128, -74.0060 },
    { I_DXB, L"DXB", 25.2048,  55.2708 },
    { I_TYO, L"TYO", 35.6762, 139.6503 },
};

static SoleState g_sole;
static CRITICAL_SECTION g_lock;
static volatile LONG g_run;
static HANDLE g_thread;
static uint32_t g_last_space;
static uint32_t g_last_atmo;

static uint32_t epoch_sec(void) {
    FILETIME ft;
    ULARGE_INTEGER u;

    GetSystemTimeAsFileTime(&ft);
    u.LowPart = ft.dwLowDateTime;
    u.HighPart = ft.dwHighDateTime;
    return (uint32_t)((u.QuadPart - 116444736000000000ULL) / 10000000ULL);
}

static float tsi_from_f107(float f107) {
    return 1360.85f + (f107 - 67.0f) * 0.0072f;
}

static void cycle_from_f107(float f107, wchar_t *out, int cap) {
    if (f107 < 80.0f)
        lstrcpynW(out, L"Ciclo 25  minimo / uscita", cap);
    else if (f107 < 120.0f)
        lstrcpynW(out, L"Ciclo 25  ascendente", cap);
    else if (f107 < 170.0f)
        lstrcpynW(out, L"Ciclo 25  verso massimo", cap);
    else
        lstrcpynW(out, L"Ciclo 25  massimo attivo", cap);
}

static void carrington_label(float kp, float dst, const char *max_class, wchar_t *out, int cap) {
    int xclass = (max_class && max_class[0] == 'X');

    if (kp >= 8.0f || dst <= -300.0f)
        lstrcpynW(out, L"ALTO  tempesta severa / grid", cap);
    else if (kp >= 6.0f || dst <= -150.0f || xclass)
        lstrcpynW(out, L"ELEVATO  CME / flare impatto", cap);
    else if (kp >= 4.0f || dst <= -80.0f)
        lstrcpynW(out, L"MODERATO  monitor Dst/Kp", cap);
    else
        lstrcpynW(out, L"BASSO  condizioni nominali", cap);
}

static BOOL http_get(const wchar_t *url, char *buf, size_t cap) {
    size_t n = 0;
    DWORD st = 0, err = 0;

    return ingest_inet_get(url, buf, cap, &n, &st, &err) && n > 0;
}

static void fetch_space(SoleSpace *sp) {
    char body[SOLE_BODY_MAX];
    float v;
    int ok = 0;

    sp->kp = -9999.0f;
    sp->dst = -9999.0f;
    sp->tsi_wm2 = -9999.0f;
    sp->f107 = -9999.0f;
    sp->wind_kms = -9999.0f;
    sp->density_pcc = -9999.0f;
    sp->bt_nt = -9999.0f;
    sp->bz_nt = -9999.0f;
    sp->xray_flux = -9999.0f;
    sp->flare_class[0] = 0;
    sp->xray_max_class[0] = 0;
    if (http_get(SOLE_URL_KP, body, sizeof(body)) &&
        ingest_json_last_float(body, "Kp", &v)) {
        sp->kp = v;
        ok = 1;
    }
    if (http_get(SOLE_URL_DST, body, sizeof(body)) &&
        ingest_json_last_float(body, "dst", &v))
        sp->dst = v;
    if (http_get(SOLE_URL_WIND, body, sizeof(body)) &&
        ingest_json_last_float(body, "proton_speed", &v))
        sp->wind_kms = v;
    if (http_get(SOLE_URL_MAG, body, sizeof(body))) {
        if (ingest_json_last_float(body, "bt", &v)) sp->bt_nt = v;
        if (ingest_json_last_float(body, "bz_gsm", &v)) sp->bz_nt = v;
    }
    if (http_get(SOLE_URL_F107, body, sizeof(body)) &&
        ingest_json_last_float(body, "flux", &v)) {
        sp->f107 = v;
        sp->tsi_wm2 = tsi_from_f107(v);
    }
    if (http_get(SOLE_URL_XRAY, body, sizeof(body))) {
        ingest_json_last_string(body, "current_class", sp->flare_class, sizeof(sp->flare_class));
        ingest_json_last_string(body, "max_class", sp->xray_max_class, sizeof(sp->xray_max_class));
        if (ingest_json_last_float(body, "current_int_xrlong", &v))
            sp->xray_flux = v;
    }
    if (http_get(SOLE_URL_ACE, body, sizeof(body))) {
        float d, s;
        if (ingest_ace_swepam_last(body, &d, &s)) {
            sp->density_pcc = d;
            if (sp->wind_kms <= 0.0f) sp->wind_kms = s;
        }
    }
    sp->updated = epoch_sec();
    sp->ok = ok;
    carrington_label(sp->kp, sp->dst, sp->xray_max_class, sp->carrington, 40);
}

static BOOL fetch_atmo_hub(SoleAtmoHub *hub, double lat, double lon) {
    wchar_t url[512];
    char body[SOLE_BODY_MAX];
    SoleAtmoHub out;

    memset(&out, 0, sizeof(out));
    wsprintfW(url,
        L"https://api.open-meteo.com/v1/forecast?latitude=%.4f&longitude=%.4f"
        L"&current=shortwave_radiation,diffuse_radiation,direct_normal_irradiance,"
        L"temperature_2m,wind_speed_100m,cloud_cover,precipitation"
        L"&wind_speed_unit=ms&timezone=UTC",
        lat, lon);
    if (!http_get(url, body, sizeof(body))) return FALSE;
    if (!ingest_json_float(body, "shortwave_radiation", &out.ghi)) return FALSE;
    ingest_json_float(body, "diffuse_radiation", &out.dhi);
    ingest_json_float(body, "direct_normal_irradiance", &out.dni);
    ingest_json_float(body, "temperature_2m", &out.temp_c);
    ingest_json_float(body, "wind_speed_100m", &out.wind100_ms);
    ingest_json_float(body, "cloud_cover", &out.cloud_pct);
    ingest_json_float(body, "precipitation", &out.precip_mm);
    out.ok = 1;
    *hub = out;
    return TRUE;
}

static void fetch_atmo(SoleAtmoHub *hubs) {
    int i;

    for (i = 0; i < SOLE_HUB_N; i++) {
        Clock *c = time_get(SOLE_HUBS[i].clk);
        double lat = SOLE_HUBS[i].lat;
        double lon = SOLE_HUBS[i].lon;
        SoleAtmoHub tmp;

        if (c && c->ok) {
            lat = c->lat;
            lon = c->lon;
        }
        lstrcpynW(hubs[i].abbr, SOLE_HUBS[i].abbr, 8);
        tmp = hubs[i];
        if (fetch_atmo_hub(&tmp, lat, lon))
            hubs[i] = tmp;
    }
}

static void sole_refresh(void) {
    SoleState snap;
    uint32_t now = epoch_sec();
    int need_space = !g_last_space || (now - g_last_space) >= SOLE_SPACE_SEC;
    int need_atmo = !g_last_atmo || (now - g_last_atmo) >= SOLE_ATMO_SEC;

    EnterCriticalSection(&g_lock);
    snap = g_sole;
    LeaveCriticalSection(&g_lock);

    if (need_space)
        fetch_space(&snap.space);
    if (need_atmo) {
        fetch_atmo(snap.hubs);
        snap.atmo_updated = now;
    }

    if (snap.space.f107 > 0.0f) {
        double toa_pw = snap.space.tsi_wm2 * SOLE_TOA_SCALE / 1.0e15;
        wchar_t tsi_s[16], pw_s[16];
        ui_fmt_wdouble(tsi_s, 16, snap.space.tsi_wm2, 2);
        ui_fmt_wdouble(pw_s, 16, toa_pw, 1);
        wsprintfW(snap.toa_line, L"TOA %s W/m2  |  %s PW sul disco", tsi_s, pw_s);
        cycle_from_f107(snap.space.f107, snap.cycle, 48);
    } else {
        lstrcpyW(snap.toa_line, L"TOA attesa feed NOAA...");
        lstrcpyW(snap.cycle, L"Ciclo 25  (TSI da F10.7 NOAA)");
    }

    if (snap.space.ok && snap.hubs[0].ok)
        lstrcpyW(snap.status, L"NOAA SWPC + Open-Meteo live");
    else if (snap.space.ok)
        lstrcpyW(snap.status, L"spazio OK  |  atmosfera in caricamento");
    else if (snap.hubs[0].ok)
        lstrcpyW(snap.status, L"atmosfera OK  |  spazio in caricamento");
    else
        lstrcpyW(snap.status, L"connessione feed solare...");

    EnterCriticalSection(&g_lock);
    g_sole = snap;
    if (need_space) g_last_space = now;
    if (need_atmo) g_last_atmo = now;
    LeaveCriticalSection(&g_lock);

    if (g_page == PAGE_ASTRO)
        InvalidateRect(g_hwnd, NULL, FALSE);
}

static unsigned __stdcall sole_worker(void *arg) {
    (void)arg;
    Sleep(800);
    while (InterlockedCompareExchange(&g_run, 1, 1) == 1) {
        sole_refresh();
        Sleep(30000);
    }
    return 0;
}

void sole_init(void) {
    memset(&g_sole, 0, sizeof(g_sole));
    InitializeCriticalSection(&g_lock);
    InterlockedExchange(&g_run, 1);
    g_thread = (HANDLE)_beginthreadex(NULL, 0, sole_worker, NULL, 0, NULL);
}

void sole_shutdown(void) {
    InterlockedExchange(&g_run, 0);
    if (g_thread) {
        WaitForSingleObject(g_thread, 5000);
        CloseHandle(g_thread);
        g_thread = NULL;
    }
    DeleteCriticalSection(&g_lock);
}

void sole_tick(void) {
    (void)0;
}

const SoleState *sole_state(void) {
    return &g_sole;
}

void sole_copy(SoleState *out) {
    if (!out) return;
    EnterCriticalSection(&g_lock);
    *out = g_sole;
    LeaveCriticalSection(&g_lock);
}

static void sole_kv(HDC dc, int x, int *y, int w, const wchar_t *k, const wchar_t *v, COLORREF vc) {
    RECT kr = { x, *y, x + w * 28 / 100, *y + 14 };
    RECT vr = { kr.right + 4, *y, x + w, *y + 14 };
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    SetTextColor(dc, CLR_DIM);
    TextOutW(dc, kr.left, kr.top, k, lstrlenW(k));
    SetTextColor(dc, vc);
    TextOutW(dc, vr.left, vr.top, v, lstrlenW(v));
    *y += 14;
}

static void sole_kv_f(HDC dc, int x, int *y, int w, const wchar_t *k, float v, int dec, const wchar_t *u,
                      COLORREF vc) {
    wchar_t buf[48];
    wchar_t vs[20];
    if (v <= -9000.0f) {
        sole_kv(dc, x, y, w, k, L"n/d", CLR_OFF);
        return;
    }
    ui_fmt_wdouble(vs, 20, v, dec);
    wsprintfW(buf, L"%s %s", vs, u);
    sole_kv(dc, x, y, w, k, buf, vc);
}

void sole_paint(HDC dc, const RECT *rc) {
    SoleState s;
    RECT body = *rc, left, right, top;
    wchar_t line[160];
    wchar_t age_s[16];
    int y, i, lh = 14;
    int space_age, atmo_age, now = (int)epoch_sec();

    EnterCriticalSection(&g_lock);
    s = g_sole;
    LeaveCriticalSection(&g_lock);

    if (body.bottom <= body.top + 60) return;
    top = body;
    top.bottom = top.top + 14;
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    SetTextColor(dc, CLR_DIM);
  wsprintfW(line, L"%s  |  %s  |  %s", s.status, s.cycle, s.toa_line);
    TextOutW(dc, top.left, top.top, line, lstrlenW(line));
    body.top += 16;

    left = body;
    left.right = body.left + (body.right - body.left) * 50 / 100 - 6;
    right = body;
    right.left = left.right + 12;

    ui_subheading(dc, &(RECT){ left.left, left.top, left.right, left.top + 12 },
                  L"LAYER 1 — SPAZIO  (satellite NOAA, latenza ore)");
    left.top += 14;
    y = left.top;
    space_age = s.space.updated ? now - (int)s.space.updated : -1;
    if (space_age >= 0) {
        wsprintfW(age_s, L"%dm fa", space_age / 60);
        sole_kv(dc, left.left, &y, left.right - left.left, L"aggiornamento", age_s, CLR_OFF);
    }

    sole_kv_f(dc, left.left, &y, left.right - left.left, L"TSI (F10.7 proxy)",
              s.space.tsi_wm2, 2, L"W/m2", CLR_ACC);
    sole_kv_f(dc, left.left, &y, left.right - left.left, L"F10.7 radio",
              s.space.f107, 0, L"sfu", CLR_TXT);
    sole_kv_f(dc, left.left, &y, left.right - left.left, L"Vento solare",
              s.space.wind_kms, 0, L"km/s DSCOVR", CLR_TXT);
    sole_kv_f(dc, left.left, &y, left.right - left.left, L"Densita plasma",
              s.space.density_pcc, 1, L"p/cc ACE", CLR_TXT);
    sole_kv_f(dc, left.left, &y, left.right - left.left, L"Bt IMF",
              s.space.bt_nt, 0, L"nT", CLR_TXT);
    sole_kv_f(dc, left.left, &y, left.right - left.left, L"Bz GSM",
              s.space.bz_nt, 0, L"nT", s.space.bz_nt < -5.0f ? CLR_DN : CLR_TXT);
    sole_kv_f(dc, left.left, &y, left.right - left.left, L"Kp geomag",
              s.space.kp, 1, L"", s.space.kp >= 5.0f ? CLR_DN : CLR_TXT);
    sole_kv_f(dc, left.left, &y, left.right - left.left, L"Dst Kyoto",
              s.space.dst, 0, L"nT", s.space.dst <= -100.0f ? CLR_DN : CLR_TXT);
    sole_kv(dc, left.left, &y, left.right - left.left, L"Rischio grid", s.space.carrington,
            s.space.kp >= 6.0f ? CLR_DN : CLR_TXT);

    y += 4;
    if (s.space.flare_class[0]) {
        wchar_t fx[48];
        wchar_t xf[12];
        MultiByteToWideChar(CP_UTF8, 0, s.space.flare_class, -1, fx, 48);
        MultiByteToWideChar(CP_UTF8, 0, s.space.xray_max_class, -1, xf, 12);
        wsprintfW(line, L"GOES flare %s  max %s", fx, xf);
        sole_kv(dc, left.left, &y, left.right - left.left, L"X-ray flux", line, CLR_ACC);
        sole_kv_f(dc, left.left, &y, left.right - left.left, L"irradianza X",
                  s.space.xray_flux, 6, L"W/m2", CLR_DIM);
    } else {
        sole_kv(dc, left.left, &y, left.right - left.left, L"GOES X-ray", L"attesa feed", CLR_OFF);
    }

    y += 6;
    SetTextColor(dc, CLR_OFF);
    TextOutW(dc, left.left, y,
             L"TSI: proxy TSIS/SORCE via F10.7 NOAA  |  vento: DSCOVR  |  plasma: ACE",
             68);

    ui_subheading(dc, &(RECT){ right.left, right.top, right.right, right.top + 12 },
                  L"LAYER 2 — ATMOSFERA  (Open-Meteo, latenza min)");
    right.top += 14;
    y = right.top;
    atmo_age = s.atmo_updated ? now - (int)s.atmo_updated : -1;
    if (atmo_age >= 0) {
        wsprintfW(age_s, L"%dm fa", atmo_age / 60);
        sole_kv(dc, right.left, &y, right.right - right.left, L"aggiornamento", age_s, CLR_OFF);
    }

    {
        static const int OFF[8] = { 0, 34, 78, 122, 166, 206, 246, 286 };
        static const wchar_t *HDR[8] = {
            L"HUB", L"GHI", L"DNI", L"DHI", L"T C", L"W100", L"CLD%", L"PCP"
        };
        int x0 = right.left, x;

        SelectObject(dc, fSm);
        for (i = 0; i < 8; i++) {
            SetTextColor(dc, CLR_DIM);
            TextOutW(dc, x0 + OFF[i], y, HDR[i], lstrlenW(HDR[i]));
        }
        y += lh + 2;
        ui_hline(dc, x0, y - 2, right.right, CLR_GRID);

        for (i = 0; i < SOLE_HUB_N; i++) {
            wchar_t c0[8], c1[10], c2[10], c3[10], c4[8], c5[8], c6[8], c7[8];
            const SoleAtmoHub *h = &s.hubs[i];
            if (!h->ok) continue;
            ui_fmt_wdouble(c1, 10, h->ghi, 0);
            ui_fmt_wdouble(c2, 10, h->dni, 0);
            ui_fmt_wdouble(c3, 10, h->dhi, 0);
            ui_fmt_wdouble(c4, 8, h->temp_c, 1);
            ui_fmt_wdouble(c5, 8, h->wind100_ms, 1);
            ui_fmt_wdouble(c6, 8, h->cloud_pct, 0);
            ui_fmt_wdouble(c7, 8, h->precip_mm, 1);
            lstrcpynW(c0, h->abbr, 8);
            SetTextColor(dc, CLR_ACC);
            TextOutW(dc, x0 + OFF[0], y, c0, lstrlenW(c0));
            SetTextColor(dc, h->ghi > 200.0f ? CLR_UP : CLR_TXT);
            TextOutW(dc, x0 + OFF[1], y, c1, lstrlenW(c1));
            SetTextColor(dc, CLR_TXT);
            TextOutW(dc, x0 + OFF[2], y, c2, lstrlenW(c2));
            TextOutW(dc, x0 + OFF[3], y, c3, lstrlenW(c3));
            TextOutW(dc, x0 + OFF[4], y, c4, lstrlenW(c4));
            TextOutW(dc, x0 + OFF[5], y, c5, lstrlenW(c5));
            TextOutW(dc, x0 + OFF[6], y, c6, lstrlenW(c6));
            TextOutW(dc, x0 + OFF[7], y, c7, lstrlenW(c7));
            y += lh;
        }
    }

    y += 8;
    SetTextColor(dc, CLR_OFF);
    TextOutW(dc, right.left, y,
             L"GHI/DNI/DHI W/m2 al suolo  |  vento hub 100m  |  FV + eolico + domanda termica",
             72);

    y = left.bottom - 28;
    if (y > left.top + 120) {
        double global_ghi = 0.0;
        int n = 0;
        for (i = 0; i < SOLE_HUB_N; i++)
            if (s.hubs[i].ok) { global_ghi += s.hubs[i].ghi; n++; }
        if (n > 0) {
            wchar_t gs[16];
            ui_fmt_wdouble(gs, 16, global_ghi / n, 0);
            wsprintfW(line, L"Media hub GHI %s W/m2  — immissione suolo (pannelli FV)", gs);
            SetTextColor(dc, CLR_ACC);
            TextOutW(dc, left.left, y, line, lstrlenW(line));
        }
    }
}
