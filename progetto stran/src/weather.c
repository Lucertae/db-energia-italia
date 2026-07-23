#include "weather.h"
#include "ingest_sole.h"
#include "ingest_curl.h"
#include "world_map.h"
#include "map_canvas.h"
#include "chart.h"
#include "pages.h"
#include <process.h>
#include <math.h>
#include <stdio.h>
#include <string.h>

#define WX_BODY_MAX    (256 * 1024)
#define WX_FETCH_SEC   600
#define WX_BATCH       12
#define WX_HEAT_STEP   4
#define WX_IDW_PWR     2.0
#define WX_HIT_R2      (14 * 14)

static const struct {
    const wchar_t *name;
    double lat, lon;
    uint8_t region;
} WX_HUB[] = {
    { L"REK", 64.15, -21.95, 0 }, { L"OSL", 59.91,  10.75, 0 },
    { L"LON", 51.51,  -0.13, 2 }, { L"PAR", 48.86,   2.35, 2 },
    { L"BER", 52.52,  13.41, 2 }, { L"MOS", 55.75,  37.62, 2 },
    { L"IST", 41.01,  28.98, 2 }, { L"CAI", 30.04,  31.24, 4 },
    { L"DXB", 25.20,  55.27, 6 }, { L"MUM", 19.08,  72.88, 6 },
    { L"PEK", 39.90, 116.41, 6 }, { L"TYO", 35.68, 139.69, 7 },
    { L"SGP",  1.35, 103.82, 5 }, { L"NAI",  -1.29,  36.82, 5 },
    { L"LAG",  6.52,   3.38, 5 }, { L"NYC",  40.71, -74.01, 3 },
    { L"HOU",  29.76, -95.37, 3 }, { L"CHI",  41.88, -87.63, 3 },
    { L"LAX",  34.05,-118.24, 3 }, { L"YVR",  49.28,-123.12, 3 },
    { L"NAT",  45.0,  -40.0,  1 }, { L"PAC",  20.0,-150.0,  7 },
    { L"RIO", -22.91, -43.17, 9 }, { L"SAO", -23.55, -46.63, 9 },
    { L"SYD", -33.87, 151.21, 8 }, { L"JNB", -26.20,  28.04, 10 },
    { L"SAT", -45.0,    0.0, 11 }, { L"GRL",  72.0,  -40.0,  0 },
    { L"ALG",  36.0,    3.0,  4 }, { L"KAZ",  48.0,   68.0,  6 },
    { L"PER", -12.0,  -77.0,  9 }, { L"AKL", -37.0,  175.0,  8 },
    { L"HEL",  60.0,   25.0,  2 }, { L"THR",  35.7,   51.4,  4 },
    { L"BOG",   4.7,  -74.1,  5 }, { L"ANC",  61.2,-149.9,  0 },
};

static const double WX_GLAT[] = { 65.0, 45.0, 25.0, 5.0, -15.0, -35.0, -55.0 };
static const double WX_GLON[] = { -150.0, -120.0, -90.0, -60.0, -30.0, 0.0, 30.0, 60.0, 90.0, 120.0, 150.0, 175.0 };

static const wchar_t *REG_NAMES[WEATHER_REG_N] = {
    L"Arctic", L"N Atlantic", L"Europe", L"N America", L"Sahara / ME",
    L"Equatorial", L"Monsoon Asia", L"W Pacific", L"Oceania",
    L"S America", L"S Africa", L"S Ocean"
};

static const wchar_t *LAYER_LBL[WX_LAYER_COUNT] = {
    L"TEMP", L"PRES", L"RH", L"WIND", L"CLD", L"PCP"
};

typedef struct {
    double lat, lon;
    wchar_t name[8];
    uint8_t region;
    uint8_t is_hub;
} WxCoord;

static WxCoord       g_coord[WEATHER_SITE_N];
static int           g_coord_n;
static WeatherState  g_wx;
static MapCanvas     g_frame;
static RECT          g_map_rc, g_chips_rc, g_list_rc;
static CRITICAL_SECTION g_lock;
static volatile LONG g_run, g_refreshing, g_need_refresh;
static HANDLE        g_thread;
static uint32_t      g_last_fetch;
static int           g_sel;
static int           g_hub_scroll;

static void wx_fmt_coord_url(wchar_t *url, size_t cap, double lat, double lon,
                             const wchar_t *params) {
    char la[24], lo[24];
    snprintf(la, sizeof(la), "%.4f", lat);
    snprintf(lo, sizeof(lo), "%.4f", lon);
    wsprintfW(url,
        L"https://api.open-meteo.com/v1/forecast?latitude=%hs&longitude=%hs%s",
        la, lo, params);
}

static int hub_count_ok(const WeatherSite *sites, int n) {
    int i, c = 0;
    for (i = 0; i < n; i++)
        if (sites[i].is_hub && sites[i].ok) c++;
    return c;
}

static int hub_rank(const WeatherSite *sites, int n, int site_i) {
    int i, r = 0;
    for (i = 0; i < n && i < site_i; i++)
        if (sites[i].is_hub && sites[i].ok) r++;
    return r;
}

static uint32_t epoch_sec(void) {
    FILETIME ft;
    ULARGE_INTEGER u;
    GetSystemTimeAsFileTime(&ft);
    u.LowPart = ft.dwLowDateTime;
    u.HighPart = ft.dwHighDateTime;
    return (uint32_t)((u.QuadPart - 116444736000000000ULL) / 10000000ULL);
}

static uint8_t region_from_latlon(double lat, double lon) {
    double alat = fabs(lat);
    if (alat >= 62.0) return 0;
    if (lon >= -60.0 && lon <= 15.0 && lat >= 35.0 && lat <= 72.0) return 2;
    if (lon >= -170.0 && lon <= -50.0 && lat >= 15.0) return 3;
    if (alat <= 18.0 && lon >= -25.0 && lon <= 55.0) return 4;
    if (alat <= 12.0) return 5;
    if (lon >= 60.0 && lon <= 140.0 && lat >= 5.0 && lat <= 45.0) return 6;
    if (lon >= 120.0 || lon <= -120.0) return 7;
    if (lat <= -10.0 && lon >= 110.0) return 8;
    if (lat <= -10.0 && lon >= -85.0 && lon <= -30.0) return 9;
    if (lat <= -15.0 && lon >= 10.0 && lon <= 45.0) return 10;
    if (lat <= -40.0) return 11;
    if (lat >= 25.0 && lon >= -70.0 && lon <= -10.0) return 1;
    return 2;
}

static BOOL coord_near_hub(double lat, double lon) {
    int i;
    for (i = 0; i < (int)(sizeof(WX_HUB) / sizeof(WX_HUB[0])); i++) {
        double dlat = lat - WX_HUB[i].lat, dlon = lon - WX_HUB[i].lon;
        if (dlat * dlat + dlon * dlon < 9.0) return TRUE;
    }
    return FALSE;
}

static void wx_build_coords(void) {
    int i, j, n = 0;
    for (i = 0; i < (int)(sizeof(WX_HUB) / sizeof(WX_HUB[0])) && n < WEATHER_SITE_N; i++) {
        g_coord[n].lat = WX_HUB[i].lat;
        g_coord[n].lon = WX_HUB[i].lon;
        g_coord[n].region = WX_HUB[i].region;
        g_coord[n].is_hub = 1;
        lstrcpynW(g_coord[n].name, WX_HUB[i].name, 8);
        n++;
    }
    for (i = 0; i < (int)(sizeof(WX_GLAT) / sizeof(WX_GLAT[0])); i++) {
        for (j = 0; j < (int)(sizeof(WX_GLON) / sizeof(WX_GLON[0])); j++) {
            if (n >= WEATHER_SITE_N) break;
            if (coord_near_hub(WX_GLAT[i], WX_GLON[j])) continue;
            g_coord[n].lat = WX_GLAT[i];
            g_coord[n].lon = WX_GLON[j];
            g_coord[n].region = region_from_latlon(WX_GLAT[i], WX_GLON[j]);
            g_coord[n].is_hub = 0;
            g_coord[n].name[0] = 0;
            n++;
        }
    }
    g_coord_n = n;
}

static void classify_air_mass(double lat, double lon, float t, float rh, float p,
                              wchar_t *out, int cap) {
    float alat = (float)fabs(lat);
    (void)p;
    if (alat >= 60.0f && t < -5.0f) lstrcpynW(out, L"Ac  arctic continental", cap);
    else if (alat >= 60.0f && rh >= 75.0f) lstrcpynW(out, L"Am  arctic maritime", cap);
    else if (alat >= 60.0f) lstrcpynW(out, L"Pc  polar cold", cap);
    else if (alat >= 40.0f && rh >= 70.0f) lstrcpynW(out, L"Pm  polar maritime", cap);
    else if (alat >= 40.0f && t < 8.0f) lstrcpynW(out, L"Pc  polar continental", cap);
    else if (alat < 12.0f && t >= 26.0f && rh >= 70.0f) lstrcpynW(out, L"E   equatorial", cap);
    else if (alat < 23.0f && rh >= 65.0f) lstrcpynW(out, L"Tm  tropical maritime", cap);
    else if (alat < 23.0f) lstrcpynW(out, L"Tc  tropical continental", cap);
    else if (alat >= 20.0f && alat <= 35.0f && rh < 40.0f) lstrcpynW(out, L"ST  subtropical dry", cap);
    else if (lon >= 60.0 && lon <= 140.0 && alat >= 8.0f && alat <= 30.0f && rh >= 72.0f)
        lstrcpynW(out, L"M   monsoon / SW", cap);
    else if (rh >= 60.0f) lstrcpynW(out, L"m   maritime return", cap);
    else lstrcpynW(out, L"c   continental", cap);
}


static COLORREF temp_color(float t) {
    if (t <= -20.0f) return RGB(20, 40, 180);
    if (t >= 40.0f) return RGB(220, 40, 30);
    if (t < 0.0f) { float u = (t + 20.0f) / 20.0f; return RGB((int)(20+60*u),(int)(40+100*u),(int)(180+40*u)); }
    if (t < 15.0f) { float u = t/15.0f; return RGB((int)(80+80*u),(int)(140+40*u),(int)(220-80*u)); }
    if (t < 28.0f) { float u=(t-15.0f)/13.0f; return RGB((int)(160+60*u),(int)(180-20*u),(int)(140-100*u)); }
    { float u=(t-28.0f)/12.0f; if(u>1)u=1; return RGB(220,(int)(160-120*u),(int)(40-10*u)); }
}
static COLORREF press_color(float hpa) {
    float u; if (hpa<=980) return RGB(120,60,180); if (hpa>=1040) return RGB(240,220,60);
    u=(hpa-980)/60; return RGB((int)(120+120*u),(int)(60+160*u),(int)(180-120*u));
}
static COLORREF rh_color(float rh) {
    if (rh<=20) return RGB(160,120,60); if (rh>=95) return RGB(40,100,220);
    { float u=(rh-20)/75; return RGB((int)(160-120*u),(int)(120+40*u),(int)(60+160*u)); }
}
static COLORREF wind_color(float ms) {
    if (ms<=2) return RGB(60,80,100); if (ms>=20) return RGB(240,240,255);
    { float u=(ms-2)/18; return RGB((int)(60+180*u),(int)(80+160*u),(int)(100+155*u)); }
}
static COLORREF cloud_color(float pct) {
    if (pct<=5) return RGB(20,30,50); if (pct>=95) return RGB(200,205,220);
    { float u=pct/100; return RGB((int)(20+180*u),(int)(30+175*u),(int)(50+170*u)); }
}
static COLORREF precip_color(float mm) {
    if (mm<=0.05f) return RGB(30,40,55); if (mm>=8) return RGB(40,120,240);
    { float u=mm/8; return RGB((int)(30+10*u),(int)(40+80*u),(int)(55+185*u)); }
}
static float layer_value(const WeatherSite *s, int layer) {
    if (!s||!s->ok) return 0;
    switch(layer){case WX_LAYER_PRESS:return s->pressure_hpa;case WX_LAYER_RH:return s->rh_pct;
    case WX_LAYER_WIND:return s->wind_ms;case WX_LAYER_CLOUD:return s->cloud_pct;
    case WX_LAYER_PRECIP:return s->precip_mm;default:return s->temp_c;}
}
static COLORREF layer_color_val(float v, int layer) {
    switch(layer){case WX_LAYER_PRESS:return press_color(v);case WX_LAYER_RH:return rh_color(v);
    case WX_LAYER_WIND:return wind_color(v);case WX_LAYER_CLOUD:return cloud_color(v);
    case WX_LAYER_PRECIP:return precip_color(v);default:return temp_color(v);}
}
static void pixel_to_latlon(int x,int y,int w,int h,double *lat,double *lon){
    if(w<2)w=2;if(h<2)h=2;*lon=(double)x/(w-1)*360-180;*lat=90-(double)y/(h-1)*180;}
static double idw_value(double lat,double lon,const WeatherSite *sites,int n,int layer){
    double wsum=0,vsum=0; int i;
    for(i=0;i<n;i++){const WeatherSite *s=&sites[i];double dlat,dlon,d2,w;float v;
    if(!s->ok)continue;dlat=lat-s->lat;dlon=lon-s->lon;d2=dlat*dlat+dlon*dlon;if(d2>625.0)continue;
    w=1.0/pow(d2+0.25,WX_IDW_PWR*0.5);v=layer_value(s,layer);vsum+=w*v;wsum+=w;}
    return wsum<0.05?-9999.0:vsum/wsum;}
static void blend_pixel(MapCanvas *c,int x,int y,COLORREF col,float alpha){
    uint32_t *px,base,nr,ng,nb;if(!c||!c->bits)return;
    if((unsigned)x>=(unsigned)c->w||(unsigned)y>=(unsigned)c->h)return;
    px=(uint32_t*)(c->bits+y*c->stride+x*4);base=*px;
    nr=(uint32_t)((1-alpha)*(base&0xFF)+alpha*GetRValue(col));
    ng=(uint32_t)((1-alpha)*((base>>8)&0xFF)+alpha*GetGValue(col));
    nb=(uint32_t)((1-alpha)*((base>>16)&0xFF)+alpha*GetBValue(col));
    *px=nr|(ng<<8)|(nb<<16);}
static void paint_heatmap(MapCanvas *c,const WeatherSite *sites,int n,int layer){
    int x,y,w=c->w,h=c->h;
    for(y=0;y<h;y+=WX_HEAT_STEP)for(x=0;x<w;x+=WX_HEAT_STEP){
        double lat,lon,v;COLORREF col;int dx,dy;
        pixel_to_latlon(x,y,w,h,&lat,&lon);v=idw_value(lat,lon,sites,n,layer);
        if(v<=-9000.0)continue;
        col=layer_color_val((float)v,layer);
        for(dy=0;dy<WX_HEAT_STEP&&y+dy<h;dy++)for(dx=0;dx<WX_HEAT_STEP&&x+dx<w;dx++)
            blend_pixel(c,x+dx,y+dy,col,0.55f);}}
static BOOL http_get(const wchar_t *url,char *buf,size_t cap){
    size_t n=0;DWORD st=0,err=0;return ingest_curl_get(url,buf,cap,&n,&st,&err)&&n>0;}
static BOOL array_ok(const char *json,const char *key,float *out,int need,int *out_n){
    int n=0;if(!ingest_json_float_array(json,key,out,need,&n)||n!=need)return FALSE;
    if(out_n)*out_n=n;return TRUE;}

static int json_top_objects(const char *json, const char *starts[], int lens[], int max_n) {
    const char *p;
    int n = 0, depth;

    if (!json) return 0;
    p = json;
    while (*p == ' ' || *p == '\n' || *p == '\r') p++;
    if (*p != '[') {
        if (*p == '{' && max_n > 0) {
            const char *start = p;
            depth = 0;
            do {
                if (*p == '{') depth++;
                else if (*p == '}') depth--;
                p++;
            } while (*p && depth > 0);
            starts[0] = start;
            lens[0] = (int)(p - start);
            return 1;
        }
        return 0;
    }
    p++;
    while (*p && n < max_n) {
        while (*p == ' ' || *p == ',' || *p == '\n' || *p == '\r') p++;
        if (*p == ']') break;
        if (*p != '{') break;
        starts[n] = p;
        depth = 0;
        do {
            if (*p == '{') depth++;
            else if (*p == '}') depth--;
            p++;
        } while (*p && depth > 0);
        lens[n] = (int)(p - starts[n]);
        n++;
    }
    return n;
}

static BOOL parse_current_site(const char *obj, int obj_len, WeatherSite *s) {
    char block[4096];
    const char *cur;
    float t = 0.0f, rh = 0.0f, pr = 0.0f, ws = 0.0f, wd = 0.0f;
    float cc = 0.0f, pc = 0.0f, dw = 0.0f;

    if (!obj || obj_len <= 0 || obj_len >= (int)sizeof(block) || !s) return FALSE;
    memcpy(block, obj, (size_t)obj_len);
    block[obj_len] = 0;
    cur = strstr(block, "\"current\"");
    if (!cur) return FALSE;
    if (!ingest_json_float(cur, "temperature_2m", &t)) return FALSE;
    if (!ingest_json_float(cur, "surface_pressure", &pr)) return FALSE;
    ingest_json_float(cur, "relative_humidity_2m", &rh);
    ingest_json_float(cur, "wind_speed_10m", &ws);
    ingest_json_float(cur, "wind_direction_10m", &wd);
    ingest_json_float(cur, "cloud_cover", &cc);
    ingest_json_float(cur, "precipitation", &pc);
    ingest_json_float(cur, "dew_point_2m", &dw);
    s->temp_c = t;
    s->rh_pct = rh;
    s->pressure_hpa = pr;
    s->wind_ms = ws;
    s->wind_deg = wd;
    s->cloud_pct = cc;
    s->precip_mm = pc;
    s->dew_c = dw;
    s->ok = (s->temp_c > -90.0f && s->pressure_hpa > 800.0f);
    if (s->ok)
        classify_air_mass(s->lat, s->lon, s->temp_c, s->rh_pct, s->pressure_hpa,
                          s->air_mass, 28);
    return s->ok;
}


static void site_from_coord(WeatherSite *s, const WxCoord *c) {
    memset(s, 0, sizeof(*s));
    s->lat = c->lat;
    s->lon = c->lon;
    s->region = c->region;
    s->is_hub = c->is_hub;
    lstrcpynW(s->name, c->name, 8);
}

static BOOL fetch_batch(int start, int count) {
    wchar_t url[4096];
    char latbuf[1024], lonbuf[1024], body[WX_BODY_MAX];
    char *latp, *lonp;
    int i, bn, got = 0;

    if (start < 0 || count <= 0 || start + count > g_coord_n) return FALSE;
    if (count > WX_BATCH) count = WX_BATCH;

    latbuf[0] = lonbuf[0] = 0;
    latp = latbuf;
    lonp = lonbuf;
    for (i = 0; i < count; i++) {
        char la[24], lo[24];
        snprintf(la, sizeof(la), "%s%.4f", (i ? "," : ""), g_coord[start + i].lat);
        snprintf(lo, sizeof(lo), "%s%.4f", (i ? "," : ""), g_coord[start + i].lon);
        if ((int)(latp - latbuf) + (int)strlen(la) >= (int)sizeof(latbuf) - 4) break;
        if ((int)(lonp - lonbuf) + (int)strlen(lo) >= (int)sizeof(lonbuf) - 4) break;
        latp += sprintf(latp, "%s", la);
        lonp += sprintf(lonp, "%s", lo);
    }
    bn = i;
    if (bn <= 0) return FALSE;

    wsprintfW(url,
        L"https://api.open-meteo.com/v1/forecast?latitude=%hs&longitude=%hs"
        L"&current=temperature_2m,relative_humidity_2m,surface_pressure,"
        L"wind_speed_10m,wind_direction_10m,cloud_cover,precipitation,dew_point_2m"
        L"&wind_speed_unit=ms&timezone=UTC",
        latbuf, lonbuf);

    if (!http_get(url, body, sizeof(body))) return FALSE;

    {
        const char *ostarts[WX_BATCH];
        int olens[WX_BATCH], on, j;

        on = json_top_objects(body, ostarts, olens, WX_BATCH);
        if (on <= 0) return FALSE;
        if (on < bn) bn = on;

        for (j = 0; j < bn; j++) {
            WeatherSite *s = &g_wx.sites[start + j];
            EnterCriticalSection(&g_lock);
            site_from_coord(s, &g_coord[start + j]);
            if (parse_current_site(ostarts[j], olens[j], s))
                got++;
            LeaveCriticalSection(&g_lock);
        }
    }
    return got > 0;
}

static BOOL fetch_forecast(int idx) {
    wchar_t url[512];
    char body[WX_BODY_MAX];
    WeatherSite *s;
    float th[WX_FC_H], wh[WX_FC_H], ph[WX_FC_H];
    int n;
    double lat, lon;
    uint8_t ok;

    EnterCriticalSection(&g_lock);
    if (idx < 0 || idx >= g_wx.site_n) {
        LeaveCriticalSection(&g_lock);
        return FALSE;
    }
    s = &g_wx.sites[idx];
    ok = (uint8_t)s->ok;
    lat = s->lat;
    lon = s->lon;
    LeaveCriticalSection(&g_lock);
    if (!ok) return FALSE;

    wx_fmt_coord_url(url, 512, lat, lon,
        L"&hourly=temperature_2m,wind_speed_10m,precipitation"
        L"&forecast_hours=24&wind_speed_unit=ms&timezone=UTC");

    if (!http_get(url, body, sizeof(body))) return FALSE;

    memset(th, 0, sizeof(th));
    memset(wh, 0, sizeof(wh));
    memset(ph, 0, sizeof(ph));
    if (!ingest_json_float_array(body, "temperature_2m", th, WX_FC_H, &n) || n < 4)
        return FALSE;
    if (n > WX_FC_H) n = WX_FC_H;
    ingest_json_float_array(body, "wind_speed_10m", wh, n, NULL);
    ingest_json_float_array(body, "precipitation", ph, n, NULL);

    EnterCriticalSection(&g_lock);
    if (idx < 0 || idx >= g_wx.site_n) {
        LeaveCriticalSection(&g_lock);
        return FALSE;
    }
    s = &g_wx.sites[idx];
    if (!s->ok) {
        LeaveCriticalSection(&g_lock);
        return FALSE;
    }
    memcpy(s->fc_temp, th, sizeof(float) * (size_t)n);
    memcpy(s->fc_wind, wh, sizeof(float) * (size_t)n);
    memcpy(s->fc_precip, ph, sizeof(float) * (size_t)n);
    s->fc_n = n;
    s->fc_updated = epoch_sec();
    LeaveCriticalSection(&g_lock);
    return TRUE;
}

static void weather_do_refresh(void) {
    int i, ok_n = 0;
    wchar_t st[120];

    wx_build_coords();
    EnterCriticalSection(&g_lock);
    g_wx.site_n = g_coord_n;
    for (i = 0; i < g_coord_n; i++)
        site_from_coord(&g_wx.sites[i], &g_coord[i]);
    LeaveCriticalSection(&g_lock);

    for (i = 0; i < g_coord_n; i += WX_BATCH) {
        int n = g_coord_n - i;
        if (n > WX_BATCH) n = WX_BATCH;
        if (fetch_batch(i, n)) {
            int j;
            for (j = i; j < i + n && j < g_coord_n; j++)
                if (g_wx.sites[j].ok) ok_n++;
        }
        Sleep(200);
    }

    EnterCriticalSection(&g_lock);
    if (g_sel < 0 || g_sel >= g_wx.site_n) {
        for (i = 0; i < g_wx.site_n; i++) {
            if (g_wx.sites[i].is_hub && g_wx.sites[i].ok) { g_sel = i; break; }
        }
        if (g_sel < 0 && g_wx.site_n > 0) g_sel = 0;
    }
    if (g_sel >= 0 && g_sel < g_wx.site_n)
        fetch_forecast(g_sel);
    g_wx.updated = epoch_sec();
    g_last_fetch = g_wx.updated;
    if (ok_n > 0)
        wsprintfW(st, L"Open-Meteo GFS  |  %d/%d nodi  |  layer %s",
                  ok_n, g_coord_n, LAYER_LBL[g_wx.layer]);
    else
        lstrcpynW(st, L"Open-Meteo: fetch fallito (rete?)", 120);
    lstrcpynW(g_wx.status, st, 120);
    LeaveCriticalSection(&g_lock);
    if (g_hwnd && g_page == PAGE_MET)
        InvalidateRect(g_hwnd, NULL, FALSE);
}

static unsigned __stdcall weather_thread(void *arg) {
    (void)arg;
    while (InterlockedCompareExchange(&g_run, 0, 0)) {
        uint32_t now = epoch_sec();
        int stale = (g_last_fetch == 0 || now - g_last_fetch >= WX_FETCH_SEC);
        if (stale || InterlockedCompareExchange(&g_need_refresh, 0, 0)) {
            if (InterlockedCompareExchange(&g_refreshing, 1, 0) == 0) {
                if (InterlockedCompareExchange(&g_need_refresh, 0, 1))
                    (void)0;
                weather_do_refresh();
                InterlockedExchange(&g_refreshing, 0);
            }
        }
        Sleep(2000);
    }
    return 0;
}

static void paint_spark(HDC dc, const RECT *rc, const float *vals, int n, COLORREF col) {
    POINT pts[WX_FC_H];
    HPEN pen, old;
    int i, w, h, mn, mx;
    float fmn, fmx, span;
    RECT r = *rc;

    if (!vals || n < 2 || r.right <= r.left + 4 || r.bottom <= r.top + 4) return;
    w = r.right - r.left;
    h = r.bottom - r.top;
    fmn = fmx = vals[0];
    for (i = 1; i < n; i++) {
        if (vals[i] < fmn) fmn = vals[i];
        if (vals[i] > fmx) fmx = vals[i];
    }
    span = fmx - fmn;
    if (span < 1e-4f) span = 1.0f;
    for (i = 0; i < n; i++) {
        pts[i].x = r.left + (i * w) / (n - 1);
        mn = r.bottom - (int)((vals[i] - fmn) / span * (h - 1));
        pts[i].y = mn;
    }
    pen = CreatePen(PS_SOLID, 1, col);
    old = (HPEN)SelectObject(dc, pen);
    Polyline(dc, pts, n);
    SelectObject(dc, old);
    DeleteObject(pen);
}

static void paint_wind_arrow(HDC dc, int x, int y, float deg, float ms, COLORREF c) {
    double rad;
    int dx, dy, len;
    HPEN pen, old;

    if (ms < 0.5f) return;
    len = 4 + (int)(ms * 0.8f);
    if (len > 18) len = 18;
    rad = (deg + 180.0) * 3.14159265 / 180.0;
    dx = (int)(sin(rad) * len);
    dy = (int)(-cos(rad) * len);
    pen = CreatePen(PS_SOLID, 1, c);
    old = (HPEN)SelectObject(dc, pen);
    MoveToEx(dc, x, y, NULL);
    LineTo(dc, x + dx, y + dy);
    SelectObject(dc, old);
    DeleteObject(pen);
}

static void paint_region_summary(HDC dc, int x, int y, int w, const WeatherSite *sites, int n) {
    float tsum[WEATHER_REG_N], tct[WEATHER_REG_N];
    float psum[WEATHER_REG_N], pct[WEATHER_REG_N];
    wchar_t line[80];
    int i, r, row = 0;

    memset(tsum, 0, sizeof(tsum));
    memset(tct, 0, sizeof(tct));
    memset(psum, 0, sizeof(psum));
    memset(pct, 0, sizeof(pct));
    for (i = 0; i < n; i++) {
        if (!sites[i].ok) continue;
        r = sites[i].region;
        if (r < 0 || r >= WEATHER_REG_N) continue;
        tsum[r] += sites[i].temp_c;
        psum[r] += sites[i].pressure_hpa;
        tct[r] += 1.0f;
        pct[r] += 1.0f;
    }
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    SetTextColor(dc, CLR_DIM);
    TextOutW(dc, x, y, L"REGIONI  T avg / P avg", 21);
    y += 14;
    for (r = 0; r < WEATHER_REG_N; r++) {
        wchar_t ts[16], ps[16];
        if (tct[r] < 0.5f) continue;
        ui_fmt_wdouble(ts, 16, tsum[r] / tct[r], 1);
        ui_fmt_wdouble(ps, 16, psum[r] / pct[r], 0);
        wsprintfW(line, L"%-11s %5sC %4shPa", REG_NAMES[r], ts, ps);
        SetTextColor(dc, CLR_TXT);
        TextOutW(dc, x, y + row * 12, line, lstrlenW(line));
        row++;
        if (row >= 8) break;
    }
}

void weather_init(void) {
    memset(&g_wx, 0, sizeof(g_wx));
    g_wx.layer = WX_LAYER_TEMP;
    lstrcpynW(g_wx.status, L"meteo: avvio...", 120);
    InitializeCriticalSection(&g_lock);
    wx_build_coords();
    g_wx.site_n = g_coord_n;
    g_sel = -1;
    g_hub_scroll = 0;
    g_last_fetch = 0;
    InterlockedExchange(&g_run, 1);
    InterlockedExchange(&g_refreshing, 0);
    InterlockedExchange(&g_need_refresh, 1);
    g_thread = (HANDLE)_beginthreadex(NULL, 0, weather_thread, NULL, 0, NULL);
}

void weather_shutdown(void) {
    InterlockedExchange(&g_run, 0);
    if (g_thread) {
        WaitForSingleObject(g_thread, 8000);
        CloseHandle(g_thread);
        g_thread = NULL;
    }
    map_canvas_destroy(&g_frame);
    DeleteCriticalSection(&g_lock);
}

void weather_tick(void) {
    static uint32_t last_poll;
    uint32_t now = epoch_sec();
    if (!g_hwnd || g_last_fetch != 0) return;
    if (now - last_poll < 2) return;
    last_poll = now;
    InvalidateRect(g_hwnd, NULL, FALSE);
}

void weather_request_refresh(void) {
    InterlockedExchange(&g_need_refresh, 1);
}

void weather_set_layer(int layer) {
    if (layer < 0 || layer >= WX_LAYER_COUNT) return;
    EnterCriticalSection(&g_lock);
    g_wx.layer = layer;
    LeaveCriticalSection(&g_lock);
}

int weather_layer(void) {
    int l;
    EnterCriticalSection(&g_lock);
    l = g_wx.layer;
    LeaveCriticalSection(&g_lock);
    return l;
}

void weather_select_hub_delta(int delta) {
    int i, n, next = -1;
    EnterCriticalSection(&g_lock);
    n = g_wx.site_n;
    if (delta > 0) {
        for (i = (g_sel < 0 ? 0 : g_sel + 1); i < n; i++) {
            if (g_wx.sites[i].is_hub && g_wx.sites[i].ok) { next = i; break; }
        }
    } else if (delta < 0) {
        for (i = (g_sel < 0 ? n - 1 : g_sel - 1); i >= 0; i--) {
            if (g_wx.sites[i].is_hub && g_wx.sites[i].ok) { next = i; break; }
        }
    }
    LeaveCriticalSection(&g_lock);
    if (next >= 0)
        weather_set_selected(next);
}

void weather_set_selected(int i) {
    int need_fc = 0;
    EnterCriticalSection(&g_lock);
    if (i < 0) i = 0;
    if (i >= g_wx.site_n) i = g_wx.site_n - 1;
    if (g_wx.site_n <= 0) { LeaveCriticalSection(&g_lock); return; }
    g_sel = i;
    if (g_wx.sites[i].ok && g_wx.sites[i].fc_n < 4)
        need_fc = 1;
    LeaveCriticalSection(&g_lock);
    if (need_fc && InterlockedCompareExchange(&g_refreshing, 0, 0) == 0) {
        EnterCriticalSection(&g_lock);
        fetch_forecast(g_sel);
        LeaveCriticalSection(&g_lock);
        if (g_hwnd) InvalidateRect(g_hwnd, NULL, FALSE);
    }
}

int weather_selected(void) {
    int s;
    EnterCriticalSection(&g_lock);
    s = g_sel;
    LeaveCriticalSection(&g_lock);
    return s;
}

int weather_map_hit(POINT pt) {
    int i, best = -1, lx, ly, mw, mh, px, py;
    double best_d = 1e30, d;
    WeatherSite snap[WEATHER_SITE_N];
    int n;

    if (!PtInRect(&g_map_rc, pt)) return -1;
    lx = pt.x - g_map_rc.left;
    ly = pt.y - g_map_rc.top;
    mw = g_map_rc.right - g_map_rc.left;
    mh = g_map_rc.bottom - g_map_rc.top;
    EnterCriticalSection(&g_lock);
    n = g_wx.site_n;
    if (n > WEATHER_SITE_N) n = WEATHER_SITE_N;
    memcpy(snap, g_wx.sites, sizeof(WeatherSite) * (size_t)n);
    LeaveCriticalSection(&g_lock);

    for (i = 0; i < n; i++) {
        if (!snap[i].ok) continue;
        world_map_project_local((float)snap[i].lat, (float)snap[i].lon, mw, mh, &px, &py);
        d = (double)(lx - px) * (lx - px) + (double)(ly - py) * (ly - py);
        if (d < best_d) { best_d = d; best = i; }
    }
    return (best_d <= WX_HIT_R2) ? best : -1;
}

int weather_layer_hit(POINT pt) {
    int i;
    if (!PtInRect(&g_chips_rc, pt)) return -1;
    for (i = 0; i < WX_LAYER_COUNT; i++) {
        RECT chip;
        int cw = (g_chips_rc.right - g_chips_rc.left) / WX_LAYER_COUNT;
        chip.left = g_chips_rc.left + i * cw;
        chip.right = chip.left + cw - 2;
        chip.top = g_chips_rc.top;
        chip.bottom = g_chips_rc.bottom;
        if (PtInRect(&chip, pt)) return i;
    }
    return -1;
}

int weather_list_hit(POINT pt) {
    int i, row_h = 13, y, rank = 0;
    if (!PtInRect(&g_list_rc, pt)) return -1;
    y = g_list_rc.top;
    EnterCriticalSection(&g_lock);
    for (i = 0; i < g_wx.site_n; i++) {
        RECT row;
        if (!g_wx.sites[i].is_hub || !g_wx.sites[i].ok) continue;
        if (rank < g_hub_scroll) { rank++; continue; }
        row.left = g_list_rc.left;
        row.right = g_list_rc.right;
        row.top = y;
        row.bottom = y + row_h;
        if (row.bottom > g_list_rc.bottom) break;
        if (PtInRect(&row, pt)) {
            LeaveCriticalSection(&g_lock);
            return i;
        }
        y += row_h;
        rank++;
    }
    LeaveCriticalSection(&g_lock);
    return -1;
}

const WeatherState *weather_state(void) {
    return &g_wx;
}

int weather_copy_sites(WeatherSite *out, int cap) {
    int n;

    if (!out || cap <= 0) return 0;
    EnterCriticalSection(&g_lock);
    n = g_wx.site_n;
    if (n > cap) n = cap;
    if (n > 0)
        memcpy(out, g_wx.sites, sizeof(WeatherSite) * (size_t)n);
    LeaveCriticalSection(&g_lock);
    return n;
}

void weather_paint(HDC dc, const RECT *rc) {
    RECT r = *rc, map, side, top, chips, list, det, fc;
    wchar_t line[160], vbuf[16];
    int i, n, sel, layer, mw, mh, px, py, hub_y, rank;
    const MapCanvas *base;
    WeatherSite snap[WEATHER_SITE_N];
    uint32_t updated;
    HPEN grid, old_pen;

    if (r.bottom <= r.top + 40) return;
    top = r;
    top.bottom = top.top + 14;
    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    EnterCriticalSection(&g_lock);
    n = g_wx.site_n;
    if (n > WEATHER_SITE_N) n = WEATHER_SITE_N;
    memcpy(snap, g_wx.sites, sizeof(WeatherSite) * (size_t)n);
    sel = g_sel;
    layer = g_wx.layer;
    updated = g_wx.updated;
    lstrcpynW(line, g_wx.status, 160);
    LeaveCriticalSection(&g_lock);

    SetTextColor(dc, CLR_DIM);
    TextOutW(dc, top.left, top.top, line, lstrlenW(line));
    r.top += 16;

    side.left = r.right - (r.right - r.left) * 28 / 100;
    side.right = r.right;
    side.top = r.top;
    side.bottom = r.bottom;
    map = r;
    map.right = side.left - 8;

    chips = map;
    chips.bottom = chips.top + 16;
    map.top = chips.bottom + 2;
    g_chips_rc = chips;
    g_map_rc = map;

    ui_subheading(dc, &chips, L"LAYERS  TEMP PRES RH WIND CLD PCP");
    chips.top += 14;
    g_chips_rc = chips;
    for (i = 0; i < WX_LAYER_COUNT; i++) {
        RECT chip;
        int cw = (chips.right - chips.left) / WX_LAYER_COUNT;
        chip.left = chips.left + i * cw;
        chip.right = chip.left + cw - 2;
        chip.top = chips.top;
        chip.bottom = chips.top + 14;
        ui_fill(dc, &chip, layer == i ? bWhite : bBand);
        SetTextColor(dc, layer == i ? CLR_BG : CLR_DIM);
        TextOutW(dc, chip.left + 4, chip.top + 1, LAYER_LBL[i], lstrlenW(LAYER_LBL[i]));
    }

    mw = map.right - map.left;
    mh = map.bottom - map.top;
    world_map_ensure(dc, &map);
    base = world_map_base();
    if (mw > 4 && mh > 4 && base && base->bits &&
        map_canvas_resize(&g_frame, dc, mw, mh)) {
        size_t src_bytes = (size_t)base->stride * (size_t)base->h;
        size_t dst_bytes = (size_t)g_frame.stride * (size_t)g_frame.h;
        if (src_bytes > dst_bytes) src_bytes = dst_bytes;
        memcpy(g_frame.bits, base->bits, src_bytes);
        paint_heatmap(&g_frame, snap, n, layer);
        map_canvas_blit(dc, &g_frame, map.left, map.top);

        for (i = 0; i < n; i++) {
            COLORREF c;
            int rad;
            HBRUSH br, old_br;
            HPEN pen, old_pn;
            if (!snap[i].ok) continue;
            world_map_project_local((float)snap[i].lat, (float)snap[i].lon, mw, mh, &px, &py);
            c = layer_color_val(layer_value(&snap[i], layer), layer);
            rad = snap[i].is_hub ? 3 : 2;
            if (i == sel) {
                HPEN ring = CreatePen(PS_SOLID, 1, CLR_ACC);
                old_pn = (HPEN)SelectObject(dc, ring);
                SelectObject(dc, GetStockObject(HOLLOW_BRUSH));
                Ellipse(dc, map.left + px - 6, map.top + py - 6,
                        map.left + px + 6, map.top + py + 6);
                SelectObject(dc, old_pn);
                DeleteObject(ring);
            }
            br = CreateSolidBrush(c);
            pen = CreatePen(PS_SOLID, 1, c);
            old_br = (HBRUSH)SelectObject(dc, br);
            old_pn = (HPEN)SelectObject(dc, pen);
            Ellipse(dc, map.left + px - rad, map.top + py - rad,
                    map.left + px + rad, map.top + py + rad);
            SelectObject(dc, old_br);
            SelectObject(dc, old_pn);
            DeleteObject(br);
            DeleteObject(pen);
            if (snap[i].is_hub && snap[i].wind_ms >= 1.0f)
                paint_wind_arrow(dc, map.left + px, map.top + py,
                                 snap[i].wind_deg, snap[i].wind_ms, CLR_TXT);
        }
    }

    grid = CreatePen(PS_SOLID, 1, RGB(28, 36, 44));
    old_pen = (HPEN)SelectObject(dc, grid);
    MoveToEx(dc, map.left, map.top + mh / 2, NULL);
    LineTo(dc, map.right, map.top + mh / 2);
    MoveToEx(dc, map.left + mw / 2, map.top, NULL);
    LineTo(dc, map.left + mw / 2, map.bottom);
    SelectObject(dc, old_pen);
    DeleteObject(grid);

    ui_fill(dc, &side, bBg);

    list = side;
    list.bottom = side.top + (side.bottom - side.top) * 42 / 100;
    det.left = side.left;
    det.right = side.right;
    det.top = list.bottom + 4;
    det.bottom = side.bottom - 88;
    g_list_rc = list;

    ui_subheading(dc, &list, L"HUBS  (click)");
    list.top += 14;
    g_list_rc = list;
    hub_y = list.top;

    {
        int max_rows = (list.bottom - hub_y) / 13;
        int hr;
        if (max_rows < 1) max_rows = 1;
        if (sel >= 0 && sel < n && snap[sel].is_hub) {
            hr = hub_rank(snap, n, sel);
            if (hr < g_hub_scroll) g_hub_scroll = hr;
            if (hr >= g_hub_scroll + max_rows) g_hub_scroll = hr - max_rows + 1;
        }
        rank = 0;
        SelectObject(dc, fSm);
        for (i = 0; i < n; i++) {
            wchar_t rh[16], pr[16];
            const WeatherSite *s = &snap[i];
            if (!s->is_hub || !s->ok) continue;
            if (rank < g_hub_scroll) { rank++; continue; }
            if (hub_y + 13 > list.bottom) break;
            SetTextColor(dc, (i == sel) ? CLR_ACC : CLR_TXT);
            ui_fmt_wdouble(vbuf, 16, s->temp_c, 1);
            ui_fmt_wdouble(rh, 16, s->rh_pct, 0);
            ui_fmt_wdouble(pr, 16, s->pressure_hpa, 0);
            wsprintfW(line, L"%-4s  %5s C  %3s%%  %4s hPa",
                      s->name, vbuf, rh, pr);
            TextOutW(dc, list.left, hub_y, line, lstrlenW(line));
            hub_y += 13;
            rank++;
        }
    }

    ui_subheading(dc, &det, L"DETTAGLIO + 24h FC");
    det.top += 14;
    fc.left = det.left;
    fc.right = det.right;
    fc.top = det.top + 58;
    fc.bottom = fc.top + 72;
    if (sel >= 0 && sel < n && snap[sel].ok) {
        const WeatherSite *s = &snap[sel];
        wchar_t lat[16], lon[16], rh[16], pr[16], ws[16], cl[16], pc[16], dw[16];
        SetTextColor(dc, CLR_ACC);
        ui_fmt_wdouble(lat, 16, s->lat, 2);
        ui_fmt_wdouble(lon, 16, s->lon, 2);
        wsprintfW(line, L"%s  %s  %s", s->name[0] ? s->name : L"GRID", lat, lon);
        TextOutW(dc, det.left, det.top, line, lstrlenW(line));
        det.top += 14;
        SetTextColor(dc, CLR_TXT);
        ui_fmt_wdouble(vbuf, 16, s->temp_c, 1);
        ui_fmt_wdouble(rh, 16, s->rh_pct, 0);
        ui_fmt_wdouble(pr, 16, s->pressure_hpa, 0);
        ui_fmt_wdouble(ws, 16, s->wind_ms, 1);
        wsprintfW(line, L"T %s C   RH %s%%   P %s hPa   W %s m/s",
                  vbuf, rh, pr, ws);
        TextOutW(dc, det.left, det.top, line, lstrlenW(line));
        det.top += 14;
        ui_fmt_wdouble(cl, 16, s->cloud_pct, 0);
        ui_fmt_wdouble(pc, 16, s->precip_mm, 2);
        ui_fmt_wdouble(dw, 16, s->dew_c, 1);
        wsprintfW(line, L"CLD %s%%   PCP %s mm/h   dew %s C", cl, pc, dw);
        TextOutW(dc, det.left, det.top, line, lstrlenW(line));
        det.top += 14;
        SetTextColor(dc, CLR_DIM);
        TextOutW(dc, det.left, det.top, s->air_mass, lstrlenW(s->air_mass));
        if (s->fc_n >= 4) {
            RECT sr = { det.left, fc.top, det.right, fc.top + 24 };
            paint_spark(dc, &sr, s->fc_temp, s->fc_n, CLR_LINE);
            sr.top = sr.bottom + 4;
            sr.bottom = sr.top + 22;
            paint_spark(dc, &sr, s->fc_wind, s->fc_n, CLR_UP);
            sr.top = sr.bottom + 4;
            sr.bottom = sr.top + 22;
            paint_spark(dc, &sr, s->fc_precip, s->fc_n, RGB(80, 140, 220));
        }
    } else {
        SetTextColor(dc, CLR_OFF);
        TextOutW(dc, det.left, det.top, L"Seleziona un hub sulla mappa o lista", 36);
    }

    paint_region_summary(dc, side.left, side.bottom - 82, side.right - side.left, snap, n);
    if (updated)
        wsprintfW(line, L"aggiornato %u s fa", epoch_sec() - updated);
    else
        line[0] = 0;
    SetTextColor(dc, CLR_OFF);
    TextOutW(dc, side.left, side.bottom - 12, line, lstrlenW(line));
}

