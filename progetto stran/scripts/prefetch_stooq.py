#!/usr/bin/env python3
"""Download Stooq daily OHLCV history for company catalog into cache/stooq/."""
import csv
import os
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE = os.path.join(ROOT, "cache", "stooq")

SYMS = [
    "xom.us", "cvx.us", "shel.uk", "bp.uk", "tte.fr", "eqnr.us", "eni.it", "rep.mc",
    "2222.sa", "pbr.us", "ptr.us", "snpm.us", "cop.us", "eog.us", "oxy.us", "slb.us",
    "hal.us", "lng.us", "vlo.us", "mpc.us", "enel.it", "ng.uk", "eon.de", "rwe.de",
    "ibe.mc", "nee.us", "duk.us", "engi.pa", "snam.it", "ig.it", "wmb.us", "kmi.us",
    "oke.us", "edp.pt", "orsted.co",
]


def fetch_hist(sym: str):
  safe = sym.replace(".", "_")
  url = f"https://stooq.com/q/d/l/?s={sym}&i=d"
  req = urllib.request.Request(url, headers={"User-Agent": "ops-desk/1.0"})
  with urllib.request.urlopen(req, timeout=60) as resp:
      text = resp.read().decode("utf-8", errors="replace")
  rows = []
  for line in text.splitlines():
      if not line or line.startswith("Date,"):
          continue
      cols = line.split(",")
      if len(cols) < 5:
          continue
      try:
          close = float(cols[4])
      except ValueError:
          continue
      if close > 0:
          rows.append((cols[0], close))
  return rows


def write_fred(path: str, rows):
  with open(path, "w", encoding="utf-8", newline="") as f:
      w = csv.writer(f)
      w.writerow(["DATE", "CLOSE"])
      for d, c in rows[-1900:]:
          w.writerow([d, f"{c:.4f}"])


def main():
  os.makedirs(CACHE, exist_ok=True)
  ok = fail = 0
  for sym in SYMS:
      out = os.path.join(CACHE, f"{sym.replace('.', '_')}.csv")
      try:
          rows = fetch_hist(sym)
          if len(rows) < 20:
              print(f"FAIL {sym} ({len(rows)} rows)")
              fail += 1
              continue
          write_fred(out, rows)
          print(f"OK {sym} {len(rows)}d")
          ok += 1
      except Exception as e:
          print(f"FAIL {sym}: {e}")
          fail += 1
      time.sleep(0.4)
    print("Stooq bulk hist blocked (JS verify). Prices accumulate daily in cache/stooq/ on live refresh.")
  return 0 if ok > 0 else 1


if __name__ == "__main__":
  raise SystemExit(main())
