from pathlib import Path
import re
import json

t = Path("cache/ingest/_wm_layers.ts").read_text(encoding="utf-8")
# key: def('key', ..., 'Label', ...)
rows = re.findall(
    r"^\s{2}([a-zA-Z][a-zA-Z0-9]+):\s+def\(\s*'[^']+'\s*,\s*'[^']*'\s*,\s*'[^']*'\s*,\s*'([^']+)'",
    t,
    re.M,
)
print("layers", len(rows))
for k, lab in rows:
    print(f"{k:28} {lab}")

# Our coverage buckets - what we actually ingest live/pipe/ser
ours = {
    "natural disasters": ["usgs", "gdacs", "nasa-eonet", "nasa-firms"],
    "flights / ADS-B": ["opensky-eu"],
    "AIS / maritime": ["portwatch pipeline (IMF PortWatch)", "NOT live AISStream"],
    "cyber IOC": ["feodo-tracker"],
    "markets/crypto": ["coingecko", "binance", "polymarket", "defillama", "yahoo-vix", "cnn-fear-greed"],
    "weather sample": ["openmeteo-london/houston"],
    "sanctions index": ["opensanctions-datasets"],
    "gas/power EU": ["gie-agsi", "fraunhofer", "entsoe harvest"],
    "macro": ["FRED/ECB/IMF WEO harvest", "worldbank-cpi-us"],
    "news RSS concrete": ["~370 feeds"],
    "news GN topics": ["EXCLUDED by design (~400 WM uses)"],
}

gaps_typical = [
    ("ucdpEvents", "UCDP GED conflict events API — not ingested"),
    ("iranAttacks / military events", "WM curated conflict registries — not ingested as API"),
    ("ais live", "AISStream / live vessel positions — we only have PortWatch daily aggregates"),
    ("flights full", "FAA ASWS, AviationStack, ICAO NOTAMs, Wingbits — we only have OpenSky EU bbox"),
    ("cyber fuller", "URLhaus, AlienVault OTX, AbuseIPDB, ransomware.live — we only have Feodo"),
    ("waterways/chokepoints live", "NGA warnings + AIS classifiers — we have PortWatch + desk CSV"),
    ("CII choropleth", "WM proprietary CII v8 service — no equivalent"),
    ("hotspots escalation", "WM hotspot registry + scoring — not replicated"),
    ("military bases overlays", "static WM geo registries — map UI assets, not our INGEST page"),
    ("pipelines / commodity geo", "static WM registries"),
    ("finance radar 29 exchanges", "WM finance service — we have sparse tickers (VIX, Coinbase, Binance)"),
    ("Google News topic feeds (~404)", "intentionally excluded (not concrete publishers)"),
    ("RT / RT Russia RSS", "removed (connection blocked here)"),
    ("cloudflare-outages live stream", "still points at Google News in our live_streams.json"),
]

print("\nOUR INBOUND BUCKETS")
for k, v in ours.items():
    print(f"  {k}: {', '.join(v)}")
print("\nGAP LIST VS WM PRODUCT")
for a, b in gaps_typical:
    print(f"  - {a}: {b}")

out = {
    "wm_layers": [{"key": k, "label": lab} for k, lab in rows],
    "rss_summary": {
        "wm_total": 673,
        "wm_concrete": 269,
        "wm_gnews": 404,
        "ours_concrete": 370,
        "missing_concrete_rss": ["RT", "RT Russia"],
        "gnews_gap_by_design": 404,
    },
    "gaps": [{"item": a, "note": b} for a, b in gaps_typical],
}
Path("cache/ingest/wm_coverage_report.json").write_text(
    json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8"
)
print("\nWrote cache/ingest/wm_coverage_report.json")
