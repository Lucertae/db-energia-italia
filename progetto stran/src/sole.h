#ifndef SOLE_H
#define SOLE_H

#include "common.h"
#include <stdint.h>

#define SOLE_HUB_N 4

typedef struct {
    float kp;
    float dst;
    float tsi_wm2;
    float f107;
    float wind_kms;
    float density_pcc;
    float bt_nt;
    float bz_nt;
    float xray_flux;
    char  flare_class[12];
    char  xray_max_class[12];
    wchar_t carrington[40];
    uint32_t updated;
    int   ok;
} SoleSpace;

typedef struct {
    wchar_t abbr[8];
    float ghi;
    float dni;
    float dhi;
    float temp_c;
    float wind100_ms;
    float cloud_pct;
    float precip_mm;
    int   ok;
} SoleAtmoHub;

typedef struct {
    SoleSpace space;
    SoleAtmoHub hubs[SOLE_HUB_N];
    wchar_t cycle[48];
    wchar_t toa_line[56];
    wchar_t status[120];
    uint32_t atmo_updated;
} SoleState;

void sole_init(void);
void sole_shutdown(void);
void sole_tick(void);
const SoleState *sole_state(void);
void sole_copy(SoleState *out);
void sole_paint(HDC dc, const RECT *rc);

#endif
