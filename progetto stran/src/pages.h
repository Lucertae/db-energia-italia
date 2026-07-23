#ifndef PAGES_H
#define PAGES_H

#include "common.h"

/* F1..F12 + N=NEWS + D=CAT  (14 pagine) */
#define PAGE_OPS      0
#define PAGE_MKT      1
#define PAGE_FX       2
#define PAGE_NRG      3
#define PAGE_GAS      4
#define PAGE_MET      5
#define PAGE_ASTRO    6
#define PAGE_LAB      7
#define PAGE_SIG      8
#define PAGE_RISK     9
#define PAGE_GEO     10
#define PAGE_AIS     11
#define PAGE_NEWS    12
#define PAGE_CAT     13
#define PAGE_INGEST  14
#define PAGE_GLOBE   15
#define PAGE_COUNT   16

#define GEO_TAB_COUNT  7
#define NRG_TAB_COUNT  4

extern int g_page;
extern int g_geo_tab;
extern int g_nrg_tab;
extern int g_data_only; /* 1 = solo UI DATI (ING + GLOBE) */

void pages_set_data_only(int on);
int  pages_can_switch(int page);
void pages_paint(HDC dc);
void pages_hint(HDC dc);
int  pages_tab_hit(POINT pt);
int  pages_subtab_hit(POINT pt);
int  pages_from_vkey(int vk);
void pages_geo_tab_next(int dir);
void pages_nrg_tab_next(int dir);
const wchar_t *pages_name(int page);
const wchar_t *pages_hotkey(int page);

#endif
