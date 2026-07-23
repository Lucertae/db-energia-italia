#ifndef GLOSSARY_H
#define GLOSSARY_H

#include "common.h"
#include "pages.h"
void gloss_paint_panel(HDC dc, const RECT *rc, int page_id);
void gloss_paint_footer(HDC dc, const RECT *rc, int page_id);

#endif
