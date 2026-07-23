#ifndef COMPANIES_H
#define COMPANIES_H

#include "common.h"
#include <stdint.h>

#define CO_TIER_MAJOR    0  /* super-major IOC */
#define CO_TIER_NATIONAL 1  /* NOC */
#define CO_TIER_SEMI     2  /* E&P / oilfield services mid-large */
#define CO_TIER_UTILITY  3  /* utility / IPP */
#define CO_TIER_DISTRIB  4  /* gas/power distributor */

#define CO_MAX 56

typedef struct {
    char     sym[16];
    wchar_t  name[36];
    wchar_t  country[16];
    wchar_t  segment[20];
    uint8_t  tier;
    float    price;
    float    chg_pct;
    uint32_t ymd;
    int      have;
} CompanyQuote;

void companies_init(void);
int  companies_count(void);
const CompanyQuote *companies_get(int i);
void companies_refresh(void);
void companies_paint(HDC dc, const RECT *rc, int filter_tier);
void companies_paint_tiles(HDC dc, const RECT *rc);

#endif
