#!/usr/bin/env python3
"""OPS DESK full harvest orchestrator (ciccio10 / local)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("DESK_ROOT", HERE.parents[1]))
CACHE = Path(os.environ.get("DESK_CACHE", ROOT / "cache"))
LIBERO_DIR = Path(os.environ.get("LIBERO_DIR", ROOT / "scripts" / "libero"))


def run_py(name: str) -> int:
    script = HERE / name
    print(f"\n=== {name} ===", flush=True)
    r = subprocess.run([sys.executable, str(script)], cwd=str(HERE))
    return r.returncode


def run_libero() -> int:
    libero = LIBERO_DIR / "fetch_all.py"
    if not libero.is_file():
        print("SKIP libero: script missing", file=sys.stderr)
        return 2
    env = os.environ.copy()
    env.setdefault("LIBERO_DB", str(LIBERO_DIR / "libero.db"))
    env.setdefault("LIBERO_EXPORT", str(CACHE))
    print("\n=== libero fetch_all ===", flush=True)
    return subprocess.run([sys.executable, str(libero), "all"], env=env, cwd=str(libero.parent)).returncode


def main() -> int:
    CACHE.mkdir(parents=True, exist_ok=True)
    steps = [
        "import_wm_feeds.py",
        "build_feed_overrides.py",
        "harvest_live_streams.py",
        "harvest_intel.py",
        "build_intel_index.py",
        "build_ingest_manifest.py",
        "harvest_fred.py",
        "harvest_ecb.py",
        "harvest_crypto.py",
        "harvest_equities.py",
        "harvest_eia.py",
        "fred_inventories.py",
        "eia_public_inventories.py",
        "harvest_entsoe.py",
        "harvest_portwatch.py",
        "../spine_build.py",
    ]
    results: dict[str, int] = {}
    for step in steps:
        results[step] = run_py(step)
    results["libero"] = run_libero()
    print("\n=== summary ===")
    for k, v in results.items():
        print(f"  {k}: {v}")
    hard_fail = sum(1 for k, v in results.items() if v not in (0, 2))
    return 0 if hard_fail < len(results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
