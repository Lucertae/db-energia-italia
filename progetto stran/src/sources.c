#include "sources.h"
#include "series.h"
#include <string.h>

const SourceDef g_sources[] = {
    { "BRT", "DCOILBRENTEU",    NULL, L"BRENT",    SER_ENERGY, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "WTI", "DCOILWTICO",      NULL, L"WTI",      SER_ENERGY, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "HUB", "DHHNGSP",         NULL, L"HH GAS",   SER_ENERGY, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "TTF", "PNGASEUUSDM",     NULL, L"EU GAS",   SER_ENERGY, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "COA", "PCOALAUUSDM",     NULL, L"COAL AU",  SER_ENERGY, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "BRF", "DEXBZUS",         NULL, L"USD/BRL",  SER_FX, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "ZAF", "DEXSFUS",         NULL, L"USD/ZAR",  SER_FX, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "INF", "DEXINUS",         NULL, L"USD/INR",  SER_FX, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "CNF", "DEXCHUS",         NULL, L"USD/CNY",  SER_FX, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "MXF", "DEXMXUS",         NULL, L"USD/MXN",  SER_FX, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "KEF", "DEXKOUS",         NULL, L"USD/KRW",  SER_FX, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "EUF", "DEXUSEU",         NULL, L"USD/EUR",  SER_FX, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "NZF", "DEXUSNZ",         NULL, L"USD/NZD",  SER_FX, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "JPF", "DEXJPUS",         NULL, L"JPY/USD",  SER_FX, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "GBF", "DEXUSUK",         NULL, L"USD/GBP",  SER_FX, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "U10", "DGS10",           NULL, L"US 10Y",   SER_RATE, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "E10", "IRLTLT01EZM156N", NULL, L"EA 10Y",   SER_RATE, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "Z10", "IRLTLT01ZAM156N", NULL, L"ZA 10Y",   SER_RATE, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "SOF", "SOFR",            NULL, L"SOFR",     SER_RATE, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "EDF", "ECBDFR",          NULL, L"ECB DFR",  SER_RATE, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "JKM", "PNGASJPUSDM",     NULL, L"JKM LNG",  SER_ENERGY, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "CPR", "PCOPPUSDM",       NULL, L"COPPER",   SER_MACRO, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "BE5", "T5YIE",           NULL, L"BE 5Y",    SER_MACRO, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "VIX", "VIXCLS",          NULL, L"VIX",      SER_MACRO, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "CAD", "DEXCAUS",         NULL, L"USD/CAD",  SER_FX, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "CRU", NULL,              NULL, L"US CRUDE", SER_ENERGY, SRC_EIA,  0 },
    { "NGS", NULL,              NULL, L"US GAS ST",SER_ENERGY, SRC_EIA,  0 },
    { "DXY", "DTWEXBGS",        NULL, L"DXY",      SER_FX,     SRC_FRED, SRC_FLAG_FRED_CURL },
    { "NOK", "DEXNOUS",         NULL, L"USD/NOK",  SER_FX,     SRC_FRED, SRC_FLAG_FRED_CURL },
    { "SEK", "DEXSDUS",         NULL, L"USD/SEK",  SER_FX,     SRC_FRED, SRC_FLAG_FRED_CURL },
    { "U2",  "DGS2",            NULL, L"US 2Y",    SER_RATE,   SRC_FRED, SRC_FLAG_FRED_CURL },
    { "U5",  "DGS5",            NULL, L"US 5Y",    SER_RATE,   SRC_FRED, SRC_FLAG_FRED_CURL },
    { "BE1", "T10YIE",          NULL, L"BE 10Y",   SER_MACRO,  SRC_FRED, SRC_FLAG_FRED_CURL },
    { "SPX", "SP500",           NULL, L"S&P500",   SER_MACRO,  SRC_FRED, SRC_FLAG_FRED_CURL },
    { "XAU", NULL,              NULL, L"GOLD",     SER_MACRO,  SRC_EIA,  0 },
    { "HYO", "BAMLH0A0HYM2",    NULL, L"HY OAS",   SER_MACRO,  SRC_FRED, SRC_FLAG_FRED_CURL },
    { "IGO", "BAMLC0A0CM",      NULL, L"IG OAS",   SER_MACRO,  SRC_FRED, SRC_FLAG_FRED_CURL },
    { "NAS", "NASDAQCOM",       NULL, L"NASDAQ",   SER_MACRO,  SRC_FRED, SRC_FLAG_FRED_CURL },
    { "FED", "DFF",             NULL, L"FED FUND", SER_RATE,   SRC_FRED, SRC_FLAG_FRED_CURL },
    { "U30", "DGS30",           NULL, L"US 30Y",   SER_RATE,   SRC_FRED, SRC_FLAG_FRED_CURL },
    { "HOL", "DHOILNYH",        NULL, L"HEAT OIL", SER_ENERGY, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "RBO", "GASREGW",         NULL, L"GASOLINE", SER_ENERGY, SRC_FRED, SRC_FLAG_FRED_CURL },
    { "HAS", NULL,              NULL, L"HASHRATE", SER_MACRO,  SRC_EIA,  0 },
    { "CBE", NULL,              NULL, L"CBECI GWh",SER_ENERGY, SRC_EIA,  0 },
    { "EMI", NULL,              NULL, L"BTC CO2",  SER_ENERGY, SRC_EIA,  0 },
    { "CVI", NULL,              NULL, L"CRYPTO VOL",SER_MACRO, SRC_EIA,  0 },
    { "FEE", NULL,              NULL, L"BTC FEES", SER_CRYPTO, SRC_EIA,  0 },
    { "DIF", NULL,              NULL, L"DIFFICULTY",SER_CRYPTO, SRC_EIA,  0 },
    { "REV", NULL,              NULL, L"MINER REV",SER_CRYPTO, SRC_EIA,  0 },
    { "BVL", NULL,              NULL, L"BTC VOL",  SER_CRYPTO, SRC_EIA,  0 },
    { "MCP", NULL,              NULL, L"BTC MCAP", SER_CRYPTO, SRC_EIA,  0 },
    { "GPR", NULL,              NULL, L"GEOP RISK", SER_MACRO,  SRC_EIA,  0 },
    { "CPU", NULL,              NULL, L"CLIM POL", SER_MACRO,  SRC_EIA,  0 },
    { "EUA", NULL,              NULL, L"CARBON EU",SER_ENERGY, SRC_EIA,  0 },
    { "GRN", NULL,              NULL, L"CLEAN ETF",SER_ENERGY, SRC_EIA,  0 },
    { "DIR", NULL,              NULL, L"DIRTY ETF",SER_ENERGY, SRC_EIA,  0 },
    { "NGF", NULL,              NULL, L"NG FUT",   SER_ENERGY, SRC_EIA,  0 },
};

const int g_sources_n = (int)(sizeof(g_sources) / sizeof(g_sources[0]));

const SourceDef *source_by_id(const char *id) {
    int i;

    if (!id) return NULL;
    for (i = 0; i < g_sources_n; i++) {
        if (g_sources[i].id[0] == id[0] && g_sources[i].id[1] == id[1] &&
            g_sources[i].id[2] == id[2])
            return &g_sources[i];
    }
    return NULL;
}
