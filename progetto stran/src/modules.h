#ifndef MODULES_H
#define MODULES_H

#include "common.h"

typedef struct {
    char   id[24];
    char   msg[96];
    int    ok;
} ModuleRow;

typedef struct {
    char   pair[12];
    float  profit_bps;
    int    actionable;
} FxCycleRow;

typedef struct {
    char   pair[12];
    float  mom_63d;
    float  carry_spread;
} FxCarryRow;

typedef struct {
    char   id[16];
    char   msg[96];
    int    alert;
    char   sector[12];
} WeatherSigRow;

typedef struct {
    char   desk[8];
    float  delta_norm;
    float  om_mw;
    float  pub_mw;
    int    alert;
} WindDeltaRow;

typedef struct {
    char   zone[8];
    float  hdd_anom;
    float  cdd_anom;
} HddZoneRow;

typedef struct {
    float  oni;
    char   phase[16];
} EnsoSnap;

void modules_reload(void);
int  modules_count(void);
const ModuleRow *modules_get(int i);
const char *modules_brief(void);
const char *modules_built_at(void);

int  modules_fx_cycle_count(void);
const FxCycleRow *modules_fx_cycle_get(int i);

int  modules_fx_carry_top_count(void);
const FxCarryRow *modules_fx_carry_top_get(int i);

int  modules_weather_sig_count(void);
const WeatherSigRow *modules_weather_sig_get(int i);

int  modules_wind_delta_count(void);
const WindDeltaRow *modules_wind_delta_get(int i);

int  modules_hdd_zone_count(void);
const HddZoneRow *modules_hdd_zone_get(int i);
const EnsoSnap *modules_enso(void);

void modules_paint_fx_panel(HDC dc, RECT *rc);
void modules_paint_fx_ranking(HDC dc, RECT *rc);
void modules_paint_fx_cycles(HDC dc, RECT *rc);
void modules_paint_weather_panel(HDC dc, RECT *rc);
void modules_paint_wind_delta(HDC dc, RECT *rc);
void modules_paint_hdd_enso(HDC dc, RECT *rc);
void modules_paint_spine_grid(HDC dc, RECT *rc);

#endif
