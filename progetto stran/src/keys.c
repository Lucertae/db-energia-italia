#include "keys.h"
#include <stdio.h>
#include <string.h>

static const KeyInfo g_keys[] = {
    { "eia",       "EIA_API_KEY",             "cache\\eia.key",       "ENERGY",
      "US EIA energy series",
      "https://www.eia.gov/opendata/register.php", 1 },
    { "entsoe",    "ENTSOE_API_TOKEN",        "cache\\entsoe.key",    "ENERGY",
      "ENTSO-E Transparency (EU grid)",
      "https://transparency.entsoe.eu", 1 },
    { "gie",       "HEDGE_GIE_API_KEY",       "cache\\gie.key",       "ENERGY",
      "GIE AGSI/ALSI gas storage",
      "https://agsi.gie.eu", 1 },
    { "terna",     "TERNA_API_KEY",           "cache\\terna.key",     "ENERGY",
      "Terna IT electricity",
      "https://api.terna.it", 0 },
    { "emaps",     "ELECTRICITYMAPS_API_KEY", "cache\\emaps.key",     "ENERGY",
      "Electricity Maps carbon intensity",
      "https://api.electricitymaps.com", 0 },
    { "ocm",       "OPENCHARGEMAP_API_KEY",   "cache\\ocm.key",       "ENERGY",
      "Open Charge Map EV",
      "https://openchargemap.org/site/develop", 0 },
    { "ais",       "AISSTREAM_API_KEY",       "cache\\ais.key",       "MAP",
      "AISStream vessel map (AIS page)",
      "https://aisstream.io", 0 },
    { "gfw",       "GFW_API_TOKEN",           "cache\\gfw.key",       "MAP",
      "Global Fishing Watch map layer",
      "https://globalfishingwatch.org/our-apis", 0 },
    { "firms",     "NASA_FIRMS_MAP_KEY",      "cache\\firms.key",     "MAP",
      "NASA FIRMS fire hotspots raster",
      "https://firms.modaps.eosdis.nasa.gov/api/map_key", 0 },
    { "opensky",   "OPENSKY_CLIENT_ID",       "cache\\opensky.key",   "MAP",
      "OpenSky auth (opt rate limit) client id:secret",
      "https://opensky-network.org", 0 },
    { "aviationstack", "AVIATIONSTACK_API_KEY", "cache\\aviationstack.key", "MAP",
      "AviationStack flights enrichment",
      "https://aviationstack.com", 0 },
    { "acled",     "ACLED_API_KEY",           "cache\\acled.key",     "MAP",
      "ACLED conflict map events",
      "https://acleddata.com", 0 },
    { "ucdp",      "UCDP_ACCESS_TOKEN",       "cache\\ucdp.key",      "MAP",
      "UCDP GED conflict deaths map",
      "https://ucdp.uu.se/apidocs", 0 },
    { "abuseipdb", "ABUSEIPDB_API_KEY",       "cache\\abuseipdb.key", "MAP",
      "AbuseIPDB cyber geo enrichment",
      "https://www.abuseipdb.com", 0 },
    { "otx",       "OTX_API_KEY",             "cache\\otx.key",       "MAP",
      "AlienVault OTX threat pulses",
      "https://otx.alienvault.com", 0 },
    { "fred",      "FRED_API_KEY",            "cache\\fred.key",      "MACRO",
      "Federal Reserve FRED series",
      "https://fred.stlouisfed.org/docs/api/api_key.html", 0 },
    { "databento", "DATABENTO_API_KEY",       "cache\\databento.key", "MARKET",
      "Databento market ticks",
      "https://databento.com", 0 },
    { "quandl",    "QUANDL_API_KEY",          "cache\\quandl.key",    "MARKET",
      "Nasdaq Data Link (Quandl)",
      "https://data.nasdaq.com", 0 },
    { "cdsapi",    "CDSAPI_KEY",              "cache\\cdsapi.key",    "CLIMATE",
      "Copernicus CDS climate API",
      "https://cds.climate.copernicus.eu", 0 },
    { "finnhub",   "FINNHUB_API_KEY",         "cache\\finnhub.key",   "MARKET",
      "Finnhub market quotes (WM)",
      "https://finnhub.io", 0 },
    { "icao",      "ICAO_API_KEY",            "cache\\icao.key",      "MAP",
      "ICAO NOTAM realtime",
      "https://www.icao.int", 0 },
    { "openaq",    "OPENAQ_API_KEY",          "cache\\openaq.key",    "MAP",
      "OpenAQ air quality",
      "https://openaq.org", 0 },
    { "waqi",      "WAQI_API_KEY",            "cache\\waqi.key",      "MAP",
      "WAQI air quality map",
      "https://aqicn.org/api", 0 },
    { "windy",     "WINDY_API_KEY",           "cache\\windy.key",     "MAP",
      "Windy webcams API",
      "https://api.windy.com", 0 },
};

static int g_n = (int)(sizeof(g_keys) / sizeof(g_keys[0]));

static void trim_inplace(char *s) {
    size_t n;
    char *p = s;

    while (*p == ' ' || *p == '\t') p++;
    if (p != s) memmove(s, p, strlen(p) + 1);
    n = strlen(s);
    while (n > 0 && (s[n - 1] == '\n' || s[n - 1] == '\r' ||
                     s[n - 1] == ' ' || s[n - 1] == '\t'))
        s[--n] = 0;
}

int keys_count(void) {
    return g_n;
}

const KeyInfo *keys_info(int idx) {
    if (idx < 0 || idx >= g_n) return NULL;
    return &g_keys[idx];
}

int keys_find(const char *id) {
    int i;
    if (!id) return -1;
    for (i = 0; i < g_n; i++) {
        if (lstrcmpiA(g_keys[i].id, id) == 0)
            return i;
    }
    return -1;
}

int keys_load(int idx, char *out, int cap) {
    const KeyInfo *k;
    char buf[KEYS_MAX_VALUE];
    FILE *f;
    DWORD n;

    if (!out || cap < 2) return 0;
    out[0] = 0;
    k = keys_info(idx);
    if (!k) return 0;

    n = GetEnvironmentVariableA(k->env, buf, (DWORD)sizeof(buf));
    if (n > 0 && n < sizeof(buf)) {
        trim_inplace(buf);
        if (buf[0]) {
            lstrcpynA(out, buf, cap);
            return (int)strlen(out);
        }
    }

    CreateDirectoryA("cache", NULL);
    f = fopen(k->file, "r");
    if (!f) return 0;
    if (!fgets(buf, (int)sizeof(buf), f)) {
        fclose(f);
        return 0;
    }
    fclose(f);
    trim_inplace(buf);
    if (!buf[0]) return 0;
    lstrcpynA(out, buf, cap);
    return (int)strlen(out);
}

BOOL keys_have_idx(int idx) {
    char buf[KEYS_MAX_VALUE];
    return keys_load(idx, buf, (int)sizeof(buf)) > 0;
}

BOOL keys_have(const char *id) {
    int i = keys_find(id);
    if (i < 0) return FALSE;
    return keys_have_idx(i);
}

BOOL keys_save(int idx, const char *value) {
    const KeyInfo *k;
    char clean[KEYS_MAX_VALUE];
    FILE *f;

    k = keys_info(idx);
    if (!k || !value) return FALSE;
    lstrcpynA(clean, value, (int)sizeof(clean));
    trim_inplace(clean);
    if (!clean[0]) return keys_clear(idx);

    CreateDirectoryA("cache", NULL);
    f = fopen(k->file, "w");
    if (!f) return FALSE;
    fputs(clean, f);
    fclose(f);
    SetEnvironmentVariableA(k->env, clean);
    /* alias used by some ENTSO-E scripts */
    if (lstrcmpiA(k->id, "entsoe") == 0)
        SetEnvironmentVariableA("HEDGE_ENTSOE_TOKEN", clean);
    return TRUE;
}

BOOL keys_clear(int idx) {
    const KeyInfo *k = keys_info(idx);
    if (!k) return FALSE;
    DeleteFileA(k->file);
    SetEnvironmentVariableA(k->env, NULL);
    if (lstrcmpiA(k->id, "entsoe") == 0)
        SetEnvironmentVariableA("HEDGE_ENTSOE_TOKEN", NULL);
    return TRUE;
}

void keys_apply_all(void) {
    int i;
    char buf[KEYS_MAX_VALUE];

    for (i = 0; i < g_n; i++) {
        if (keys_load(i, buf, (int)sizeof(buf)) > 0)
            SetEnvironmentVariableA(g_keys[i].env, buf);
    }
}

void keys_status_line(wchar_t *buf, int cap) {
    int i, pos = 0;

    if (!buf || cap < 8) return;
    buf[0] = 0;
    pos = wsprintfW(buf, L"KEYS");
    for (i = 0; i < g_n; i++) {
        if (pos + 14 >= cap) break;
        pos += wsprintfW(buf + pos, L" %hs:%s",
            g_keys[i].id, keys_have_idx(i) ? L"+" : L"-");
    }
}

void keys_summary(wchar_t *buf, int cap) {
    int i, set_n = 0, miss = 0, req_miss = 0;

    if (!buf || cap < 8) return;
    for (i = 0; i < g_n; i++) {
        if (keys_have_idx(i)) set_n++;
        else {
            miss++;
            if (g_keys[i].required) req_miss++;
        }
    }
    wsprintfW(buf, L"API set=%d miss=%d req_miss=%d  totale=%d",
              set_n, miss, req_miss, g_n);
}
