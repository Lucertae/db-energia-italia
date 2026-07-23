#ifndef CRYPTO_H
#define CRYPTO_H

#include "common.h"
#include "series.h"

#define CRY_MAX 14

typedef struct {
    char     id[4];
    wchar_t  name[16];
    char     binance[16];
    char     kraken[16];
    float    usd_binance;
    float    usd_kraken;
    float    chg_24h;
    float    basis_bps;   /* (binance-kraken)/mid * 10000 */
    float    vol_quote;
    float    funding_pct; /* Binance perp funding % per 8h */
    int      have;
    int      have_funding;
} CryptoQuote;

void crypto_init(void);
void crypto_refresh(void);
int  crypto_count(void);
const CryptoQuote *crypto_get(int i);

void crypto_paint_page(HDC dc, const RECT *rc, const SeriesStore *macro);
void crypto_merge_series(SeriesStore *st);

#endif
