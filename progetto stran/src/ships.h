#ifndef SHIPS_H
#define SHIPS_H

#include "common.h"
#include <stdint.h>

#define SHIP_MAX 32768

typedef struct {
    uint32_t mmsi;
    float lat;
    float lon;
    float sog;
    float cog;
    uint32_t seen;
    int    active;
} ShipVessel;

void ships_init(void);
void ships_shutdown(void);
int  ships_count(void);
int  ships_selected(void);
void ships_set_selected(int i);
int  ships_map_hit(POINT pt);
const ShipVessel *ships_get(int i);
const wchar_t *ships_status_line(void);
int  ships_count_in_bbox(float lat_min, float lat_max, float lon_min, float lon_max);
void ships_paint(HDC dc, const RECT *rc);

#endif
