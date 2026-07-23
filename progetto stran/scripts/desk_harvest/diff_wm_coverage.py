#!/usr/bin/env python3
"""Compare our concrete ingest coverage vs live World Monitor upstream."""
from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import import_wm_feeds as iw  # noqa: E402

UA = {"User-Agent": "ops-desk-wm-diff/1.0"}


def host(url: str) -> str:
    try:
        h = urlparse(url).netloc.lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def is_gnews(url: str) -> bool:
    u = (url or "").lower()
    return "news.google.com" in u or "/rss/search" in u


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=90) as r:
        return r.read().decode("utf-8", errors="replace")


def load_ours() -> tuple[list[dict], list[dict]]:
    feeds = json.loads((HERE / "intel_feeds.json").read_text(encoding="utf-8"))["feeds"]
    live = json.loads((HERE / "live_streams.json").read_text(encoding="utf-8"))
    streams = live.get("streams") or []
    return feeds, streams


def main() -> int:
    our_feeds, our_live = load_ours()
    our_all_urls = {f["url"].rstrip("/").lower() for f in our_feeds if f.get("url")}
    our_concrete = [f for f in our_feeds if f.get("url") and not is_gnews(f["url"])]
    our_conc_urls = {f["url"].rstrip("/").lower() for f in our_concrete}
    our_conc_hosts = {host(f["url"]) for f in our_concrete}
    our_conc_names = {f["name"].strip().lower() for f in our_concrete if f.get("name")}
    our_live_ids = {s.get("id", "").lower() for s in our_live}
    our_live_hosts = {host(s.get("url", "")) for s in our_live if s.get("url")}

    wm: list[dict] = []
    for label, url, cat_prefix in iw.WM_RSS_FILES:
        try:
            raw = fetch(url)
            got = iw.parse_wm_rss_blocks(raw, cat_prefix)
            wm.extend(got)
            print(f"fetched WM {label}: {len(got)}")
        except Exception as e:
            print(f"WM {label} FAIL: {e}")
    try:
        dig = iw.parse_digest_feeds(fetch(iw.WM_DIGEST))
        wm.extend(dig)
        print(f"fetched WM digest: {len(dig)}")
    except Exception as e:
        print(f"WM digest FAIL: {e}")

    wm = iw.dedupe(wm)
    wm_concrete = [f for f in wm if not is_gnews(f.get("url", ""))]
    wm_gnews = [f for f in wm if is_gnews(f.get("url", ""))]

    # Missing from our concrete set (by URL host+name fuzzy)
    missing_url = []
    missing_host_cov = []
    for f in wm_concrete:
        u = f["url"].rstrip("/").lower()
        h = host(f["url"])
        n = (f.get("name") or "").strip().lower()
        if u in our_conc_urls or u in our_all_urls:
            continue
        if n and n in our_conc_names:
            continue
        if h and h in our_conc_hosts:
            # we have same host under another feed name — soft miss
            missing_host_cov.append(f)
            continue
        missing_url.append(f)

    # Also compare live streams from WM if harvest_live_streams documents them
    live_doc = HERE / "live_streams.json"
    # Try pull WM live stream catalog references from our file notes
    print()
    print("=== SUMMARY ===")
    print(f"World Monitor RSS total (deduped):     {len(wm)}")
    print(f"  of which Google News topic queries:  {len(wm_gnews)}")
    print(f"  of which concrete publisher feeds:   {len(wm_concrete)}")
    print(f"Our intel_feeds.json total:            {len(our_feeds)}")
    print(f"  still Google News in file:           {sum(1 for f in our_feeds if is_gnews(f.get('url','')))}")
    print(f"  concrete publisher feeds:            {len(our_concrete)}")
    print(f"Our live_streams:                      {len(our_live)}")
    print()
    print(f"WM concrete missing by URL+name:       {len(missing_url)}")
    print(f"WM concrete same-host already covered: {len(missing_host_cov)}")

    # Group missing by category
    by_cat: dict[str, list] = {}
    for f in missing_url:
        cat = f.get("category", "?")
        by_cat.setdefault(cat, []).append(f)

    print("\n=== MISSING WM CONCRETE SOURCES (by category) ===")
    for cat in sorted(by_cat):
        rows = by_cat[cat]
        print(f"\n[{cat}] {len(rows)}")
        for f in sorted(rows, key=lambda x: x.get("name", "")):
            print(f"  - {f.get('name','?'):40} {host(f.get('url','')):28} {f.get('url','')[:90]}")

    out = {
        "wm_total": len(wm),
        "wm_gnews": len(wm_gnews),
        "wm_concrete": len(wm_concrete),
        "ours_total": len(our_feeds),
        "ours_concrete": len(our_concrete),
        "ours_live": len(our_live),
        "missing_concrete": [
            {"name": f.get("name"), "url": f.get("url"), "category": f.get("category"), "host": host(f.get("url", ""))}
            for f in missing_url
        ],
        "same_host_covered": [
            {"name": f.get("name"), "url": f.get("url"), "host": host(f.get("url", ""))}
            for f in missing_host_cov
        ],
    }
    dest = Path(__file__).resolve().parents[2] / "cache" / "ingest" / "wm_coverage_gap.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
