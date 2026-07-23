#ifndef INGEST_INTEL_H
#define INGEST_INTEL_H

#include <stdint.h>

#define INTEL_REFRESH_SEC       300
#define INTEL_POLL_SEC          15
#define PORTWATCH_REFRESH_SEC   21600

int ingest_intel_refresh(uint32_t max_age_portwatch, uint32_t max_age_headlines);

#endif
