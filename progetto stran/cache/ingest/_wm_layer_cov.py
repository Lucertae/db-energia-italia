from pathlib import Path
import re
import json

t = Path("cache/ingest/_wm_layers.ts").read_text(encoding="utf-8")

# Keys in LAYER_REGISTRY
keys = re.findall(r"^\s{2}([a-zA-Z][a-zA-Z0-9]+):\s+def\(", t, re.M)
print("LAYER_REGISTRY keys", len(keys))

# Explanations with source
expl = []
for m in re.finditer(
    r"key:\s*'([^']+)'.*?category:\s*'([^']*)'.*?purpose:\s*'([^']*)'.*?source:\s*'([^']*)'.*?freshness:\s*'([^']*)'",
    t,
    re.S,
):
    expl.append(
        {
            "key": m.group(1),
            "category": m.group(2),
            "purpose": m.group(3)[:80],
            "source": m.group(4),
            "freshness": m.group(5),
        }
    )

# simpler: source lines near keys
sources = re.findall(
    r"key:\s*'([^']+)'[\s\S]{0,400}?source:\s*'([^']+)'",
    t,
)
print("explanations with source", len(sources))
for k, s in sources:
    print(f"{k:28} | {s}")

Path("cache/ingest/wm_layer_sources.json").write_text(
    json.dumps({"keys": keys, "sources": [{"key": k, "source": s} for k, s in sources]}, indent=2),
    encoding="utf-8",
)

# Coverage gap taxonomy vs our live + pipes
our_tokens = {
    "usgs", "gdacs", "noaa", "eonet", "firms", "gdelt", "opensky", "coingecko",
    "polymarket", "reliefweb", "acled", "defillama", "binance", "open-meteo",
    "openmeteo", "opensanctions", "agsi", "gie", "feodo", "ais", "adsb",
    "flight", "vessel", "marine", "portwatch", "entsoe", "fred", "imf",
    "satellite", "fires", "quake", "conflict", "cyber", "outage",
}

live = json.loads(Path("scripts/desk_harvest/live_streams.json").read_text(encoding="utf-8"))
our_blob = " ".join(
    (s.get("id", "") + " " + s.get("name", "") + " " + s.get("url", "")).lower()
    for s in live.get("streams", [])
)
# also portwatch is a pipeline
our_blob += " portwatch ais entsoe fred eia imf weo"

print("\n=== LAYER SOURCE COVERAGE (heuristic) ===")
missing = []
covered = []
for k, s in sources:
    blob = (k + " " + s).lower()
    hit = any(tok in our_blob or tok in blob and tok in our_blob for tok in our_tokens if tok in blob)
    # simpler keyword map
    kw_map = [
        ("quake", "usgs"),
        ("earthquake", "usgs"),
        ("firms", "firms"),
        ("fire", "eonet"),
        ("gdacs", "gdacs"),
        ("ais", "portwatch"),
        ("vessel", "portwatch"),
        ("ads-b", "opensky"),
        ("adsb", "opensky"),
        ("flight", "opensky"),
        ("aircraft", "opensky"),
        ("gdelt", "gdelt"),
        ("acled", "acled"),
        ("relief", "reliefweb"),
        ("sanctions", "opensanctions"),
        ("crypto", "coingecko"),
        ("weather", "openmeteo"),
        ("gas storage", "agsi"),
        ("cyber", "feodo"),
    ]
    ok = False
    for needle, our in kw_map:
        if needle in blob and our in our_blob:
            ok = True
            break
    if ok:
        covered.append((k, s))
    else:
        missing.append((k, s))

print(f"covered~{len(covered)} missing~{len(missing)} of {len(sources)}")
print("\nMISSING / WEAK vs our live+pipe:")
for k, s in missing:
    print(f"  - {k:28} source={s}")
