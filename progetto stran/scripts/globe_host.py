#!/usr/bin/env python3
"""Frameless WebView2 host positioned over the OPS DESK content area."""
from __future__ import annotations

import argparse
import sys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://127.0.0.1:5174/")
    ap.add_argument("--x", type=int, default=80)
    ap.add_argument("--y", type=int, default=80)
    ap.add_argument("--w", type=int, default=1280)
    ap.add_argument("--h", type=int, default=800)
    ap.add_argument("--title", default="OPS DESK · GLOBE")
    args = ap.parse_args()

    try:
        import webview
    except ImportError:
        print("pip install pywebview", file=sys.stderr)
        return 1

    webview.create_window(
        args.title,
        args.url,
        width=max(640, args.w),
        height=max(480, args.h),
        x=args.x,
        y=args.y,
        frameless=False,
        easy_drag=False,
        confirm_close=False,
        background_color="#000000",
    )
    # Edge Chromium / WebView2 on Windows
    webview.start(gui="edgechromium")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
