#!/usr/bin/env python3
"""Expand live_streams.json with World Monitor gap fillers (concrete free endpoints)."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG = HERE / "live_streams.json"

NEW = [
    # Aviation
    {
        "id": "faa-asws",
        "name": "FAA ASWS Airport Status",
        "url": "https://nasstatus.faa.gov/api/airport-status-information",
        "type": "xml",
        "sector": "TRANSPORT",
        "refresh_sec": 300,
        "origin": "nasstatus.faa.gov",
        "ref": "worldmonitor",
    },
    {
        "id": "opensky-us",
        "name": "OpenSky Aircraft CONUS",
        "url": "https://opensky-network.org/api/states/all?lamin=24&lomin=-125&lamax=50&lomax=-66",
        "type": "json",
        "sector": "TRANSPORT",
        "refresh_sec": 60,
        "origin": "opensky-network.org",
        "ref": "worldmonitor",
    },
    {
        "id": "opensky-mena",
        "name": "OpenSky Aircraft MENA",
        "url": "https://opensky-network.org/api/states/all?lamin=12&lomin=25&lamax=42&lomax=60",
        "type": "json",
        "sector": "TRANSPORT",
        "refresh_sec": 60,
        "origin": "opensky-network.org",
        "ref": "worldmonitor",
    },
    {
        "id": "opensky-asia",
        "name": "OpenSky Aircraft East Asia",
        "url": "https://opensky-network.org/api/states/all?lamin=0&lomin=95&lamax=45&lomax=145",
        "type": "json",
        "sector": "TRANSPORT",
        "refresh_sec": 60,
        "origin": "opensky-network.org",
        "ref": "worldmonitor",
    },
    # Maritime / AIS proxy (PortWatch daily remains in PIPE; this is density pulse via MarineTraffic-style free mirrors)
    {
        "id": "ais-stream-optional",
        "name": "AISStream Live (API key)",
        "url": "https://stream.aisstream.io/v0/stream",
        "type": "ws",
        "sector": "MARITIME",
        "refresh_sec": 30,
        "origin": "aisstream.io",
        "env_key": "AISSTREAM_API_KEY",
        "optional": True,
        "note": "WebSocket API — skipped without AISSTREAM_API_KEY",
        "ref": "worldmonitor",
    },
    # Conflict / UCDP substitute + GDELT geo
    {
        "id": "gdelt-geo-conflict",
        "name": "GDELT Geo Conflict",
        "url": "https://api.gdeltproject.org/api/v2/geo/geo?query=conflict%20OR%20war%20OR%20missile&format=geojson&timespan=24h",
        "type": "geojson",
        "sector": "CONFLICT",
        "refresh_sec": 900,
        "origin": "api.gdeltproject.org",
        "ref": "worldmonitor",
    },
    {
        "id": "gdelt-geo-protest",
        "name": "GDELT Geo Protest",
        "url": "https://api.gdeltproject.org/api/v2/geo/geo?query=protest%20OR%20riot&format=geojson&timespan=24h",
        "type": "geojson",
        "sector": "CONFLICT",
        "refresh_sec": 900,
        "origin": "api.gdeltproject.org",
        "ref": "worldmonitor",
    },
    {
        "id": "ucdp-ged-optional",
        "name": "UCDP GED Events (API key)",
        "url": "https://ucdpapi.pcr.uu.se/api/gedevents/23.1",
        "type": "json",
        "sector": "CONFLICT",
        "refresh_sec": 86400,
        "origin": "ucdpapi.pcr.uu.se",
        "env_key": "UCDP_ACCESS_TOKEN",
        "optional": True,
        "note": "Requires UCDP API token",
        "ref": "worldmonitor",
    },
    # Cyber
    {
        "id": "urlhaus-recent",
        "name": "URLhaus Recent Malicious URLs",
        "url": "https://urlhaus.abuse.ch/downloads/csv_recent/",
        "type": "csv",
        "sector": "CYBER",
        "refresh_sec": 3600,
        "origin": "urlhaus.abuse.ch",
        "ref": "worldmonitor",
        "insecure_ssl": True,
    },
    {
        "id": "ransomware-live",
        "name": "Ransomware.live Victims",
        "url": "https://ransomware.live/rss.xml",
        "type": "rss",
        "sector": "CYBER",
        "refresh_sec": 1800,
        "origin": "ransomware.live",
        "ref": "worldmonitor",
    },
    {
        "id": "feodo-recommended",
        "name": "Feodo Tracker Recommended",
        "url": "https://feodotracker.abuse.ch/downloads/ipblocklist_recommended.json",
        "type": "json",
        "sector": "CYBER",
        "refresh_sec": 3600,
        "origin": "feodotracker.abuse.ch",
        "ref": "worldmonitor",
    },
    # Outages (replace Google News cloudflare stream)
    {
        "id": "cloudflare-status",
        "name": "Cloudflare Status History",
        "url": "https://www.cloudflarestatus.com/history.rss",
        "type": "rss",
        "sector": "CYBER",
        "refresh_sec": 900,
        "origin": "cloudflarestatus.com",
        "ref": "worldmonitor",
    },
    {
        "id": "aws-status",
        "name": "AWS Service Status",
        "url": "https://status.aws.amazon.com/rss/all.rss",
        "type": "rss",
        "sector": "CYBER",
        "refresh_sec": 900,
        "origin": "status.aws.amazon.com",
        "ref": "worldmonitor",
    },
    {
        "id": "azure-status",
        "name": "Azure Status Feed",
        "url": "https://azure.status.microsoft/en-us/status/feed/",
        "type": "rss",
        "sector": "CYBER",
        "refresh_sec": 900,
        "origin": "azure.status.microsoft",
        "ref": "worldmonitor",
    },
    # Security advisories / health
    {
        "id": "uk-fcdo-travel",
        "name": "UK FCDO Travel Advice",
        "url": "https://www.gov.uk/foreign-travel-advice.atom",
        "type": "atom",
        "sector": "GEO",
        "refresh_sec": 3600,
        "origin": "gov.uk",
        "ref": "worldmonitor",
    },
    {
        "id": "who-news",
        "name": "WHO News",
        "url": "https://www.who.int/rss-feeds/news-english.xml",
        "type": "rss",
        "sector": "HUMANITARIAN",
        "refresh_sec": 3600,
        "origin": "who.int",
        "ref": "worldmonitor",
    },
    {
        "id": "ecdc-news",
        "name": "ECDC News",
        "url": "https://www.ecdc.europa.eu/en/taxonomy/term/2942/feed",
        "type": "rss",
        "sector": "HUMANITARIAN",
        "refresh_sec": 3600,
        "origin": "ecdc.europa.eu",
        "ref": "worldmonitor",
    },
    {
        "id": "cdc-travel",
        "name": "CDC Travel Notices",
        "url": "https://tools.cdc.gov/api/v2/resources/media/132609.rss",
        "type": "rss",
        "sector": "HUMANITARIAN",
        "refresh_sec": 3600,
        "origin": "cdc.gov",
        "ref": "worldmonitor",
    },
    {
        "id": "disease-sh-global",
        "name": "disease.sh Global Cases",
        "url": "https://disease.sh/v3/covid-19/all",
        "type": "json",
        "sector": "HUMANITARIAN",
        "refresh_sec": 3600,
        "origin": "disease.sh",
        "ref": "worldmonitor",
    },
    # Space / orbital
    {
        "id": "celestrak-stations",
        "name": "CelesTrak Space Stations TLE",
        "url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=stations&FORMAT=json",
        "type": "json",
        "sector": "SPACE",
        "refresh_sec": 3600,
        "origin": "celestrak.org",
        "ref": "worldmonitor",
    },
    {
        "id": "celestrak-active",
        "name": "CelesTrak Active Satellites (sample)",
        "url": "https://celestrak.org/NORAD/elements/gp.php?GROUP=active&FORMAT=json",
        "type": "json",
        "sector": "SPACE",
        "refresh_sec": 7200,
        "origin": "celestrak.org",
        "ref": "worldmonitor",
        "note": "Large catalog — parser samples first objects",
    },
    # Finance radar — major indices via Yahoo
    {
        "id": "yahoo-sp500",
        "name": "Yahoo S&P 500",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/%5EGSPC?interval=1d&range=5d",
        "type": "json",
        "sector": "FINANCE",
        "refresh_sec": 300,
        "origin": "query1.finance.yahoo.com",
        "ref": "worldmonitor",
    },
    {
        "id": "yahoo-nasdaq",
        "name": "Yahoo NASDAQ",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/%5EIXIC?interval=1d&range=5d",
        "type": "json",
        "sector": "FINANCE",
        "refresh_sec": 300,
        "origin": "query1.finance.yahoo.com",
    },
    {
        "id": "yahoo-dji",
        "name": "Yahoo Dow Jones",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/%5EDJI?interval=1d&range=5d",
        "type": "json",
        "sector": "FINANCE",
        "refresh_sec": 300,
        "origin": "query1.finance.yahoo.com",
    },
    {
        "id": "yahoo-ftse",
        "name": "Yahoo FTSE 100",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/%5EFTSE?interval=1d&range=5d",
        "type": "json",
        "sector": "FINANCE",
        "refresh_sec": 300,
        "origin": "query1.finance.yahoo.com",
    },
    {
        "id": "yahoo-dax",
        "name": "Yahoo DAX",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/%5EGDAXI?interval=1d&range=5d",
        "type": "json",
        "sector": "FINANCE",
        "refresh_sec": 300,
        "origin": "query1.finance.yahoo.com",
    },
    {
        "id": "yahoo-cac",
        "name": "Yahoo CAC 40",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/%5EFCHI?interval=1d&range=5d",
        "type": "json",
        "sector": "FINANCE",
        "refresh_sec": 300,
        "origin": "query1.finance.yahoo.com",
    },
    {
        "id": "yahoo-nikkei",
        "name": "Yahoo Nikkei 225",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/%5EN225?interval=1d&range=5d",
        "type": "json",
        "sector": "FINANCE",
        "refresh_sec": 300,
        "origin": "query1.finance.yahoo.com",
    },
    {
        "id": "yahoo-hsi",
        "name": "Yahoo Hang Seng",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/%5EHSI?interval=1d&range=5d",
        "type": "json",
        "sector": "FINANCE",
        "refresh_sec": 300,
        "origin": "query1.finance.yahoo.com",
    },
    {
        "id": "yahoo-sse",
        "name": "Yahoo Shanghai Composite",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/000001.SS?interval=1d&range=5d",
        "type": "json",
        "sector": "FINANCE",
        "refresh_sec": 300,
        "origin": "query1.finance.yahoo.com",
    },
    {
        "id": "yahoo-kospi",
        "name": "Yahoo KOSPI",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/%5EKS11?interval=1d&range=5d",
        "type": "json",
        "sector": "FINANCE",
        "refresh_sec": 300,
        "origin": "query1.finance.yahoo.com",
    },
    {
        "id": "yahoo-bse",
        "name": "Yahoo BSE Sensex",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/%5EBSESN?interval=1d&range=5d",
        "type": "json",
        "sector": "FINANCE",
        "refresh_sec": 300,
        "origin": "query1.finance.yahoo.com",
    },
    {
        "id": "yahoo-asx",
        "name": "Yahoo ASX 200",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/%5EAXJO?interval=1d&range=5d",
        "type": "json",
        "sector": "FINANCE",
        "refresh_sec": 300,
        "origin": "query1.finance.yahoo.com",
    },
    {
        "id": "yahoo-bvsp",
        "name": "Yahoo Bovespa",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/%5EBVSP?interval=1d&range=5d",
        "type": "json",
        "sector": "FINANCE",
        "refresh_sec": 300,
        "origin": "query1.finance.yahoo.com",
    },
    {
        "id": "yahoo-brent",
        "name": "Yahoo Brent Crude",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/BZ%3DF?interval=1d&range=5d",
        "type": "json",
        "sector": "ENERGY",
        "refresh_sec": 300,
        "origin": "query1.finance.yahoo.com",
    },
    {
        "id": "yahoo-wti",
        "name": "Yahoo WTI Crude",
        "url": "https://query1.finance.yahoo.com/v8/finance/chart/CL%3DF?interval=1d&range=5d",
        "type": "json",
        "sector": "ENERGY",
        "refresh_sec": 300,
        "origin": "query1.finance.yahoo.com",
    },
    {
        "id": "bis-policy-rates",
        "name": "BIS Central Bank Policy Rates",
        "url": "https://stats.bis.org/api/v1/data/WS_CBPOL/all/all?format=csv",
        "type": "csv",
        "sector": "FINANCE",
        "refresh_sec": 86400,
        "origin": "stats.bis.org",
        "ref": "worldmonitor",
    },
    {
        "id": "yahoo-fin-news",
        "name": "Yahoo Finance Top Stories",
        "url": "https://finance.yahoo.com/rss/topfinstories",
        "type": "rss",
        "sector": "FINANCE",
        "refresh_sec": 900,
        "origin": "finance.yahoo.com",
    },
    # Natural
    {
        "id": "usgs-significant",
        "name": "USGS Significant Quakes Week",
        "url": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/significant_week.geojson",
        "type": "geojson",
        "sector": "NATURAL",
        "refresh_sec": 600,
        "origin": "earthquake.usgs.gov",
    },
]


def main() -> int:
    cfg = json.loads(CFG.read_text(encoding="utf-8"))
    streams = cfg.get("streams") or []
    by_id = {s["id"]: s for s in streams}

    # Fix Google News cloudflare outages stream in place
    if "cloudflare-outages" in by_id:
        by_id["cloudflare-outages"]["url"] = "https://www.cloudflarestatus.com/history.rss"
        by_id["cloudflare-outages"]["origin"] = "cloudflarestatus.com"
        by_id["cloudflare-outages"]["note"] = "Cloudflare status RSS (replaced Google News query)"
        by_id["cloudflare-outages"]["type"] = "rss"

    added = 0
    for s in NEW:
        if s["id"] in by_id:
            # refresh URL/meta for existing
            by_id[s["id"]].update(s)
            continue
        streams.append(s)
        by_id[s["id"]] = s
        added += 1

    cfg["streams"] = streams
    cfg["updated"] = "2026-07-15"
    cfg["description"] = (
        "Live API streams — WM/GlobeOps parity + gap fillers "
        "(FAA, OpenSky regions, GDELT geo, cyber, advisories, Yahoo exchanges, BIS, CelesTrak)"
    )
    CFG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"streams={len(streams)} added={added}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
