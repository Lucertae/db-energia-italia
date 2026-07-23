#ifndef CATALOG_H
#define CATALOG_H

#include "common.h"
#include "series.h"

void catalog_paint(HDC dc, const RECT *body, const SeriesStore *st);
int  catalog_list_hit(POINT pt);
int  catalog_prov_hit(POINT pt);
void catalog_key_char(wchar_t ch);
void catalog_key_down(int vk);
void catalog_clear_search(void);
void catalog_set_prov(int p);
void catalog_select_idx(int idx);
const char *catalog_selected_id(void);

#endif
