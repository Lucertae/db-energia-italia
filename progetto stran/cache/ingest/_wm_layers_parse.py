import re
import urllib.request
from pathlib import Path

UA = {"User-Agent": "ops-desk/1.0"}
url = "https://raw.githubusercontent.com/koala73/worldmonitor/main/src/config/map-layer-definitions.ts"
req = urllib.request.Request(url, headers=UA)
t = urllib.request.urlopen(req, timeout=60).read().decode("utf-8", "replace")
Path("cache/ingest/_wm_layers.ts").write_text(t, encoding="utf-8")

# Parse layer objects roughly: id + title/name + sourceUrl if any
blocks = re.findall(r"\{[^{}]{20,800}\}", t)
layers = []
for b in blocks:
    mid = re.search(r"\bid:\s*'([^']+)'", b)
    name = re.search(r"\b(?:name|title|label):\s*'([^']+)'", b)
    src = re.search(r"\b(?:url|endpoint|source|api):\s*'([^']+)'", b)
    if mid:
        layers.append(
            {
                "id": mid.group(1),
                "name": name.group(1) if name else "",
                "src": src.group(1) if src else "",
            }
        )

# dedupe by id keeping first
seen = set()
uniq = []
for L in layers:
    if L["id"] in seen:
        continue
    seen.add(L["id"])
    uniq.append(L)

print(f"parsed_layers={len(uniq)}")
for L in uniq:
    print(f"{L['id']:32} {L['name'][:40]:40} {L['src'][:60]}")

# Our live + harvest IDs for rough coverage notes
live = __import__("json").loads(Path("scripts/desk_harvest/live_streams.json").read_text(encoding="utf-8"))
our_ids = {s["id"] for s in live.get("streams", [])}
print("\nOUR_LIVE", len(our_ids))
for s in live.get("streams", []):
    print(" ", s["id"], "-", s.get("name"))
