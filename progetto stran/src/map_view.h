#ifndef MAP_VIEW_H
#define MAP_VIEW_H

#include "common.h"

void map_view_init(void);
void map_view_paint(HDC dc, const RECT *rc);
void map_view_scroll(int lines);
int  map_view_key(int vk);
int  map_view_wheel(int delta);
int  map_view_hit(POINT pt);
/* If user Enter on a layer that needs a key, returns key id index via out; else -1 */
int  map_view_selected_key_idx(void);

#endif
