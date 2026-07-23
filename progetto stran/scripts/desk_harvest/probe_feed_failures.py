#!/usr/bin/env python3
"""Probe all feeds and list failures with URLs."""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import harvest_intel as hi  # noqa: E402

cfg = json.loads((HERE / "intel_feeds.json").read_text(encoding="utf-8"))
feeds = cfg["feeds"]
timeout = int(cfg.get("timeout_sec", 25))
overrides = hi.load_overrides()

failures = []
with ThreadPoolExecutor(max_workers=20) as pool:
    futs = {pool.submit(hi.harvest_one, f, 1, timeout, overrides): f for f in feeds}
    for fut in as_completed(futs):
        f = futs[fut]
        rows, err = fut.result()
        if err:
            failures.append({"id": f["id"], "name": f["name"], "url": f["url"], "error": err})

failures.sort(key=lambda x: x["name"])
out = HERE / "feed_failures.json"
out.write_text(json.dumps(failures, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"failures: {len(failures)} / {len(feeds)}")
for x in failures:
    print(f"{x['name'][:40]:40} | {x['error'][:70]}")
    print(f"  {x['url'][:110]}")
