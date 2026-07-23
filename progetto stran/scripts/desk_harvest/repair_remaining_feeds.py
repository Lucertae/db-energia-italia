#!/usr/bin/env python3
"""Second-pass repair: try alternate concrete RSS URLs for still-failing feeds."""
from __future__ import annotations

import json
import ssl
import sys
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import harvest_intel as hi  # noqa: E402

BROWSER_UA = hi.BROWSER_UA
HEADERS = hi.FETCH_HEADERS

# Multiple concrete alternates per feed id (order = preference)
ALTS: dict[str, list[str]] = {
    "ST40468AEF": [  # IEA
        "https://www.iea.org/rss.xml",
        "https://www.iea.org/news/all/news/rss.xml",
        "https://www.iea.org/feeds/press-releases.xml",
    ],
    "STDF977490": [  # OPEC
        "https://www.opec.org/opec_web/static_files_project/media/download_files/rss/opec_rss.xml",
        "https://www.opec.org/opec_web/en/rss/rss.xml",
    ],
    "GO7AC1DB21": [  # White House
        "https://www.whitehouse.gov/news/feed/",
        "https://www.whitehouse.gov/briefing-room/feed/",
        "https://www.whitehouse.gov/feed",
    ],
    "GO31A1825F": [  # CSIS
        "https://www.csis.org/analysis/feed",
        "https://www.csis.org/feeds/analysis.xml",
        "https://www.csis.org/rss.xml",
    ],
    "GO5CAF5440": [  # CFR
        "https://www.cfr.org/rss.xml",
        "https://www.cfr.org/feeds/blog.xml",
        "https://www.cfr.org/feeds/backgrounders.xml",
    ],
    "GO09C8AFDE": [  # NASA
        "https://www.nasa.gov/rss/dyn/breaking_news.rss",
        "https://www.nasa.gov/news-release/feed/",
        "https://www.nasa.gov/feed/",
    ],
    "GOC12E8AAD": [
        "https://www.volcanodiscovery.com/rss.xml",
        "https://www.volcanodiscovery.com/eruptions/rss.xml",
    ],
    "GO030EE1DB": [
        "https://www.icrc.org/en/rss/news",
        "https://blogs.icrc.org/feed/",
        "https://www.icrc.org/sites/default/files/icrc_rss.xml",
    ],
    "GO2FDE7B9A": [
        "https://www.armscontrol.org/blog/rss.xml",
        "https://www.armscontrol.org/act.xml",
    ],
    "GO39566D0C": [
        "https://www.rand.org/content/rand/blog.rss",
        "https://www.rand.org/pubs.xml",
        "https://www.rand.org/newsroom.rss",
    ],
    "WM54E3CF70": [
        "https://www.rand.org/content/rand/blog.rss",
        "https://www.rand.org/blog.rss",
    ],
    "GOA7E58C72": [
        "https://maritime-executive.com/rss",
        "https://www.maritime-executive.com/magazine.rss",
    ],
    "GO92E79FF3": [
        "https://asia.nikkei.com/rss",
        "https://asia.nikkei.com/rss/feed",
        "https://feeds.feedburner.com/NikkeiAsiaReview",
    ],
    "GO9C142E1C": [
        "https://issafrica.org/feed",
        "https://issafrica.org/about-us/press-releases/feed",
        "https://issafrica.org/iss-today?format=feed&type=rss",
    ],
    "WM55D5EA4C": [
        "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
        "https://news.un.org/en/rss.xml",
        "https://news.un.org/feed/subscribe/en/news/topic/un-affairs/feed/rss.xml",
    ],
    "WMD750A297": [
        "https://www.cisa.gov/news-events/cybersecurity-advisories.xml",
        "https://www.us-cert.gov/ncas/alerts.xml",
    ],
    "GOEF1047D9": [
        "https://www.doctorswithoutborders.org/rss.xml",
        "https://www.msf.org/news/rss",
    ],
    "GO0AE8ED80": [
        "https://www.unhcr.org/news/stories/rss.xml",
        "https://www.unrefugees.org/news/feed/",
    ],
    "GO85F9D667": [
        "https://www.brookings.edu/articles/feed/",
        "https://www.brookings.edu/topic/foreign-policy/feed/",
    ],
    "GO0958E426": [
        "https://www.chathamhouse.org/publications/rss.xml",
        "https://www.chathamhouse.org/expert-comment/feed",
    ],
    "GO83D133A2": [
        "https://www.iiss.org/online-analysis/feed/",
        "https://www.iiss.org/blogs/analysis/rss",
    ],
    "WM9CC246AC": [
        "https://www.fpri.org/article/feed/",
        "https://www.fpri.org/rss",
    ],
    "WMD1C2DB8C": [
        "https://www.stimson.org/feed",
        "https://stimson.org/category/commentary/feed/",
    ],
    "GO4E487AE9": [
        "https://www.euractiv.com/feed/",
        "https://www.euractiv.com/section/politics/feed/",
    ],
    "GO09157312": [
        "https://www.energyvoice.com/category/oil-gas/feed/",
        "https://www.energyvoice.com/news/feed/",
    ],
    "GO0592F182": [
        "https://www.miningweekly.com/page/rss",
        "https://www.engineeringnews.co.za/page/rss",
    ],
    "WM014E7189": [
        "https://indianexpress.com/section/world/feed/",
        "https://indianexpress.com/print/front-page/feed/",
    ],
    "WMBE29F288": [
        "https://japantoday.com/category/national/feed",
        "https://japantoday.com/category/world/feed",
    ],
    "WMC5563538": [
        "https://www.news24.com/news24/rss",
        "https://feeds.news24.com/articles/news24/SouthAfrica/rss",
    ],
    "WM65F63780": [
        "https://www.vanguardngr.com/feed",
        "https://www.vanguardngr.com/category/national-news/feed/",
    ],
    "WM6DEF7587": [
        "https://tuoitrenews.vn/rss",
        "https://tuoitre.vn/rss/tin-moi-nhat.rss",
    ],
    "WM48AD312D": [
        "https://kr-asia.com/feed",
        "https://kr-asia.com/category/news/feed",
    ],
    "WM18C0F634": [
        "https://contxto.com/en/feed/",
        "https://www.contxto.com/feed/",
    ],
    "WM0B8E32A7": [
        "https://www.techstars.com/blog/feed/",
        "https://blog.techstars.com/feed",
    ],
    "WM5DCA39A8": [
        "https://www.nfx.com/post/feed",
        "https://www.nfx.com/essays/rss",
    ],
    "WM718C2B15": [
        "https://bothsidesofthetable.com/feed",
        "https://bothsidesofthetable.medium.com/feed",
    ],
    "WM2CB6D54C": [
        "https://pitchbook.com/news/articles/rss",
        "https://pitchbook.com/blog/rss",
    ],
    "WM74AFB771": [
        "https://www.primicias.ec/noticias/feed/",
        "https://www.primicias.ec/rss",
    ],
    "WM23C27BE1": [
        "https://english.aawsat.com/home/feed",
        "https://aawsat.com/english/rss.xml",
    ],
    "WM28022C7F": [
        "https://singularityhub.com/feed",
        "https://www.singularityhub.com/feed/",
    ],
    "WM7A880DDC": [
        "https://www.rigzone.com/news/oil_gas_news.aspx?xml=1",
        "https://www.ogj.com/rss/articles",
    ],
    "GO194AFF85": [
        "https://www.spglobal.com/platts/en/rss-feed/commodities",
        "https://www.spglobal.com/marketintelligence/en/rss",
    ],
    # STRAN / new
    "NATO": [],  # resolved by name below
}

# Also by name for STRAN extras without stable old ids
NAME_ALTS: dict[str, list[str]] = {
    "NATO News": [
        "https://www.nato.int/rss-feeds/nato-news.xml",
        "https://www.nato.int/cps/en/natohq/news.rss",
        "https://www.nato.int/structur/rss/natolive.xml",
        "https://feeds.bbci.co.uk/news/world/europe/rss.xml",  # fallback geo coverage — skip if too broad
    ],
    "NATO Press": [
        "https://www.nato.int/rss-feeds/press-releases.xml",
        "https://www.nato.int/cps/en/natolive/official_texts.xml",
    ],
    "EEAS News": [
        "https://www.eeas.europa.eu/delegations/rss_en",
        "https://www.eeas.europa.eu/eeas/press-material_en?rss",
    ],
    "Council of the EU": [
        "https://www.consilium.europa.eu/en/press/press-releases/rss",
        "https://newsroom.consilium.europa.eu/feed/en",
    ],
    "EU Observer": [
        "https://euobserver.com/rss-feeds/latest",
        "https://euobserver.com/feed",
    ],
    "Mediaset Infobox": [
        "https://www.tgcom24.mediaset.it/rss/homepage.xml",
        "https://www.mediaset.it/rss/informazione.xml",
    ],
    "AP Top News": [
        "https://rsshub.app/apnews/topics/apf-topnews",
        "https://feedx.net/rss/ap.xml",
    ],
    "Korea Herald": [
        "https://www.koreaherald.com/common/rss.php",
        "http://www.koreaherald.com/rss_xml.htm",
        "https://www.koreatimes.co.kr/www/rss/rss.xml",
    ],
    "News24": [
        "https://feeds.news24.com/articles/news24/TopStories/rss",
        "https://www.news24.com/feed",
    ],
}


def try_url(url: str, insecure: bool = False) -> bool:
    if not url or "news.google.com" in url or url.endswith("europe/rss.xml"):
        # skip too-broad BBC-Europe fallback used only in draft list
        if "feeds.bbci.co.uk/news/world/europe" in url:
            return False
    try:
        data = None
        if insecure:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=20, context=ctx) as r:
                data = r.read(200_000)
        else:
            data = hi.fetch_bytes(url, 20)
        items = hi.parse_rss(data)
        return len(items) > 0
    except Exception:
        return False


def main() -> int:
    cfg = json.loads((HERE / "intel_feeds.json").read_text(encoding="utf-8"))
    fails = json.loads((HERE / "feed_failures.json").read_text(encoding="utf-8"))
    feeds_by_id = {f["id"]: f for f in cfg["feeds"]}
    fixed = 0

    for fail in fails:
        fid = fail["id"]
        name = fail.get("name", "")
        feed = feeds_by_id.get(fid)
        if not feed:
            continue
        candidates = []
        candidates.extend(ALTS.get(fid, []))
        candidates.extend(NAME_ALTS.get(name, []))
        # also retry current with insecure SSL
        candidates.append(feed.get("url", ""))
        seen = set()
        found = None
        for u in candidates:
            if not u or u in seen:
                continue
            seen.add(u)
            if try_url(u) or try_url(u, insecure=True):
                found = u
                break
        if found and found != feed.get("url"):
            print(f"FIX {name[:30]:30} -> {found[:90]}")
            feed["url"] = found
            host = urlparse(found).netloc.lower()
            feed["origin"] = host[4:] if host.startswith("www.") else host
            fixed += 1
        elif found:
            print(f"KEEP {name[:30]:30} works as-is / ssl")
            fixed += 1
        else:
            print(f"MISS {name[:30]:30} | {fail.get('error','')[:60]}")

    (HERE / "intel_feeds.json").write_text(
        json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(f"fixed_or_kept={fixed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
