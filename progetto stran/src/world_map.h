#ifndef WORLD_MAP_H
#define WORLD_MAP_H

#include "common.h"
#include "map_canvas.h"

#define WORLD_OCEAN_RGB  RGB(10, 18, 28)
#define WORLD_COAST_RGB  RGB(72, 92, 72)

void world_map_init(void);
void world_map_shutdown(void);
void world_map_ensure(HDC ref_dc, const RECT *rc);
void world_map_blit(HDC dc, const RECT *rc);
const MapCanvas *world_map_base(void);

void world_map_project_local(float lat, float lon, int w, int h, int *x, int *y);

#endif
