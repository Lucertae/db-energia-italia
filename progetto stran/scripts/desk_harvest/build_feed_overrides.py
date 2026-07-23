#!/usr/bin/env python3
"""Build intel_feed_overrides.json from probe results + manual URL fixes."""
from __future__ import annotations

import json
import urllib.parse
from pathlib import Path

HERE = Path(__file__).resolve().parent


def gnews_site(url: str) -> str:
    host = urllib.parse.urlparse(url).netloc
    if host.startswith("www."):
        host = host[4:]
    if host.startswith("feeds."):
        host = host[6:]
    q = urllib.parse.quote(f"site:{host}")
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


# Explicit URL replacements (verified working)
MANUAL: dict[str, str] = {
    "WM718C2B15": "https://news.google.com/rss/search?q=mark+suster+blog&hl=en-US&gl=US&ceid=US:en",
    "GO85F9D667": gnews_site("https://www.brookings.edu/feed/"),
    "GO5CAF5440": gnews_site("https://www.cfr.org/rss.xml"),
    "WMD750A297": gnews_site("https://www.cisa.gov/cybersecurity-advisories/all.xml"),
    "GOECCBD1E7": "http://rss.cnn.com/rss/cnn_topstories.rss",
    "GO31A1825F": gnews_site("https://www.csis.org/analysis/feed"),
    "GO0958E426": gnews_site("https://www.chathamhouse.org/rss.xml"),
    "WM18C0F634": gnews_site("https://contxto.com/feed/"),
    "GO29F396B1": "https://www.defenseone.com/rss/all/",
    "ST5EB96B28": "https://www.eia.gov/rss/todayinenergy.xml",
    "WMB959771A": "https://www.eia.gov/rss/todayinenergy.xml",
    "GO09157312": gnews_site("https://www.energyvoice.com/feed/"),
    "GO4E487AE9": gnews_site("https://www.euractiv.com/feed/"),
    "WM9CC246AC": gnews_site("https://www.fpri.org/feed/"),
    "GO030EE1DB": gnews_site("https://www.icrc.org/en/rss"),
    "ST40468AEF": gnews_site("https://www.iea.org/news/rss"),
    "GO83D133A2": gnews_site("https://www.iiss.org/rss/"),
    "GO9C142E1C": gnews_site("https://issafrica.org/iss-today/feed"),
    "WM014E7189": gnews_site("https://indianexpress.com/section/india/feed/"),
    "WMBE29F288": gnews_site("https://japantoday.com/feed/atom"),
    "WM48AD312D": gnews_site("https://kr-asia.com/feed"),
    "GO6B6F3285": "https://kyivindependent.com/feed/rss/",
    "GOEF1047D9": gnews_site("https://www.msf.org/rss"),
    "GOA7E58C72": gnews_site("https://maritime-executive.com/feed"),
    "GO0592F182": gnews_site("https://www.miningweekly.com/page/rss"),
    "GO09C8AFDE": "https://news.google.com/rss/search?q=site%3Anasa.gov+climate&hl=en-US&gl=US&ceid=US:en",
    "WM5DCA39A8": gnews_site("https://www.nfx.com/feed"),
    "WMC5563538": gnews_site("https://www.news24.com/"),
    "GO92E79FF3": "https://asia.nikkei.com/rss/feed/nar",
    "STDF977490": gnews_site("https://www.opec.org/opec_web/en/press/press_rss.htm"),
    "WM4BD28B3C": "http://www.aaronsw.com/2002/feeds/pgessays.rss",
    "WM2CB6D54C": gnews_site("https://pitchbook.com/feed"),
    "WM74AFB771": gnews_site("https://www.primicias.ec/feed/"),
    "WM022446E2": "https://news.google.com/rss/search?q=site:rt.com&hl=en-US&gl=US&ceid=US:en",
    "WM6E94AAAB": "https://news.google.com/rss/search?q=site:rt.com+russia&hl=en-US&gl=US&ceid=US:en",
    "GO194AFF85": gnews_site("https://www.spglobal.com/commodityinsights/en/rss-feed/all.rss"),
    "WMD1C2DB8C": gnews_site("https://www.stimson.org/feed/"),
    "WM0B8E32A7": gnews_site("https://www.techstars.com/blog/feed/"),
    "WM6DEF7587": gnews_site("https://tuoitrenews.vn/rss"),
    "GO0AE8ED80": gnews_site("https://www.unhcr.org/us/news/rss.xml"),
    "WM65F63780": gnews_site("https://www.vanguardngr.com/feed/"),
    "GOC12E8AAD": gnews_site("https://www.volcanodiscovery.com/rss/news.xml"),
    "GO7AC1DB21": gnews_site("https://www.whitehouse.gov/feed/"),
    "WM23C27BE1": gnews_site("https://asharqbusiness.com/rss.xml"),
}


def main() -> int:
    overrides = dict(MANUAL)
    out = HERE / "intel_feed_overrides.json"
    meta = {
        "version": 1,
        "description": "Per-feed URL overrides when primary URL fails (403/404/SSL). Applied before Google News fallback.",
        "overrides": overrides,
    }
    out.write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OK {len(overrides)} overrides -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
