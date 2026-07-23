#include "arena.h"
#include <string.h>

static unsigned char g_arena[ARENA_CAP];
static size_t g_off;

void arena_reset(void) {
    g_off = 0;
}

void *arena_alloc(size_t n) {
    size_t a;

    if (n == 0) return NULL;
    a = (n + 7u) & ~7u;
    if (g_off + a > ARENA_CAP) return NULL;
    g_off += a;
    return g_arena + (g_off - a);
}

void *arena_alloc0(size_t n) {
    void *p = arena_alloc(n);
    if (p) memset(p, 0, n);
    return p;
}

size_t arena_used(void) {
    return g_off;
}
