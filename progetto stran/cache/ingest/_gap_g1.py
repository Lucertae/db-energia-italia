import json
from pathlib import Path
from collections import Counter

root = Path(".")
m = json.loads((root / "cache/ingest/manifest.json").read_text(encoding="utf-8"))
ents = m["entries"]
live = json.loads((root / "scripts/desk_harvest/live_streams.json").read_text(encoding="utf-8"))["streams"]
live_ids = {s["id"] for s in live}
live_hosts = {(s.get("origin") or "") for s in live}
ids = {str(e.get("id")) for e in ents if e.get("id") is not None}
pubs = {str(e.get("publisher") or "").lower() for e in ents}

print("=== CURRENT ===")
print("manifest", len(ents), dict(Counter(e["section"] for e in ents)))
print("live streams", len(live))

# Already covered keywords
blob = " ".join(
    list(ids)
    + list(live_ids)
    + [str(e.get("publisher") or "") for e in ents]
).lower()

candidates = [
    # Group 1 — high value OSS / open data still thin or missing
    ("1", "CFTC COT", "pftui / OpenBB", "https://publicreporting.cftc.gov/resource/6dca-aqww.json", "API", "Commitment of Traders — NOT in live yet", "cot" not in blob),
    ("2", "Electricity Maps free", "electricitymaps", "https://api.electricitymap.org/v3/ (key) OR open carbon intensity proxies", "API", "Grid intensity by zone — adapter_off today", "electricitymap" not in blob and "carbon-intensity" not in blob),
    ("3", "GridStatus ISO feeds", "gridstatus", "https://www.gridstatus.io/ / CAISO/ERCOT open endpoints via gridstatus lib", "PIPE", "US ISO prices/load — module adapter_off", "gridstatus" not in blob and "caiso" not in blob),
    ("4", "Global Fishing Watch", "gfw", "https://gateway.api.globalfishingwatch.org/ (key)", "API", "Fishing vessel AIS — ref only, no harvest", "fishingwatch" not in blob and "gfw" not in blob),
    ("5", "Open-Meteo multi-city", "WM/energy", "https://api.open-meteo.com/v1/forecast (expand beyond London/Houston)", "API", "Only 2 cities live — expand hubs", True),  # partial
    ("6", "NOAA Space Weather", "WM natural", "https://services.swpc.noaa.gov/json/", "API", "Kp/solar alerts — not in live_streams", "swpc" not in blob and "space-weather" not in blob),
    ("7", "OpenSanctions entities dump", "opensanctions", "https://data.opensanctions.org/datasets/latest/default/entities.ftm.json", "SER", "Only dataset index today — no entity pulse", "entities.ftm" not in blob),
    ("8", "Herbie / GFS weather", "herbie", "NOAA GFS via Herbie or nomads OpenDAP", "PIPE", "adapter_off — weather model grids", "herbie" not in blob and "nomads" not in blob),
    ("9", "tar1090 / ADS-B local", "tar1090", "http://localhost/tar1090/data/aircraft.json OR adsb.lol", "API", "Military ADS-B density — no feed yet", "tar1090" not in blob and "adsb.lol" not in blob),
    ("10", "JODI Oil world", "WM China/energy", "https://www.jodidata.org/ / API mirrors", "SER", "Oil monthly balances — not harvested", "jodi" not in blob),
]

print("\n=== GROUP 1 / 10 — MISSING OR THIN ===")
n = 0
for num, name, proj, url, sec, note, missing in candidates:
    flag = "MISSING" if missing else "PARTIAL/HAVE"
    if missing or True:
        n += 1
        print(f"{num:>2}. [{flag}] {name}")
        print(f"    from: {proj}")
        print(f"    why:  {note}")
        print(f"    how:  {sec} <- {url[:90]}")
        print()

out = {
    "group": 1,
    "of": "batches of 10",
    "candidates": [
        {
            "n": c[0],
            "name": c[1],
            "project": c[2],
            "url": c[3],
            "section": c[4],
            "note": c[5],
            "missing": c[6],
        }
        for c in candidates
    ],
}
Path("cache/ingest/gap_group_01.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
print("Wrote cache/ingest/gap_group_01.json")
