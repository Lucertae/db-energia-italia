#ifndef HISTDB_H
#define HISTDB_H

#include <windows.h>
#include <stddef.h>
#include <stdint.h>

/* on-disk CSV cache: cache\<ID>.csv next to the exe */

void histdb_init(void);
BOOL histdb_save(const char *id, const char *body, size_t len);
/* max_age_sec = 0 accepts any age */
BOOL histdb_load(const char *id, char *buf, size_t cap, size_t *out_len, uint32_t max_age_sec);

#endif
