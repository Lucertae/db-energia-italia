#ifndef WEATHER_H
#define WEATHER_H

#include "common.h"
#include <stdint.h>

#define WEATHER_SITE_N  80
#define WEATHER_REG_N     12
#define WX_FC_H           24

#define WX_LAYER_TEMP   0
#define WX_LAYER_PRESS  1
#define WX_LAYER_RH     2
#define WX_LAYER_WIND   3
#define WX_LAYER_CLOUD  4
#define WX_LAYER_PRECIP 5
#define WX_LAYER_COUNT  6

typedef struct {
    wchar_t name[8];
    double  lat;
    double  lon;
    float   temp_c;
    float   pressure_hpa;
    float   rh_pct;
    float   wind_ms;
    float   wind_deg;
    float   cloud_pct;
    float   precip_mm;
    float   dew_c;
    wchar_t air_mass[28];
    float   fc_temp[WX_FC_H];
    float   fc_wind[WX_FC_H];
    float   fc_precip[WX_FC_H];
    int     fc_n;
    uint32_t fc_updated;
    uint8_t region;
    uint8_t is_hub;
    int     ok;
} WeatherSite;

typedef struct {
    WeatherSite sites[WEATHER_SITE_N];
    int         site_n;
    uint32_t    updated;
    int         layer;
    wchar_t     status[120];
} WeatherState;

void weather_init(void);
void weather_shutdown(void);
void weather_tick(void);
void weather_request_refresh(void);
void weather_set_layer(int layer);
int  weather_layer(void);
void weather_set_selected(int i);
int  weather_selected(void);
void weather_select_hub_delta(int delta);
int  weather_map_hit(POINT pt);
int  weather_layer_hit(POINT pt);
int  weather_list_hit(POINT pt);
const WeatherState *weather_state(void);
int  weather_copy_sites(WeatherSite *out, int cap);
void weather_paint(HDC dc, const RECT *rc);

#endif
