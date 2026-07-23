#include "common.h"
#include "desk.h"
#include "pages.h"
#include "time.h"

static void apply_cmdline(PWSTR cmd) {
    if (!cmd || !cmd[0]) return;
    if (wcsstr(cmd, L"--data") || wcsstr(cmd, L"/data") ||
        wcsstr(cmd, L"--dati") || wcsstr(cmd, L"/dati"))
        pages_set_data_only(1);
}

int WINAPI wWinMain(HINSTANCE hi, HINSTANCE hp, PWSTR cmd, int show) {
    MSG msg;
    HWND w;
    int sw, sh;

    (void)hp;
    (void)show;

    if (!time_init()) return 1;

    desk_chdir_exe();
    apply_cmdline(cmd);
    sw = GetSystemMetrics(SM_CXSCREEN);
    sh = GetSystemMetrics(SM_CYSCREEN);
    ui_init();

    WNDCLASSW wc = { 0 };
    wc.lpfnWndProc = desk_wndproc;
    wc.hInstance = hi;
    wc.hCursor = LoadCursor(0, IDC_ARROW);
    wc.hbrBackground = bBg;
    wc.lpszClassName = L"WC";
    RegisterClassW(&wc);

    w = CreateWindowExW(WS_EX_APPWINDOW, L"WC",
        g_data_only ? L"OPS DESK · DATI" : L"OPS DESK",
        WS_POPUP | WS_VISIBLE, 0, 0, sw, sh, 0, 0, hi, 0);
    SetForegroundWindow(w);

    while (GetMessageW(&msg, 0, 0, 0)) {
        DispatchMessageW(&msg);
    }
    return 0;
}
