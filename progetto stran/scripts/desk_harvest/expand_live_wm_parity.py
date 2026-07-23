#!/usr/bin/env python3
"""Merge World Monitor free live endpoints into live_streams.json."""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "live_streams.json"

# Free / optional-key streams used by WM seeds — skip if id already present.
NEW = [
    {"id": "wm-feodo-ipblock", "name": "Feodo Tracker IP blocklist",
     "url": "https://feodotracker.abuse.ch/downloads/ipblocklist.json",
     "type": "json", "sector": "CYBER", "refresh_sec": 3600,
     "origin": "feodotracker.abuse.ch", "ref": "worldmonitor"},
    {"id": "wm-c2intel-ipc2s", "name": "C2IntelFeeds IPC2s 30d",
     "url": "https://raw.githubusercontent.com/drb-ra/C2IntelFeeds/master/feeds/IPC2s-30day.csv",
     "type": "csv", "sector": "CYBER", "refresh_sec": 3600,
     "origin": "github.com", "ref": "worldmonitor"},
    {"id": "wm-nga-broadcast-warn", "name": "NGA MSI broadcast warnings",
     "url": "https://msi.nga.mil/api/publications/broadcast-warn?output=json&status=A",
     "type": "json", "sector": "MARITIME", "refresh_sec": 1800,
     "origin": "msi.nga.mil", "ref": "worldmonitor"},
    {"id": "wm-oref-alerts", "name": "Israel OREF live alerts",
     "url": "https://www.oref.org.il/WarningMessages/alert/alerts.json",
     "type": "json", "sector": "GEO", "refresh_sec": 60,
     "origin": "oref.org.il", "ref": "worldmonitor", "insecure_ssl": True},
    {"id": "wm-gpsjam", "name": "GPSJam interference",
     "url": "https://gpsjam.org/data",
     "type": "json", "sector": "GEO", "refresh_sec": 3600,
     "origin": "gpsjam.org", "ref": "worldmonitor"},
    {"id": "wm-safecast", "name": "Safecast radiation",
     "url": "https://api.safecast.org/measurements.json?distance=50000&limit=50",
     "type": "json", "sector": "NATURAL", "refresh_sec": 1800,
     "origin": "api.safecast.org", "ref": "worldmonitor"},
    {"id": "wm-unhcr-pop", "name": "UNHCR population",
     "url": "https://api.unhcr.org/population/v1/population/?limit=20&page=1",
     "type": "json", "sector": "HUMANITARIAN", "refresh_sec": 86400,
     "origin": "api.unhcr.org", "ref": "worldmonitor"},
    {"id": "wm-nsidc-seaice", "name": "NSIDC sea ice daily",
     "url": "https://noaadata.apps.nsidc.org/NOAA/G02135/north/daily/data/N_seaice_extent_daily_v4.0.csv",
     "type": "csv", "sector": "CLIMATE", "refresh_sec": 86400,
     "origin": "nsidc.org", "ref": "worldmonitor"},
    {"id": "wm-noaa-co2-mlo", "name": "NOAA Mauna Loa CO2 daily",
     "url": "https://gml.noaa.gov/webdata/ccgg/trends/co2/co2_daily_mlo.txt",
     "type": "csv", "sector": "CLIMATE", "refresh_sec": 86400,
     "origin": "gml.noaa.gov", "ref": "worldmonitor"},
    {"id": "wm-carbonbrief-rss", "name": "Carbon Brief RSS",
     "url": "https://www.carbonbrief.org/feed",
     "type": "rss", "sector": "CLIMATE", "refresh_sec": 3600,
     "origin": "carbonbrief.org", "ref": "worldmonitor"},
    {"id": "wm-copernicus-rss", "name": "Copernicus Climate RSS",
     "url": "https://climate.copernicus.eu/rss.xml",
     "type": "rss", "sector": "CLIMATE", "refresh_sec": 3600,
     "origin": "climate.copernicus.eu", "ref": "worldmonitor"},
    {"id": "wm-nasa-eo-rss", "name": "NASA Earth Observatory RSS",
     "url": "https://earthobservatory.nasa.gov/feeds/earth-observatory.rss",
     "type": "rss", "sector": "CLIMATE", "refresh_sec": 3600,
     "origin": "earthobservatory.nasa.gov", "ref": "worldmonitor"},
    {"id": "wm-flightglobal-rss", "name": "FlightGlobal RSS",
     "url": "https://www.flightglobal.com/rss",
     "type": "rss", "sector": "TRANSPORT", "refresh_sec": 3600,
     "origin": "flightglobal.com", "ref": "worldmonitor"},
    {"id": "wm-simpleflying-rss", "name": "Simple Flying RSS",
     "url": "https://simpleflying.com/feed/",
     "type": "rss", "sector": "TRANSPORT", "refresh_sec": 3600,
     "origin": "simpleflying.com", "ref": "worldmonitor"},
    {"id": "wm-aerotime-rss", "name": "AeroTime RSS",
     "url": "https://aerotime.aero/feed",
     "type": "rss", "sector": "TRANSPORT", "refresh_sec": 3600,
     "origin": "aerotime.aero", "ref": "worldmonitor"},
    {"id": "wm-outbreak-rss", "name": "Outbreak News Today",
     "url": "https://outbreaknewstoday.com/feed/",
     "type": "rss", "sector": "HUMANITARIAN", "refresh_sec": 3600,
     "origin": "outbreaknewstoday.com", "ref": "worldmonitor"},
    {"id": "wm-state-travel-rss", "name": "US State Dept travel advisories",
     "url": "https://travel.state.gov/_res/rss/TAsTWs.xml",
     "type": "rss", "sector": "GEO", "refresh_sec": 3600,
     "origin": "travel.state.gov", "ref": "worldmonitor"},
    {"id": "wm-coinpaprika", "name": "CoinPaprika tickers",
     "url": "https://api.coinpaprika.com/v1/tickers?limit=20",
     "type": "json", "sector": "FINANCE", "refresh_sec": 300,
     "origin": "api.coinpaprika.com", "ref": "worldmonitor"},
    {"id": "wm-portwatch-ports", "name": "IMF PortWatch daily ports",
     "url": "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Ports_Data/FeatureServer/0/query?where=1%3D1&outFields=*&f=json&resultRecordCount=50",
     "type": "json", "sector": "MARITIME", "refresh_sec": 3600,
     "origin": "arcgis.com", "ref": "worldmonitor"},
    {"id": "wm-portwatch-disrupt", "name": "IMF PortWatch disruptions",
     "url": "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/portwatch_disruptions_database/FeatureServer/0/query?where=1%3D1&outFields=*&f=json&resultRecordCount=50",
     "type": "json", "sector": "MARITIME", "refresh_sec": 3600,
     "origin": "arcgis.com", "ref": "worldmonitor"},
    {"id": "wm-pizzint-dash", "name": "PizzINT dashboard",
     "url": "https://www.pizzint.watch/api/dashboard-data",
     "type": "json", "sector": "GEO", "refresh_sec": 900,
     "origin": "pizzint.watch", "ref": "worldmonitor"},
    {"id": "wm-treasury-mts", "name": "US Treasury MTS table 9",
     "url": "https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v1/accounting/mts/mts_table_9?page[size]=10",
     "type": "json", "sector": "FINANCE", "refresh_sec": 86400,
     "origin": "fiscaldata.treasury.gov", "ref": "worldmonitor"},
    # keyed optional
    {"id": "wm-aviationstack", "name": "AviationStack flights",
     "url": "https://api.aviationstack.com/v1/flights",
     "type": "json", "sector": "TRANSPORT", "refresh_sec": 600,
     "origin": "api.aviationstack.com", "ref": "worldmonitor",
     "env_key": "AVIATIONSTACK_API_KEY", "optional": True},
    {"id": "wm-otx-export", "name": "OTX indicators export",
     "url": "https://otx.alienvault.com/api/v1/indicators/export",
     "type": "json", "sector": "CYBER", "refresh_sec": 3600,
     "origin": "otx.alienvault.com", "ref": "worldmonitor",
     "env_key": "OTX_API_KEY", "optional": True},
    {"id": "wm-abuseipdb", "name": "AbuseIPDB blacklist",
     "url": "https://api.abuseipdb.com/api/v2/blacklist",
     "type": "json", "sector": "CYBER", "refresh_sec": 3600,
     "origin": "api.abuseipdb.com", "ref": "worldmonitor",
     "env_key": "ABUSEIPDB_API_KEY", "optional": True},
    {"id": "wm-finnhub-quote", "name": "Finnhub SPY quote",
     "url": "https://finnhub.io/api/v1/quote?symbol=SPY",
     "type": "json", "sector": "FINANCE", "refresh_sec": 300,
     "origin": "finnhub.io", "ref": "worldmonitor",
     "env_key": "FINNHUB_API_KEY", "optional": True},
    {"id": "wm-firms-map", "name": "NASA FIRMS VIIRS CSV (MAP_KEY)",
     "url": "https://firms.modaps.eosdis.nasa.gov/api/area/csv",
     "type": "csv", "sector": "NATURAL", "refresh_sec": 3600,
     "origin": "firms.modaps.eosdis.nasa.gov", "ref": "worldmonitor",
     "env_key": "NASA_FIRMS_MAP_KEY", "optional": True,
     "note": "Append /MAP_KEY/world/VIIRS_SNPP_NRT/1 to url in harvester when key set"},
]


def main() -> int:
    doc = json.loads(OUT.read_text(encoding="utf-8"))
    streams = doc.get("streams") or []
    have = {s.get("id") for s in streams}
    added = 0
    for s in NEW:
        if s["id"] in have:
            continue
        streams.append(s)
        have.add(s["id"])
        added += 1
    doc["streams"] = streams
    doc["updated"] = "2026-07-15"
    doc["description"] = (
        "Live API streams — World Monitor parity (RSS+GN catalogs separate); "
        f"{len(streams)} streams"
    )
    OUT.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"live_streams: +{added} now={len(streams)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
