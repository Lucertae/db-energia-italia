#ifndef PRODUCTION_H
#define PRODUCTION_H

#include "common.h"
#include <stdint.h>

#define FUEL_SOLAR   0
#define FUEL_WIND    1
#define FUEL_HYDRO   2
#define FUEL_NUCLEAR 3
#define FUEL_GAS     4
#define FUEL_COAL    5
#define FUEL_OIL     6
#define FUEL_BIO     7
#define FUEL_OTHER   8
#define FUEL_COUNT   9

#define PROD_COUNTRY_MAX 22

typedef struct {
    wchar_t iso[4];
    wchar_t name[20];
    float   gen[FUEL_COUNT];
    float   demand_twh;
    float   consumption_mtoe;
    uint16_t year;
    int     have_gen;
    int     have_flow;
} ProdCountry;

void production_init(void);
int  production_country_count(void);
const ProdCountry *production_get(int i);
const wchar_t *production_fuel_label(int fuel);
void production_refresh(void);
void production_paint(HDC dc, const RECT *rc);

#endif
