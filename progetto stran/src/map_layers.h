#ifndef MAP_LAYERS_H
#define MAP_LAYERS_H

#include <windows.h>

/* Catalogo layer mapper: file cache + API key + se già disegnato nel desk. */
typedef struct {
    const char *id;         /* ais, weather, natural, ... */
    const char *label;      /* UI label */
    const char *kind;       /* BASE / AIS / MET / LIVE / GEO / PLANNED */
    const char *data_file;  /* cache path or "" */
    const char *key_id;     /* keys.c id or "" */
    const char *note;       /* source one-liner */
    int         desk_wired; /* 1 = already painted in C (AIS/MET/sidebar) */
} MapLayerInfo;

#define MAP_LAYER_ST_READY   1  /* on desk + data ok */
#define MAP_LAYER_ST_DATA    2  /* data/key ok, not yet painted */
#define MAP_LAYER_ST_NEEDKEY 3  /* missing API key */
#define MAP_LAYER_ST_NEEDFILE 4 /* missing cache file */
#define MAP_LAYER_ST_FREE    5  /* no key, public API (harvest) */
#define MAP_LAYER_ST_PLAN    6  /* planned / WM parity */

int  map_layers_count(void);
const MapLayerInfo *map_layers_info(int idx);
int  map_layers_status(int idx); /* MAP_LAYER_ST_* */
void map_layers_status_label(int st, wchar_t *out, int cap);
void map_layers_summary(wchar_t *buf, int cap);

#endif
