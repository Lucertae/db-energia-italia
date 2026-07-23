#ifndef ARENA_H
#define ARENA_H

#include <stddef.h>

#define ARENA_CAP (512 * 1024)

void  arena_reset(void);
void *arena_alloc(size_t n);
void *arena_alloc0(size_t n);
size_t arena_used(void);

#endif
