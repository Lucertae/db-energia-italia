#ifndef MAP_CANVAS_H
#define MAP_CANVAS_H

#include "common.h"

typedef struct {
    HBITMAP bmp;
    HDC     dc;
    BYTE   *bits;
    int     w;
    int     h;
    int     stride;
} MapCanvas;

int  map_canvas_resize(MapCanvas *c, HDC ref, int w, int h);
void map_canvas_destroy(MapCanvas *c);
void map_canvas_clear(MapCanvas *c, COLORREF color);
void map_canvas_blit(HDC dst, const MapCanvas *c, int x, int y);
void map_canvas_plot(MapCanvas *c, int x, int y, COLORREF color);

#endif
