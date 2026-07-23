#!/usr/bin/env python3
"""RSS harvest → cache/intel/headlines.csv (600+ feeds, concurrent, resilient)."""
from __future__ import annotations

import csv
import json
import os
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = Path(os.environ.get("DESK_CACHE", ROOT / "cache")) / "intel"
OUT_CSV = OUT_DIR / "headlines.csv"
OUT_STATS = OUT_DIR / "harvest_stats.json"
CONFIG = HERE / "intel_feeds.json"
OVERRIDES_FILE = HERE / "intel_feed_overrides.json"

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
FETCH_HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept": "application/rss+xml, application/xml, application/atom+xml, text/xml, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def load_overrides() -> dict[str, str]:
    if not OVERRIDES_FILE.is_file():
        return {}
    data = json.loads(OVERRIDES_FILE.read_text(encoding="utf-8"))
    return data.get("overrides", data)


def gnews_site(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("feeds."):
        host = host[6:]
    q = urllib.parse.quote(f"site:{host}")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def sanitize_xml(data: bytes) -> bytes:
    text = data.decode("utf-8", errors="replace")
    text = re.sub(r"&(?!([a-zA-Z][a-zA-Z0-9]*|#[0-9]+|#x[0-9a-fA-F]+);)", "&amp;", text)
    for end_tag in ("</rss>", "</feed>", "</rdf:RDF>"):
        idx = text.find(end_tag)
        if idx != -1:
            text = text[: idx + len(end_tag)]
            break
    return text.encode("utf-8")


def fetch_bytes(url: str, timeout: int) -> bytes:
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers=FETCH_HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read()
    except ssl.SSLError:
        # some African / APAC hosts have broken chains — still concrete publishers
        ctx2 = ssl.create_default_context()
        ctx2.check_hostname = False
        ctx2.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=timeout, context=ctx2) as resp:
            return resp.read()
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e) or "SSL" in str(e):
            ctx2 = ssl.create_default_context()
            ctx2.check_hostname = False
            ctx2.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=timeout, context=ctx2) as resp:
                return resp.read()
        raise


def strip_html(s: str) -> str:
    return re.sub(r"<[^>]+>", "", s or "").strip()


def parse_rss(data: bytes) -> list[dict]:
    for attempt in (data, sanitize_xml(data)):
        try:
            root = ET.fromstring(attempt)
        except ET.ParseError:
            continue
        items: list[dict] = []
        for item in root.findall(".//item"):
            title = item.findtext("title") or ""
            link = item.findtext("link") or ""
            pub = item.findtext("pubDate") or item.findtext("date") or ""
            items.append({"title": strip_html(title), "link": link.strip(), "pub": pub.strip()})
        if items:
            return items
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for entry in root.findall(".//a:entry", ns):
            title = entry.findtext("a:title", namespaces=ns) or ""
            link_el = entry.find("a:link", ns)
            link = link_el.get("href", "") if link_el is not None else ""
            pub = entry.findtext("a:updated", namespaces=ns) or entry.findtext("a:published", namespaces=ns) or ""
            items.append({"title": strip_html(title), "link": link.strip(), "pub": pub.strip()})
        if items:
            return items
    raise ET.ParseError("no parseable RSS/Atom items")


def pub_to_iso(pub: str) -> str:
    if not pub:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    try:
        return parsedate_to_datetime(pub).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except Exception:
        return pub[:32]


def urls_for_feed(feed: dict, overrides: dict[str, str]) -> list[str]:
    """Primary URL plus optional concrete override (World Monitor parity: keep GN)."""
    primary = feed.get("url", "")
    fid = feed.get("id", "")
    seen: set[str] = set()
    out: list[str] = []
    for u in [primary, overrides.get(fid, "")]:
        if not u:
            continue
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def harvest_one(feed: dict, max_per: int, timeout: int, overrides: dict[str, str]) -> tuple[list[dict], str | None]:
    fid = feed.get("id", "?")
    name = feed.get("name", fid)
    last_err = "no url"
    for url in urls_for_feed(feed, overrides):
        try:
            data = fetch_bytes(url, timeout)
            items = parse_rss(data)[:max_per]
            rows = []
            for it in items:
                if not it.get("title"):
                    continue
                rows.append({
                    "ts": pub_to_iso(it.get("pub", "")),
                    "source": fid,
                    "source_name": name,
                    "title": it["title"][:300],
                    "url": (it.get("link") or "")[:500],
                })
            if rows:
                return rows, None
            last_err = "empty feed"
        except Exception as e:
            last_err = str(e)
    return [], last_err


def main() -> int:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    feeds = cfg.get("feeds", [])
    overrides = load_overrides()
    max_per = int(cfg.get("max_per_feed", 5))
    max_total = int(cfg.get("max_total", 8000))
    concurrency = int(cfg.get("concurrency", 20))
    timeout = int(cfg.get("timeout_sec", 25))

    if not feeds:
        print("FAIL no feeds in config — run import_wm_feeds.py first")
        return 1

    print(f"Harvest {len(feeds)} feeds (concurrency={concurrency}, overrides={len(overrides)})")
    rows: list[dict] = []
    ok_n = 0
    fail_n = 0
    errors: list[dict] = []

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        futs = {
            pool.submit(harvest_one, f, max_per, timeout, overrides): f
            for f in feeds
        }
        for i, fut in enumerate(as_completed(futs), 1):
            feed = futs[fut]
            got, err = fut.result()
            if err:
                fail_n += 1
                errors.append({
                    "id": feed.get("id"),
                    "name": feed.get("name"),
                    "url": feed.get("url"),
                    "error": err[:160],
                })
            else:
                ok_n += 1
                rows.extend(got)
            if i % 50 == 0:
                print(f"  progress {i}/{len(feeds)} ok={ok_n} fail={fail_n} headlines={len(rows)}", flush=True)

    rows.sort(key=lambda r: r["ts"], reverse=True)
    rows = rows[:max_total]

    if not rows:
        print(f"FAIL 0 headlines (feeds={len(feeds)} ok={ok_n} fail={fail_n})")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["ts", "source", "source_name", "title", "url"])
        w.writeheader()
        w.writerows(rows)

    stats = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "feeds_configured": len(feeds),
        "feeds_ok": ok_n,
        "feeds_fail": fail_n,
        "headlines": len(rows),
        "errors": errors,
    }
    OUT_STATS.write_text(json.dumps(stats, indent=2, ensure_ascii=False), encoding="utf-8")

    # rebuild desk index (categories + live API events)
    try:
        import build_intel_index as bi
        bi.main()
    except Exception as e:
        print(f"WARN build_intel_index: {e}", flush=True)

    print(f"OK intel {len(rows)} headlines from {ok_n}/{len(feeds)} feeds -> {OUT_CSV}")
    if fail_n:
        print(f"WARN {fail_n} feeds still failing — see {OUT_STATS}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
