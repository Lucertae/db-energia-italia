#!/usr/bin/env python3
"""Test fix strategies on failed feeds."""
from __future__ import annotations

import json
import re
import ssl
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
failures = json.loads((HERE / "feed_failures.json").read_text(encoding="utf-8"))

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)
HEADERS = {
    "User-Agent": BROWSER_UA,
    "Accept": "application/rss+xml, application/xml, application/atom+xml, text/xml, */*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def site_from_url(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc
    if host.startswith("www."):
        host = host[4:]
    return host


def gnews_site(url: str) -> str:
    site = site_from_url(url)
    q = urllib.parse.quote(f"site:{site}")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


def try_fetch(url: str, insecure: bool = False) -> tuple[int, str]:
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
            data = r.read(8000)
        if b"<rss" in data or b"<feed" in data or b"<item" in data or b"<entry" in data:
            return 200, "xml-ok"
        if data[:1] == b"<":
            ET.fromstring(data)
            return 200, "parse-ok"
        return 200, f"non-xml {data[:40]!r}"
    except Exception as e:
        return 0, str(e)[:80]


# Manual URL fixes researched / known working alternates
URL_FIXES: dict[str, str] = {
    "EIA Press Releases": "https://www.eia.gov/rss/todayinenergy.xml",
    "EIA Reports": "https://www.eia.gov/rss/todayinenergy.xml",
    "IEA News": "https://www.iea.org/news/all/news/rss.xml",
    "White House": "https://www.whitehouse.gov/feed/",
    "Defense One": "https://www.defenseone.com/rss/all/",
    "CSIS": "https://www.csis.org/analysis/feed.xml",
    "CFR": "https://www.cfr.org/rss/feed.xml",
    "Maritime Exec": "https://www.maritime-executive.com/rss",
    "Kyiv Indep.": "https://kyivindependent.com/feed/rss/",
    "Nikkei Asia": "https://asia.nikkei.com/rss/feed/nar",
    "Mining Weekly": "https://www.miningweekly.com/rss",
    "ICRC": "https://www.icrc.org/en/rss.xml",
    "VolcanoDisc": "https://www.volcanodiscovery.com/news/rss.xml",
    "CNN": "http://rss.cnn.com/rss/cnn_topstories.rss",
    "UN News": "https://news.un.org/feed/subscribe/en/news/all/atom.xml",
    "NASA Climate": "https://www.nasa.gov/rss/dyn/climate_change.rss",
    "CISA": "https://www.cisa.gov/cybersecurity-advisories/ics-advisories.xml",
    "ReliefWeb": "https://reliefweb.int/updates/rss.xml?language=267",
    "RW Disasters": "https://reliefweb.int/disasters/rss.xml?language=267",
    "Paul Graham Essays": "http://www.aaronsw.com/2002/feeds/pgessays.rss",
    "Techstars Blog": "https://www.techstars.com/the-line/feed",
    "NFX Essays": "https://www.nfx.com/post/rss.xml",
    "Both Sides of Table": "https://bothsidesofthetable.com/feed/",
    "Contxto (LATAM)": "https://contxto.com/feed/rss/",
    "News24": "https://www.news24.com/rss",
    "Brookings": "https://www.brookings.edu/feed/",
    "State Dept": "https://www.state.gov/rss-feed/press-releases/feed/",
    "Euronews": "https://www.euronews.com/rss?format=mrss",
    "RT": "https://news.google.com/rss/search?q=site:rt.com&hl=en-US&gl=US&ceid=US:en",
    "RT Russia": "https://news.google.com/rss/search?q=site:rt.com+russia&hl=en-US&gl=US&ceid=US:en",
    "Tuoi Tre News": "https://news.google.com/rss/search?q=site:tuoitrenews.vn&hl=en-US&gl=US&ceid=US:en",
    "Vanguard Nigeria": "https://news.google.com/rss/search?q=site:vanguardngr.com&hl=en-US&gl=US&ceid=US:en",
}

results = []
for f in failures:
    name = f["name"]
    orig = f["url"]
    strategies = []

    code, msg = try_fetch(orig)
    if code:
        strategies.append(("original+ua", orig, msg))

    fix = URL_FIXES.get(name)
    if fix and fix != orig:
        code, msg = try_fetch(fix)
        if code:
            strategies.append(("url_fix", fix, msg))

    gn = gnews_site(orig)
    code, msg = try_fetch(gn)
    if code:
        strategies.append(("gnews", gn, msg))

    if not strategies and "SSL" in f["error"]:
        code, msg = try_fetch(orig, insecure=True)
        if code:
            strategies.append(("insecure_ssl", orig, msg))

    results.append({"name": name, "id": f["id"], "orig": orig, "strategies": strategies})

fixed = [r for r in results if r["strategies"]]
still = [r for r in results if not r["strategies"]]
print(f"fixable: {len(fixed)} still broken: {len(still)}")
for r in still:
    print("STILL", r["name"], "|", r["orig"][:80])
for r in fixed:
    best = r["strategies"][0]
    print("FIX", r["name"], "->", best[0], best[1][:90])

out = HERE / "feed_fix_candidates.json"
out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
