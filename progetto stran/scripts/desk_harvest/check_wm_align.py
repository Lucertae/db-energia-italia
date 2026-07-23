#!/usr/bin/env python3
"""Quick WM vs desk ingest alignment report."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import import_wm_feeds as iw  # noqa: E402

root = iw.find_wm_root()
print(f"WM_ROOT={root}")

allf: list[dict] = []
for label, rel, pref in iw.WM_REL_FILES:
    raw, src = iw.read_wm_file(root, rel)
    got = iw.parse_wm_text(raw, pref)
    print(f"  {label:12} parsed={len(got):4}  {src}")
    allf.extend(got)

feeds_ts = (root / "src/config/feeds.ts").read_text(encoding="utf-8") if root else ""
print(f"feeds.ts rss() calls: {len(re.findall(r'rss\\(', feeds_ts))}")
print(f"feeds.ts gn() calls:  {len(re.findall(r'\\bgn\\(', feeds_ts))}")

deduped = iw.dedupe(allf)
print(f"parser deduped (no telegram): {len(deduped)}")

our = json.loads((HERE / "intel_feeds.json").read_text(encoding="utf-8"))
print(f"our feed_count: {our.get('feed_count')} gn={our.get('google_news_count')} policy={our.get('policy')}")

our_urls = {f["url"].rstrip("/").lower() for f in our["feeds"]}
wm_urls = {f["url"].rstrip("/").lower() for f in deduped}
print(f"WM urls in ours: {len(wm_urls & our_urls)} / {len(wm_urls)}")
print(f"ours only (tg/extras): {len(our_urls - wm_urls)}")
print(f"WM missing from ours: {len(wm_urls - our_urls)}")

# sample missing
miss = sorted(wm_urls - our_urls)[:15]
for u in miss:
    print(f"  MISSING {u[:100]}")

# group by WM panel category in category field
c = Counter()
for f in our["feeds"]:
    cat = f.get("category", "")
    # wm-politics -> politics, wm-digest-europe -> europe
    parts = cat.split("-")
    if parts[0] == "wm" and len(parts) >= 2:
        if parts[1] == "digest" and len(parts) >= 3:
            c["digest:" + parts[2]] += 1
        elif parts[1] in ("finance", "tech", "telegram", "full", "base", "commodity", "energy", "happy"):
            c[parts[1] + (":" + parts[2] if len(parts) > 2 else "")] += 1
        else:
            c[parts[1]] += 1
    else:
        c[cat or "?"] += 1
print("category buckets (top 20):")
for k, v in c.most_common(20):
    print(f"  {k:28} {v}")

man = json.loads((HERE.parents[1] / "cache/ingest/manifest.json").read_text(encoding="utf-8"))
rss = [e for e in man["entries"] if e["section"] == "RSS"]
print(f"manifest RSS entries: {len(rss)}")
# how many unique origins (problemi: news.google.com collapses)
print(f"unique origin: {len({e.get('origin') for e in rss})}")
print(f"unique publisher: {len({e.get('publisher') for e in rss})}")
print(f"unique layer: {Counter(e.get('layer') for e in rss).most_common(12)}")
print(f"unique sector: {Counter(e.get('sector') for e in rss).most_common(12)}")
