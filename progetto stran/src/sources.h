#ifndef SOURCES_H
#define SOURCES_H

#include <stdint.h>

#define SRC_FLAG_FRED_CURL  0x01
#define SRC_FLAG_DISABLED   0x80

#define SRC_ECB   0
#define SRC_FRED  1
#define SRC_HTTP  2
#define SRC_EIA   3

typedef struct {
    const char    *id;
    const char    *fred_id;
    const wchar_t *url;
    const wchar_t *label;
    uint8_t        ser_kind;
    uint8_t        backend;
    uint8_t        flags;
} SourceDef;

extern const SourceDef g_sources[];
extern const int       g_sources_n;

const SourceDef *source_by_id(const char *id);

#endif
