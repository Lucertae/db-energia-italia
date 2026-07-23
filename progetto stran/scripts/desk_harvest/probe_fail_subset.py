#!/usr/bin/env python3
"""Re-probe previously failing feeds (+ optional ID list) and refresh feed_failures.json."""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import harvest_intel as hi  # noqa: E402

cfg = json.loads((HERE / "intel_feeds.json").read_text(encoding="utf-8"))
feeds_by_id = {f["id"]: f for f in cfg.get("feeds", [])}
old = []
if (HERE / "feed_failures.json").is_file():
    old = json.loads((HERE / "feed_failures.json").read_text(encoding="utf-8"))

# Also probe newly added STRAN network feeds
new_ids = [
    f["id"]
    for f in cfg.get("feeds", [])
    if str(f.get("category", "")).startswith("stran-")
]
target_ids = {x["id"] for x in old if x.get("id")} | set(new_ids)
targets = [feeds_by_id[i] for i in sorted(target_ids) if i in feeds_by_id]

overrides = hi.load_overrides()
timeout = int(cfg.get("timeout_sec", 25))
print(f"Probing {len(targets)} feeds (old fails + stran-*)...")

still = []
ok_n = 0
with ThreadPoolExecutor(max_workers=16) as pool:
    futs = {pool.submit(hi.harvest_one, f, 2, timeout, overrides): f for f in targets}
    for fut in as_completed(futs):
        f = futs[fut]
        rows, err = fut.result()
        if err:
            still.append({"id": f["id"], "name": f["name"], "url": f["url"], "error": err[:160]})
            print(f"FAIL {f['name'][:28]:28} | {err[:70]}")
        else:
            ok_n += 1
            print(f"OK   {f['name'][:28]:28} | {len(rows)} items")

# Keep unrelated previous non-target failures out — full failures list =
# all feeds not in targets that were ok before are still ok; only update probed set.
# Final list: still-failing among probed + (none from unprobed)
# For manifest accuracy: run full probe when ok, else only mark probed.
# Safer: probe ALL feeds would be slow; instead write still as new feed_failures
# AND clear any id that recovered.

recovered = target_ids - {x["id"] for x in still}
# Other failures from old list that we didn't probe this time? We probed all old.
out = sorted(still, key=lambda x: x["name"])
(HERE / "feed_failures.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
)
print(f"\nok={ok_n} still_fail={len(out)} recovered={len(recovered)}")
print(f"Wrote {HERE / 'feed_failures.json'}")
