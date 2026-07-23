from pathlib import Path
import re

t = Path("cache/ingest/_wm_layers.ts").read_text(encoding="utf-8")
print("len", len(t))
print(t[:2000])
print("---IDS---")
ids = re.findall(r"\bid:\s*'([^']+)'", t)
print("count", len(ids))
for i in ids:
    print(i)
