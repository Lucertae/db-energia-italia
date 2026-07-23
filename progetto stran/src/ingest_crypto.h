#ifndef INGEST_CRYPTO_H
#define INGEST_CRYPTO_H

#include "common.h"

typedef struct {
    float usd;
    float chg_pct;
    float high_24h;
    float low_24h;
    float vol_usd;
    int   ok;
} CryptoVenueTick;

/* Binance 24h ticker per symbol es. BTCUSDT */
BOOL ingest_binance_ticker(const char *symbol, CryptoVenueTick *out);

/* Kraken public ticker pair es. XXBTZUSD */
BOOL ingest_kraken_ticker(const char *kraken_pair, CryptoVenueTick *out);

/*
 * Storico daily Binance klines -> body CSV compatibile ingest_fred_hist.
 * symbol: BTCUSDT, limit max 1000
 */
int ingest_binance_klines(const char *symbol, int limit, char *buf, size_t cap);

/* Funding rate perp (frazione, es. 0.0001 = 0.01% / 8h) */
BOOL ingest_binance_funding(const char *symbol, float *out_pct);

#endif
