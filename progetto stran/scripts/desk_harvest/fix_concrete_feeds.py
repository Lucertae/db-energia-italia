#!/usr/bin/env python3
"""Apply concrete publisher RSS URL fixes (no Google News) + STRAN network coverage.

1. Patch broken primary URLs in intel_feeds.json
2. Rewrite intel_feed_overrides.json with concrete-only alternates
3. Append France 24 / Mediaset / NATO / EU / Asia / Africa network feeds
4. Drop Google News Hormuz scaffold from STRAN extras if present
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
FEEDS = HERE / "intel_feeds.json"
OVERRIDES = HERE / "intel_feed_overrides.json"

# Concrete alternates by feed id (verified/probe-candidates; no news.google.com)
CONCRETE_BY_ID: dict[str, str] = {
    "ST5EB96B28": "https://www.eia.gov/rss/todayinenergy.xml",
    "WMB959771A": "https://www.eia.gov/rss/todayinenergy.xml",
    "ST40468AEF": "https://www.iea.org/feeds/news.xml",
    "STDF977490": "https://www.opec.org/opec_web/staticfiles_txt/rss/news.xml",
    "GO29F396B1": "https://www.defenseone.com/rss/all/",
    "GOECCBD1E7": "http://rss.cnn.com/rss/edition.rss",
    "GO31A1825F": "https://www.csis.org/analysis/feed.xml",
    "GO5CAF5440": "https://www.cfr.org/rss/feed.xml",
    "GO6B6F3285": "https://kyivindependent.com/feed/rss/",
    "GO92E79FF3": "https://asia.nikkei.com/rss/feed/nar",
    "GO030EE1DB": "https://www.icrc.org/en/rss.xml",
    "GOC12E8AAD": "https://www.volcanodiscovery.com/news/rss.xml",
    "GO09C8AFDE": "https://www.nasa.gov/rss/dyn/earth.rss",
    "WMD750A297": "https://www.cisa.gov/cybersecurity-advisories/all.xml",
    "GO1E8B43D9": "https://reliefweb.int/updates/rss.xml",
    "GO2D0A890F": "https://reliefweb.int/disasters/rss.xml",
    "WM55D5EA4C": "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
    "GO0AE8ED80": "https://www.unhcr.org/rss.xml",
    "GOEF1047D9": "https://www.msf.org/rss.xml",
    "GOB497BBAF": "https://www.euronews.com/rss?format=mrss",
    "GO4E487AE9": "https://www.euractiv.com/section/all/feed/",
    "GO0958E426": "https://www.chathamhouse.org/rss/publications.xml",
    "GO85F9D667": "https://www.brookings.edu/feed/",
    "GO83D133A2": "https://www.iiss.org/online-analysis/rss/",
    "GO39566D0C": "https://www.rand.org/pubs/research_reports.rss",
    "WM54E3CF70": "https://www.rand.org/blog.rss",
    "GO42FE3F4E": "https://www.state.gov/rss-feed/press-releases/feed/",
    "GO7AC1DB21": "https://www.whitehouse.gov/feed/",
    "GOA7E58C72": "https://www.maritime-executive.com/rss",
    "GO0592F182": "https://www.miningweekly.com/rss",
    "WM509E1B73": "https://www.mining.com/feed/",
    "WM47E7C19A": "https://www.australianmining.com.au/feed/",
    "WMC4337AC8": "https://www.northernminer.com/feed/",
    "GO194AFF85": "https://www.spglobal.com/commodityinsights/en/rss-feed/all.rss",
    "WM7A880DDC": "https://www.rigzone.com/news/rss.asp",
    "GO09157312": "https://www.energyvoice.com/feed/",
    "GO9C142E1C": "https://issafrica.org/iss-today/feed",
    "WM65F63780": "https://www.vanguardngr.com/feed/",
    "WMC5563538": "https://feeds.news24.com/articles/news24/TopStories/rss",
    "WM014E7189": "https://indianexpress.com/feed/",
    "WMBE29F288": "https://japantoday.com/feed",
    "WM6DEF7587": "https://tuoitrenews.vn/rss/news.rss",
    "WM48AD312D": "https://kr-asia.com/feed/",
    "WM0385AA35": "https://www.techinasia.com/feed",
    "WM18C0F634": "https://contxto.com/feed/",
    "WM0B8E32A7": "https://www.techstars.com/the-line/feed",
    "WM5DCA39A8": "https://www.nfx.com/feed.xml",
    "WM4BD28B3C": "http://www.aaronsw.com/2002/feeds/pgessays.rss",
    "WM718C2B15": "https://bothsidesofthetable.com/feed/",
    "WM2CB6D54C": "https://pitchbook.com/news/rss",
    "WMBB56901A": "https://www.cbinsights.com/research/feed/",
    "WM74AFB771": "https://www.primicias.ec/feed/",
    "GO580E8164": "https://www.arabnews.com/rss.xml",
    "WM23C27BE1": "https://english.aawsat.com/rss.xml",
    "WM9CC246AC": "https://www.fpri.org/feed/",
    "WMD1C2DB8C": "https://www.stimson.org/feed/",
    "GO2FDE7B9A": "https://www.armscontrol.org/act/rss.xml",
    "WM28022C7F": "https://singularityhub.com/feed/",
    "WM4A635459": "https://goldsilverworlds.com/feed/",
    "WM022446E2": "https://www.rt.com/rss/",
    "WM6E94AAAB": "https://www.rt.com/rss/russia/",
    "WM6382DD50": "https://www.atv.hu/rss",
}

# Major network / regional coverage — concrete publishers only
STRAN_NETWORKS: list[dict] = [
    # Europe / France / Italy / EU
    {"name": "France 24 EN", "url": "https://www.france24.com/en/rss", "category": "stran-eu"},
    {"name": "France 24 FR", "url": "https://www.france24.com/fr/rss", "category": "stran-eu"},
    {"name": "France 24 Middle East", "url": "https://www.france24.com/en/middle-east/rss", "category": "stran-eu"},
    {"name": "France 24 Africa", "url": "https://www.france24.com/en/africa/rss", "category": "stran-africa"},
    {"name": "Euronews", "url": "https://www.euronews.com/rss?format=mrss", "category": "stran-eu"},
    {"name": "Euractiv", "url": "https://www.euractiv.com/section/all/feed/", "category": "stran-eu"},
    {"name": "Politico Europe", "url": "https://www.politico.eu/feed/", "category": "stran-eu"},
    {"name": "EU Observer", "url": "https://euobserver.com/rss.xml", "category": "stran-eu"},
    {"name": "DW News", "url": "https://rss.dw.com/rdf/rss-en-all", "category": "stran-eu"},
    {"name": "ANSA Top", "url": "https://www.ansa.it/sito/notizie/topnews/topnews_rss.xml", "category": "stran-eu"},
    {"name": "ANSA Mondo", "url": "https://www.ansa.it/sito/notizie/mondo/mondo_rss.xml", "category": "stran-eu"},
    {"name": "RAI News", "url": "https://www.rainews.it/rss/tutti", "category": "stran-eu"},
    {"name": "TgCom24", "url": "https://www.tgcom24.mediaset.it/rss/homepage.xml", "category": "stran-eu"},
    {"name": "Mediaset Infobox", "url": "https://www.mediasetinfinity.mediaset.it/feed/rss", "category": "stran-eu"},
    {"name": "Il Sole 24 Ore", "url": "https://www.ilsole24ore.com/rss/italia.xml", "category": "stran-eu"},
    {"name": "Corriere della Sera", "url": "https://xml2.corriereobjects.it/rss/homepage.xml", "category": "stran-eu"},
    # NATO / defense / institutions
    {"name": "NATO News", "url": "https://www.nato.int/cps/en/natohq/news.htm?format=xml", "category": "stran-defense"},
    {"name": "NATO Press", "url": "https://www.nato.int/cps/en/natolive/news_press.htm?format=xml", "category": "stran-defense"},
    {"name": "EEAS News", "url": "https://www.eeas.europa.eu/eeas/rss_en", "category": "stran-eu"},
    {"name": "European Commission", "url": "https://ec.europa.eu/commission/presscorner/api/rss", "category": "stran-eu"},
    {"name": "Council of the EU", "url": "https://www.consilium.europa.eu/en/press/press-releases/rss/", "category": "stran-eu"},
    {"name": "Defense One", "url": "https://www.defenseone.com/rss/all/", "category": "stran-defense"},
    {"name": "Defense News", "url": "https://www.defensenews.com/arc/outboundfeeds/rss/?outputType=xml", "category": "stran-defense"},
    {"name": "Breaking Defense", "url": "https://breakingdefense.com/feed/", "category": "stran-defense"},
    # Asia
    {"name": "Nikkei Asia", "url": "https://asia.nikkei.com/rss/feed/nar", "category": "stran-asia"},
    {"name": "SCMP", "url": "https://www.scmp.com/rss/91/feed", "category": "stran-asia"},
    {"name": "Channel News Asia", "url": "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml", "category": "stran-asia"},
    {"name": "Straits Times Asia", "url": "https://www.straitstimes.com/news/asia/rss.xml", "category": "stran-asia"},
    {"name": "Japan Times", "url": "https://www.japantimes.co.jp/feed/", "category": "stran-asia"},
    {"name": "The Hindu", "url": "https://www.thehindu.com/news/feeder/default.rss", "category": "stran-asia"},
    {"name": "Indian Express", "url": "https://indianexpress.com/feed/", "category": "stran-asia"},
    {"name": "Korea Herald", "url": "https://www.koreaherald.com/rss/", "category": "stran-asia"},
    {"name": "Asia Times", "url": "https://asiatimes.com/feed/", "category": "stran-asia"},
    # Africa
    {"name": "Africanews", "url": "https://www.africanews.com/feed/", "category": "stran-africa"},
    {"name": "Africa Report", "url": "https://www.theafricareport.com/feed/", "category": "stran-africa"},
    {"name": "ISS Africa", "url": "https://issafrica.org/iss-today/feed", "category": "stran-africa"},
    {"name": "News24", "url": "https://feeds.news24.com/articles/news24/TopStories/rss", "category": "stran-africa"},
    {"name": "Daily Maverick", "url": "https://www.dailymaverick.co.za/dmrss/", "category": "stran-africa"},
    {"name": "Premium Times NG", "url": "https://www.premiumtimesng.com/feed", "category": "stran-africa"},
    {"name": "AllAfrica", "url": "https://allafrica.com/tools/headlines/rdf/latest/headlines.rdf", "category": "stran-africa"},
    {"name": "BBC Africa", "url": "https://feeds.bbci.co.uk/news/world/africa/rss.xml", "category": "stran-africa"},
    # Global wires still concrete
    {"name": "AP Top News", "url": "https://rsshub.app/apnews/topics/apf-topnews", "category": "stran-wire"},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml", "category": "stran-wire"},
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml", "category": "stran-wire"},
]


def is_gnews(url: str) -> bool:
    u = (url or "").lower()
    return "news.google.com" in u or "/rss/search" in u


def slug_id(prefix: str, name: str, url: str) -> str:
    h = hashlib.sha1(f"{name}|{url}".encode()).hexdigest()[:8].upper()
    p = re.sub(r"[^A-Z]", "", prefix.upper())[:2] or "ST"
    return f"{p}{h}"[:11]


def url_host(url: str) -> str:
    try:
        h = urlparse(url).netloc.lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def main() -> int:
    cfg = json.loads(FEEDS.read_text(encoding="utf-8"))
    feeds = cfg.get("feeds", [])
    by_url = {(f.get("url") or "").rstrip("/"): f for f in feeds}
    by_name = {(f.get("name") or "").lower(): f for f in feeds}

    patched = 0
    for f in feeds:
        fid = f.get("id", "")
        if fid in CONCRETE_BY_ID:
            new_u = CONCRETE_BY_ID[fid]
            if f.get("url") != new_u:
                f["url"] = new_u
                f["origin"] = url_host(new_u)
                patched += 1
        # strip Hormuz/Malacca Google News scaffolds
        if is_gnews(f.get("url", "")) and any(
            k in (f.get("name") or "").lower() for k in ("hormuz", "malacca", "chokepoint")
        ):
            f["_drop"] = True

    feeds = [f for f in feeds if not f.pop("_drop", False)]

    added = 0
    for nf in STRAN_NETWORKS:
        key = nf["url"].rstrip("/")
        if key in by_url:
            continue
        if nf["name"].lower() in by_name:
            # same name, different URL — upgrade if current is gnews
            existing = by_name[nf["name"].lower()]
            if is_gnews(existing.get("url", "")):
                existing["url"] = nf["url"]
                existing["origin"] = url_host(nf["url"])
                existing["category"] = nf["category"]
                patched += 1
            continue
        entry = {
            "id": slug_id("ST", nf["name"], nf["url"]),
            "name": nf["name"],
            "url": nf["url"],
            "category": nf["category"],
            "origin": url_host(nf["url"]),
        }
        feeds.append(entry)
        by_url[key] = entry
        by_name[nf["name"].lower()] = entry
        added += 1

    cfg["feeds"] = feeds
    cfg["count"] = len(feeds)
    FEEDS.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    # overrides: concrete only (same map + no gnews leftovers)
    over = {
        k: v for k, v in CONCRETE_BY_ID.items() if not is_gnews(v)
    }
    meta = {
        "version": 2,
        "description": "Concrete publisher URL overrides only (no Google News).",
        "overrides": over,
    }
    OVERRIDES.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"patched={patched} added={added} total_feeds={len(feeds)} overrides={len(over)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
