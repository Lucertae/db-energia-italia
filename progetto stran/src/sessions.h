#ifndef SESSIONS_H
#define SESSIONS_H

#include "common.h"

extern BYTE sess_asia, sess_eu, sess_us;

void sessions_update(void);
void sessions_paint(HDC dc);

#endif
