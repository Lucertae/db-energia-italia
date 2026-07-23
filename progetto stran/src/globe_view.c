#include "globe_view.h"
#include <stdio.h>

static HANDLE g_bridge_proc;
static HANDLE g_vite_proc;
static HANDLE g_host_proc;
static int g_started;

static BOOL spawn_cmd(const wchar_t *cmdline, HANDLE *out) {
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    wchar_t buf[1200];

    if (!cmdline || !cmdline[0]) return FALSE;
    lstrcpynW(buf, cmdline, 1200);
    memset(&si, 0, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_HIDE;
    memset(&pi, 0, sizeof(pi));
    if (!CreateProcessW(NULL, buf, NULL, NULL, FALSE, CREATE_NO_WINDOW, NULL, NULL, &si, &pi))
        return FALSE;
    CloseHandle(pi.hThread);
    if (out) *out = pi.hProcess;
    else CloseHandle(pi.hProcess);
    return TRUE;
}

static BOOL spawn_cmd_show(const wchar_t *cmdline, HANDLE *out) {
    STARTUPINFOW si;
    PROCESS_INFORMATION pi;
    wchar_t buf[1200];

    lstrcpynW(buf, cmdline, 1200);
    memset(&si, 0, sizeof(si));
    si.cb = sizeof(si);
    si.dwFlags = STARTF_USESHOWWINDOW;
    si.wShowWindow = SW_SHOW;
    memset(&pi, 0, sizeof(pi));
    if (!CreateProcessW(NULL, buf, NULL, NULL, FALSE, 0, NULL, NULL, &si, &pi))
        return FALSE;
    CloseHandle(pi.hThread);
    if (out) *out = pi.hProcess;
    else CloseHandle(pi.hProcess);
    return TRUE;
}

void globe_view_init(void) {
    g_bridge_proc = NULL;
    g_vite_proc = NULL;
    g_host_proc = NULL;
    g_started = 0;
}

int globe_view_running(void) {
    DWORD code;
    if (!g_host_proc) return 0;
    if (!GetExitCodeProcess(g_host_proc, &code)) return 0;
    return code == STILL_ACTIVE;
}

void globe_view_hide(void) {
    /* keep bridge/vite warm; only close host window process */
    if (g_host_proc) {
        TerminateProcess(g_host_proc, 0);
        CloseHandle(g_host_proc);
        g_host_proc = NULL;
    }
}

void globe_view_show(HWND parent, const RECT *content) {
    RECT rc, scr;
    POINT pt;
    wchar_t cmd[900];
    int x, y, w, h;

    if (!content) return;
    rc = *content;
    pt.x = rc.left;
    pt.y = rc.top;
    ClientToScreen(parent, &pt);
    scr.left = pt.x;
    scr.top = pt.y;
    pt.x = rc.right;
    pt.y = rc.bottom;
    ClientToScreen(parent, &pt);
    scr.right = pt.x;
    scr.bottom = pt.y;
    x = scr.left;
    y = scr.top;
    w = scr.right - scr.left;
    h = scr.bottom - scr.top;
    if (w < 640) w = 640;
    if (h < 480) h = 480;

    if (!g_bridge_proc) {
        spawn_cmd(L"cmd.exe /c python scripts\\globe_bridge.py", &g_bridge_proc);
        Sleep(400);
    }
    if (!g_vite_proc) {
        spawn_cmd(
            L"cmd.exe /c \"cd globe && if not exist node_modules npm install && npm run dev -- --host 127.0.0.1 --port 5174\"",
            &g_vite_proc);
        Sleep(2500);
    }

    if (globe_view_running()) {
        /* already open — leave as is */
        return;
    }
    if (g_host_proc) {
        CloseHandle(g_host_proc);
        g_host_proc = NULL;
    }
    wsprintfW(cmd,
              L"cmd.exe /c python scripts\\globe_host.py --url http://127.0.0.1:5174/ --x %d --y %d --w %d --h %d",
              x, y, w, h);
    spawn_cmd_show(cmd, &g_host_proc);
    g_started = 1;
}

void globe_view_paint(HDC dc, const RECT *rc) {
    RECT r = *rc;
    wchar_t line[200];

    SetBkMode(dc, TRANSPARENT);
    SelectObject(dc, fSm);
    SetTextColor(dc, CLR_ACC);
    TextOutW(dc, r.left, r.top, L"GLOBE  ·  WebView2 overlay (Real-Time Earthquake Globe + WM layers)", 72);
    r.top += 22;
    SetTextColor(dc, CLR_DIM);
    if (globe_view_running()) {
        lstrcpyW(line, L"Finestra globo attiva. Layer: Quakes / Fires / Flights / AIS / Conflicts…");
    } else if (g_started) {
        lstrcpyW(line, L"Avvio in corso (bridge + vite + host). Se non compare, lancia scripts\\run_globe.bat");
    } else {
        lstrcpyW(line, L"Aprendo il globo…");
    }
    TextOutW(dc, r.left, r.top, line, lstrlenW(line));
    r.top += 20;
    SetTextColor(dc, CLR_OFF);
    TextOutW(dc, r.left, r.top,
             L"Base: github.com/AaronMurillo01/Real-Time-Earthquake-Globe  ·  dati: USGS + cache/live",
             88);
}
