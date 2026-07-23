#!/usr/bin/env python3
"""Download ECB eurofxref daily + historical XML into cache/ecb/."""
from __future__ import annotations

import os
import sys
import urllib.request
from pathlib import Path

UA = "ops-desk-harvest/1.0"
HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("DESK_ROOT", HERE.parents[1]))
CACHE = Path(os.environ.get("DESK_CACHE", ROOT / "cache"))
ECB_DIR = CACHE / "ecb"

URLS = {
    "eurofxref-daily.xml": "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-daily.xml",
    "eurofxref-hist.xml": "https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.xml",
}


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as resp:
        return resp.read()


def main() -> int:
    ECB_DIR.mkdir(parents=True, exist_ok=True)
    ok = 0
    for name, url in URLS.items():
        try:
            data = fetch(url)
            if len(data) < 256:
                print(f"FAIL {name}: short response", file=sys.stderr)
                continue
            (ECB_DIR / name).write_bytes(data)
            print(f"OK {name} {len(data)} bytes")
            ok += 1
        except Exception as e:
            print(f"FAIL {name}: {e}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
