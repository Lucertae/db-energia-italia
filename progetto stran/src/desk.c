#include "desk.h"
#include "time.h"
#include "solar.h"
#include "moon.h"
#include "sessions.h"
#include "pages.h"
#include "chart.h"
#include "data.h"
#include "countries.h"
#include "ships.h"
#include "catalog.h"
#include "weather.h"
#include "lab.h"
#include "intel.h"
#include "ingest_intel.h"
#include "ingest_view.h"
#include "globe_view.h"
#include "data.h"
#include <windowsx.h>

void desk_tick(void) {
    static int poll_frames;
    SYSTEMTIME utc;

    GetSystemTime(&utc);
    time_update(&utc);
    solar_update();
    moon_update(&utc);
    data_tick();
    sessions_update();
    if ((++poll_frames % INTEL_POLL_SEC) == 0) {
        int changed = 0;
        if (intel_desk_poll()) changed = 1;
        if (ingest_view_poll()) changed = 1;
        if (changed && g_hwnd)
            InvalidateRect(g_hwnd, NULL, FALSE);
    }
    if (g_page == PAGE_AIS) {
        static int ship_frames;
        if ((++ship_frames % 3) == 0)
            InvalidateRect(g_hwnd, NULL, FALSE);
    }
    if (g_page == PAGE_ASTRO) {
        static int sole_frames;
        if ((++sole_frames % 30) == 0)
            InvalidateRect(g_hwnd, NULL, FALSE);
    }
    if (g_page == PAGE_MET) {
        static int wx_frames;
        weather_tick();
        if ((++wx_frames % 60) == 0)
            InvalidateRect(g_hwnd, NULL, FALSE);
    }
    if (g_page == PAGE_INGEST) {
        ingest_view_tick();
        InvalidateRect(g_hwnd, NULL, FALSE);
    } else {
        InvalidateRect(g_hwnd, &g_d.hdr, FALSE);
    }
}

void desk_paint(HDC dc, const RECT *clip) {
    RECT hit, bg;

    GetClientRect(g_hwnd, &bg);
    ui_fill(dc, &bg, bBg);
    if (IntersectRect(&hit, clip, &g_d.hdr)) {
        time_paint_header(dc);
        pages_hint(dc);
        moon_paint_icon(dc);
    }
    pages_paint(dc);
    if (IntersectRect(&hit, clip, &g_d.footer)) solar_paint_footer(dc);
    moon_paint_popup(dc);
}

static void desk_set_page(HWND w, int page) {
    RECT body;
    if (page == g_page) return;
    if (!pages_can_switch(page)) return;
    if (g_page == PAGE_GLOBE && page != PAGE_GLOBE)
        globe_view_hide();
    g_page = page;
    if (page == PAGE_MET)
        weather_request_refresh();
    if (page == PAGE_LAB)
        lab_reload();
    if (page == PAGE_NEWS)
        intel_desk_reload();
    if (page == PAGE_NEWS) {
        intel_desk_reload();
        data_kick_intel();
    }
    if (page == PAGE_INGEST)
        ingest_view_reload();
    if (page == PAGE_GLOBE) {
        body.left = PAD;
        body.top = g_d.hdr.bottom + GAP + 26;
        body.right = g_sw - PAD;
        body.bottom = g_d.footer.top - GAP;
        globe_view_show(w, &body);
    }
    InvalidateRect(w, NULL, FALSE);
}

static void desk_fkey(HWND w, int page) {
    if (page >= 0 && page < PAGE_COUNT && pages_can_switch(page))
        desk_set_page(w, page);
}

LRESULT CALLBACK desk_wndproc(HWND w, UINT m, WPARAM wp, LPARAM lp) {
    PAINTSTRUCT ps;
    HDC dc;

    switch (m) {
    case WM_CREATE:
        g_hwnd = w;
        desk_layout(w);
        data_init();
        SetTimer(w, 1, 1000, NULL);
        desk_tick();
        InvalidateRect(w, NULL, FALSE);
        return 0;
    case WM_APP_DATA_READY:
        data_on_ready();
        return 0;
    case WM_TIMER:
        desk_tick();
        return 0;
    case WM_PAINT:
        dc = BeginPaint(w, &ps);
        desk_paint(dc, &ps.rcPaint);
        EndPaint(w, &ps);
        return 0;
    case WM_KEYDOWN:
        if (wp == VK_ESCAPE) {
            if (g_page == PAGE_CAT) {
                catalog_clear_search();
                InvalidateRect(w, NULL, FALSE);
            } else if (g_page == PAGE_INGEST) {
                /* Esc: clear filtro se attivo, altrimenti esci (necessario in data-only) */
                if (ingest_view_key(VK_ESCAPE))
                    InvalidateRect(w, NULL, FALSE);
                else
                    DestroyWindow(w);
            } else
                DestroyWindow(w);
        }
        else if (wp == VK_TAB) {
            if (!g_data_only)
                desk_set_page(w, (g_page + 1) % PAGE_COUNT);
        }
        else if (wp == VK_F1) desk_fkey(w, PAGE_OPS);
        else if (wp == VK_F2) desk_fkey(w, PAGE_MKT);
        else if (wp == VK_F3) desk_fkey(w, PAGE_FX);
        else if (wp == VK_F4) desk_fkey(w, PAGE_NRG);
        else if (wp == VK_F5) {
            if (g_page == PAGE_INGEST) {
                ingest_view_force_rebuild();
                InvalidateRect(w, NULL, FALSE);
            } else
                desk_fkey(w, PAGE_GAS);
        }
        else if (wp == VK_F6) desk_fkey(w, PAGE_MET);
        else if (wp == VK_F7) desk_fkey(w, PAGE_ASTRO);
        else if (wp == VK_F8) desk_fkey(w, PAGE_LAB);
        else if (wp == VK_F9) desk_fkey(w, PAGE_SIG);
        else if (wp == VK_F10) desk_fkey(w, PAGE_RISK);
        else if (wp == VK_F11) desk_fkey(w, PAGE_GEO);
        else if (wp == VK_F12) desk_fkey(w, PAGE_AIS);
        else if (g_page == PAGE_INGEST && ingest_view_key((int)wp)) {
            InvalidateRect(w, NULL, FALSE);
        }
        else {
            int pg = pages_from_vkey((int)wp);
            if (pg >= 0) {
                desk_set_page(w, pg);
            }
            else if (g_page == PAGE_NEWS && intel_desk_key((int)wp)) {
                InvalidateRect(w, NULL, FALSE);
            }
            else if (g_page == PAGE_LAB && lab_key((int)wp)) {
                InvalidateRect(w, NULL, FALSE);
            }
            else if (g_page == PAGE_MET) {
                if (wp == VK_UP || wp == VK_DOWN) {
                    weather_select_hub_delta(wp == VK_DOWN ? 1 : -1);
                    InvalidateRect(w, NULL, FALSE);
                }
            }
            else if (g_page == PAGE_CAT) {
                if (wp == VK_UP || wp == VK_DOWN || wp == VK_PRIOR || wp == VK_NEXT ||
                    wp == VK_HOME || wp == VK_END) {
                    catalog_key_down((int)wp);
                    InvalidateRect(w, NULL, FALSE);
                }
            }
            else if (wp == VK_OEM_3) {
                g_moon_open = !g_moon_open;
                InvalidateRect(w, NULL, FALSE);
            }
            else if (wp == VK_OEM_COMMA) {
                if (g_page == PAGE_GEO) {
                    pages_geo_tab_next(-1);
                    InvalidateRect(w, NULL, FALSE);
                } else if (g_page == PAGE_NRG) {
                    pages_nrg_tab_next(-1);
                    InvalidateRect(w, NULL, FALSE);
                }
            }
            else if (wp == VK_OEM_PERIOD) {
                if (g_page == PAGE_GEO) {
                    pages_geo_tab_next(1);
                    InvalidateRect(w, NULL, FALSE);
                } else if (g_page == PAGE_NRG) {
                    pages_nrg_tab_next(1);
                    InvalidateRect(w, NULL, FALSE);
                }
            }
        }
        return 0;
    case WM_MOUSEWHEEL:
        if (g_page == PAGE_NEWS) {
            int delta = GET_WHEEL_DELTA_WPARAM(wp);
            intel_desk_wheel(delta);
            InvalidateRect(w, NULL, FALSE);
        } else if (g_page == PAGE_INGEST) {
            int delta = GET_WHEEL_DELTA_WPARAM(wp);
            ingest_view_wheel(delta);
            InvalidateRect(w, NULL, FALSE);
        }
        return 0;
    case WM_CHAR:
        if (g_page == PAGE_CAT) {
            catalog_key_char((wchar_t)wp);
            InvalidateRect(w, NULL, FALSE);
        } else if (g_page == PAGE_INGEST) {
            ingest_view_char((wchar_t)wp);
            InvalidateRect(w, NULL, FALSE);
        }
        return 0;
    case WM_LBUTTONDOWN: {
        POINT pt = { GET_X_LPARAM(lp), GET_Y_LPARAM(lp) };
        RECT icon_hit = g_d.moon_icon;
        char hub[4];
        int tab;

        InflateRect(&icon_hit, 6, 6);
        if (PtInRect(&icon_hit, pt)) {
            g_moon_open = !g_moon_open;
            InvalidateRect(w, NULL, FALSE);
        } else if (g_moon_open && !PtInRect(&g_d.moon_pop, pt)) {
            g_moon_open = 0;
            InvalidateRect(w, NULL, FALSE);
        } else if ((tab = pages_tab_hit(pt)) >= 0) {
            desk_set_page(w, tab);
        } else if ((tab = pages_subtab_hit(pt)) >= 0) {
            if (g_page == PAGE_GEO) {
                g_geo_tab = tab;
                InvalidateRect(w, NULL, FALSE);
            } else if (g_page == PAGE_NRG) {
                g_nrg_tab = tab;
                InvalidateRect(w, NULL, FALSE);
            }
        } else if (g_page == PAGE_MET) {
            int li = weather_layer_hit(pt);
            int wi = weather_map_hit(pt);
            int hi = weather_list_hit(pt);
            if (li >= 0) {
                weather_set_layer(li);
                InvalidateRect(w, NULL, FALSE);
            } else if (hi >= 0) {
                weather_set_selected(hi);
                InvalidateRect(w, NULL, FALSE);
            } else if (wi >= 0) {
                weather_set_selected(wi);
                InvalidateRect(w, NULL, FALSE);
            }
        } else if (g_page == PAGE_CAT) {
            int pi = catalog_prov_hit(pt);
            int li;
            if (pi >= 0) {
                catalog_set_prov(pi);
                InvalidateRect(w, NULL, FALSE);
            } else if ((li = catalog_list_hit(pt)) >= 0) {
                catalog_select_idx(li);
                InvalidateRect(w, NULL, FALSE);
            }
        } else if (g_page == PAGE_GEO) {
            int ci = countries_list_hit(pt);
            if (ci >= 0) {
                countries_set_selected(ci);
                InvalidateRect(w, NULL, FALSE);
            }
        } else if (g_page == PAGE_AIS) {
            int si = ships_map_hit(pt);
            if (si >= 0) {
                ships_set_selected(si);
                InvalidateRect(w, NULL, FALSE);
            }
        } else if (g_page == PAGE_NEWS) {
            RECT body, side, inner;
            int cat;
            body.left = PAD;
            body.top = g_d.hdr.bottom + GAP + 26;
            body.right = g_sw - PAD;
            body.bottom = g_d.footer.top - GAP;
            side.left = body.left + 4;
            side.top = body.top + 26;
            side.right = body.left + (body.right - body.left) * 12 / 100 - 4;
            side.bottom = body.bottom - 4;
            inner = ui_panel_body(&side);
            if ((cat = intel_desk_cat_hit(pt, &inner)) >= 0) {
                intel_desk_set_category(cat);
                InvalidateRect(w, NULL, FALSE);
            }
        } else if (g_page == PAGE_INGEST) {
            if (ingest_view_hit(pt))
                InvalidateRect(w, NULL, FALSE);
        } else if (g_page == PAGE_FX && chart_fx_network_hit(pt, hub)) {
            lstrcpyA(g_fx_hub, hub);
            InvalidateRect(w, NULL, FALSE);
        }
        return 0;
    }
    case WM_SIZE:
        desk_layout(w);
        InvalidateRect(w, NULL, FALSE);
        return 0;
    case WM_DESTROY:
        KillTimer(w, 1);
        data_shutdown();
        ui_free();
        PostQuitMessage(0);
        return 0;
    }
    return DefWindowProcW(w, m, wp, lp);
}
