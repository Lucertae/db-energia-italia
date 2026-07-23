#ifndef INGEST_ENTSOE_H
#define INGEST_ENTSOE_H

#include <windows.h>
#include "ingest.h"

BOOL ingest_entsoe_have_key(void);

/* Aggiorna cache\<desk_id>.csv con media day-ahead recente (A44). Ritorna serie aggiornate. */
int ingest_entsoe_refresh(IngestSession *sess);

#endif
