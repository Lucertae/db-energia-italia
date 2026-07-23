#!/usr/bin/env python3
"""Equity OHLCV via Yahoo chart API -> cache/stooq/{symbol}.csv (FRED format)."""
from __future__ import annotations

import csv
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from series_config import YAHOO_EQUITIES

UA = "ops-desk-harvest/1.0"
HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("DESK_ROOT", HERE.parents[1]))
CACHE = Path(os.environ.get("DESK_CACHE", ROOT / "cache"))
STOOQ_DIR = CACHE / "stooq"

YAHOO_MAP = {
    "xom.us": "XOM",
    "cvx.us": "CVX",
    "shel.uk": "SHEL.L",
    "bp.uk": "BP.L",
    "tte.fr": "TTE.PA",
    "eqnr.us": "EQNR",
    "eni.it": "ENI.MI",
    "rep.mc": "REP.MC",
    "cop.us": "COP",
    "eog.us": "EOG",
    "oxy.us": "OXY",
    "slb.us": "SLB",
    "hal.us": "HAL",
    "lng.us": "LNG",
    "vlo.us": "VLO",
    "mpc.us": "MPC",
    "enel.it": "ENEL.MI",
    "ng.uk": "NG.L",
    "eon.de": "EON.DE",
    "rwe.de": "RWE.DE",
    "ibe.mc": "IBE.MC",
    "nee.us": "NEE",
    "duk.us": "DUK",
    "engi.pa": "ENGI.PA",
    "snam.it": "SRG.MI",
    "ig.it": "IG.MI",
    "wmb.us": "WMB",
    "kmi.us": "KMI",
    "oke.us": "OKE",
    "edp.pt": "EDP.LS",
    "orsted.co": "ORSTED.CO",
}


def fetch_yahoo(symbol: str) -> list[tuple[str, float]]:
    enc = urllib.parse.quote(symbol, safe="")
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}?interval=1d&range=5y"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as resp:
        data = json.load(resp)
    result = data.get("chart", {}).get("result")
    if not result:
        raise RuntimeError("empty chart")
    r0 = result[0]
    ts = r0.get("timestamp") or []
    closes = (r0.get("indicators") or {}).get("quote", [{}])[0].get("close") or []
    rows: list[tuple[str, float]] = []
    for t, c in zip(ts, closes):
        if t is None or c is None:
            continue
        gm = time.gmtime(int(t))
        ymd = f"{gm.tm_year:04d}-{gm.tm_mon:02d}-{gm.tm_mday:02d}"
        rows.append((ymd, float(c)))
    return rows


def main() -> int:
    STOOQ_DIR.mkdir(parents=True, exist_ok=True)
    ok = fail = 0
    for stooq_sym, _label in YAHOO_EQUITIES:
        ysym = YAHOO_MAP.get(stooq_sym)
        if not ysym:
            print(f"SKIP {stooq_sym}: no yahoo map", file=sys.stderr)
            fail += 1
            continue
        safe = stooq_sym.replace(".", "_")
        out = STOOQ_DIR / f"{safe}.csv"
        try:
            rows = fetch_yahoo(ysym)
            if len(rows) < 20:
                print(f"FAIL {stooq_sym}: {len(rows)} rows", file=sys.stderr)
                fail += 1
                continue
            with out.open("w", encoding="utf-8", newline="") as f:
                w = csv.writer(f)
                w.writerow(["DATE", "CLOSE"])
                for ymd, close in rows[-1900:]:
                    w.writerow([ymd, f"{close:.4f}"])
            print(f"OK {stooq_sym} {len(rows)}d")
            ok += 1
        except Exception as e:
            print(f"FAIL {stooq_sym}: {e}", file=sys.stderr)
            fail += 1
        time.sleep(0.35)
    print(f"equities ok={ok} fail={fail}")
    return 0 if ok > 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
