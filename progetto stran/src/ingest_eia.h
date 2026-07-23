#ifndef INGEST_EIA_H
#define INGEST_EIA_H

#include "common.h"
#include <stdint.h>

/* Legge API key da cache\\eia.key (prima riga) o variabile EIA_API_KEY */
BOOL ingest_eia_have_key(void);

/*
 * Consumo totale energia primaria per paese (Mtoe o quad Btu).
 * country_iso2: "US","DE","CN","JP","IN","BR","GB","FR","IT","RU","SA","AU","MX","KR","ZA","NO","NL","PL","ES","CA"
 * out_mtoe: ultimo valore annuale disponibile
 */
BOOL ingest_eia_country_primary(const char *country_iso2, float *out_mtoe, uint16_t *out_year);

#endif
