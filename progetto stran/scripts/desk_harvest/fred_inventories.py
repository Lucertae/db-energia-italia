#!/usr/bin/env python3
"""US weekly inventories — EIA public pages (no key). FRED mirror IDs are discontinued."""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    from eia_public_inventories import main as eia_main
    return eia_main()


if __name__ == "__main__":
    raise SystemExit(main())
