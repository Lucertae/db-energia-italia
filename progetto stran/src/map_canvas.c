#include "map_canvas.h"
#include <stdint.h>
#include <string.h>

int map_canvas_resize(MapCanvas *c, HDC ref, int w, int h) {
    BITMAPINFO bmi;
    HBITMAP old;
    void *bits;

    if (!c || w < 1 || h < 1) return 0;
    if (c->bmp && c->w == w && c->h == h) return 1;

    memset(&bmi, 0, sizeof(bmi));
    bmi.bmiHeader.biSize = sizeof(BITMAPINFOHEADER);
    bmi.bmiHeader.biWidth = w;
    bmi.bmiHeader.biHeight = -h;
    bmi.bmiHeader.biPlanes = 1;
    bmi.bmiHeader.biBitCount = 32;
    bmi.bmiHeader.biCompression = BI_RGB;

    if (!c->dc) {
        c->dc = CreateCompatibleDC(ref);
        if (!c->dc) return 0;
    }
    bits = NULL;
    old = (HBITMAP)SelectObject(c->dc, GetStockObject(WHITE_BRUSH));
    if (old && old != GetStockObject(WHITE_BRUSH))
        SelectObject(c->dc, old);

    if (c->bmp) {
        DeleteObject(c->bmp);
        c->bmp = NULL;
        c->bits = NULL;
    }

    c->bmp = CreateDIBSection(ref, &bmi, DIB_RGB_COLORS, &bits, NULL, 0);
    if (!c->bmp || !bits) return 0;

    SelectObject(c->dc, c->bmp);
    c->bits = (BYTE *)bits;
    c->w = w;
    c->h = h;
    c->stride = w * 4;
    return 1;
}

void map_canvas_destroy(MapCanvas *c) {
    if (!c) return;
    if (c->dc) {
        if (c->bmp) SelectObject(c->dc, GetStockObject(WHITE_BRUSH));
        DeleteDC(c->dc);
    }
    if (c->bmp) DeleteObject(c->bmp);
    memset(c, 0, sizeof(*c));
}

void map_canvas_clear(MapCanvas *c, COLORREF color) {
    uint32_t fill;
    int y;

    if (!c || !c->bits) return;
    fill = ((uint32_t)GetRValue(color)) | (((uint32_t)GetGValue(color)) << 8)
         | (((uint32_t)GetBValue(color)) << 16);
    for (y = 0; y < c->h; y++) {
        uint32_t *row = (uint32_t *)(c->bits + y * c->stride);
        int x;
        for (x = 0; x < c->w; x++)
            row[x] = fill;
    }
}

void map_canvas_blit(HDC dst, const MapCanvas *c, int x, int y) {
    if (!dst || !c || !c->dc || !c->bmp) return;
    BitBlt(dst, x, y, c->w, c->h, c->dc, 0, 0, SRCCOPY);
}

void map_canvas_plot(MapCanvas *c, int x, int y, COLORREF color) {
    uint32_t *px;

    if (!c || !c->bits) return;
    if ((unsigned)x >= (unsigned)c->w || (unsigned)y >= (unsigned)c->h) return;
    px = (uint32_t *)(c->bits + y * c->stride + x * 4);
    *px = ((uint32_t)GetRValue(color)) | (((uint32_t)GetGValue(color)) << 8)
        | (((uint32_t)GetBValue(color)) << 16);
}
