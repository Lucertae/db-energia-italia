#ifndef KEYS_H
#define KEYS_H

#include <windows.h>

#define KEYS_MAX_VALUE  512
#define KEYS_MAX_N      32

typedef struct {
    const char *id;       /* short id: eia, ais, ... */
    const char *env;      /* environment variable name */
    const char *file;     /* relative path cache\<id>.key */
    const char *sector;   /* ENERGY / MARITIME / ... */
    const char *label;    /* human label */
    const char *portal;   /* signup / docs URL */
    int         required; /* 1 = needed for core desk streams */
} KeyInfo;

int  keys_count(void);
const KeyInfo *keys_info(int idx);
int  keys_find(const char *id);           /* -1 if missing */

BOOL keys_have(const char *id);
BOOL keys_have_idx(int idx);
int  keys_load(int idx, char *out, int cap); /* bytes loaded, 0 if empty */
BOOL keys_save(int idx, const char *value);  /* write file + SetEnvironmentVariable */
BOOL keys_clear(int idx);                    /* delete file + clear env */

/* Load every cache\*.key into process env (call at startup + after save). */
void keys_apply_all(void);

void keys_status_line(wchar_t *buf, int cap);
void keys_summary(wchar_t *buf, int cap); /* "set=N miss=M req_miss=K" */

#endif
