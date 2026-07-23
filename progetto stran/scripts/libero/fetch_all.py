#!/usr/bin/env python3
"""
Libero ingest — paper-grade energy/crypto/systemic series.
Runs on ciccio10 (Tailscale); exports FRED-format CSV for OPS DESK cache/.
"""
from __future__ import annotations

import csv
import io
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

from libero_db import connect, upsert_series

ROOT = Path(__file__).resolve().parent
DESK = ROOT.parent.parent
DB_PATH = Path(os.environ.get("LIBERO_DB", ROOT / "libero.db"))
EXPORT_DIR = Path(os.environ.get("LIBERO_EXPORT", DESK / "cache"))

UA = "ops-desk-libero/1.0 (+research; ciccio)"


def http_get(url: str, compressed: bool = False, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    if compressed:
        req.add_header("Accept-Encoding", "gzip")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            import gzip
            data = gzip.decompress(data)
        return data


def ymd_from_date(s: str) -> int:
    s = s.strip()[:10]
    if "T" in s:
        s = s.split("T", 1)[0]
    parts = s.replace("/", "-").split("-")
    if len(parts) != 3:
        raise ValueError(s)
    y, m, d = int(parts[0]), int(parts[1]), int(parts[2])
    return y * 10000 + m * 100 + d


def rows_from_df(df: pd.DataFrame, date_col: str, val_col: str) -> list[tuple[int, float]]:
    out: list[tuple[int, float]] = []
    for _, r in df.iterrows():
        try:
            dt = pd.to_datetime(r[date_col])
            v = float(r[val_col])
        except (TypeError, ValueError):
            continue
        if v != v:  # NaN
            continue
        ymd = int(dt.year) * 10000 + int(dt.month) * 100 + int(dt.day)
        out.append((ymd, v))
    out.sort(key=lambda x: x[0])
    return out


def fetch_cbeci(conn) -> int:
    url = "https://ccaf.io/cbeci/api/v1.4.0/download/data?price=0.05"
    raw = http_get(url, compressed=True).decode("utf-8", errors="replace")
    lines = raw.splitlines()
    if not lines or "Timestamp" not in lines[1]:
        raise RuntimeError("CBECI parse fail")
    reader = csv.DictReader(lines[1:])
    rows_cbe: list[tuple[int, float]] = []
    rows_emi: list[tuple[int, float]] = []
    for row in reader:
        dt = row.get("Date and Time") or row.get("Date")
        if not dt:
            continue
        ymd = ymd_from_date(dt)
        try:
            gw = float(row["power GUESS, GW"])
            twh_ann = float(row["annualised consumption GUESS, TWh"])
        except (KeyError, ValueError):
            continue
        gwh_day = gw * 24.0
        rows_cbe.append((ymd, gwh_day))
        # Mt CO2 approx from Cambridge annualised TWh * 0.5 tCO2/MWh intensity proxy
        # (CBECI does not ship carbon; use documented grid mix ~0.5 from literature)
        mt_co2_day = twh_ann * 1e6 * 0.0005 / 365.0
        rows_emi.append((ymd, mt_co2_day))
    n = upsert_series(conn, "CBE", "CBECI power GWh/d", "ccaf.io", "GWh/d", rows_cbe)
    upsert_series(conn, "EMI", "BTC carbon est Mt/d", "ccaf.io+intensity", "MtCO2/d", rows_emi)
    return n


def fetch_blockchain_chart(conn, chart: str, sid: str, label: str, unit: str,
                           scale: float = 1.0) -> int:
    url = (
        f"https://api.blockchain.info/charts/{chart}"
        f"?timespan=all&format=json&sampled=true&metadata=false"
    )
    data = json.loads(http_get(url).decode("utf-8"))
    rows: list[tuple[int, float]] = []
    for pt in data.get("values", []):
        ts = int(pt["x"])
        val = float(pt["y"]) * scale
        t = time.gmtime(ts)
        ymd = (t.tm_year * 10000 + t.tm_mon * 100 + t.tm_mday)
        rows.append((ymd, val))
    return upsert_series(conn, sid, label, "blockchain.info", unit, rows)


def fetch_coingecko_btc(conn) -> int:
    rows_vol: list[tuple[int, float]] = []
    rows_cap: list[tuple[int, float]] = []
    rows_px: list[tuple[int, float]] = []
    days = 365
    url = (
        "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
        f"?vs_currency=usd&days={days}&interval=daily"
    )
    data = json.loads(http_get(url).decode("utf-8"))
    for ts_ms, vol in data.get("total_volumes", []):
        t = time.gmtime(int(ts_ms) / 1000)
        ymd = t.tm_year * 10000 + t.tm_mon * 100 + t.tm_mday
        rows_vol.append((ymd, float(vol)))
    for ts_ms, cap in data.get("market_caps", []):
        t = time.gmtime(int(ts_ms) / 1000)
        ymd = t.tm_year * 10000 + t.tm_mon * 100 + t.tm_mday
        rows_cap.append((ymd, float(cap)))
    for ts_ms, px in data.get("prices", []):
        t = time.gmtime(int(ts_ms) / 1000)
        ymd = t.tm_year * 10000 + t.tm_mon * 100 + t.tm_mday
        rows_px.append((ymd, float(px)))
    upsert_series(conn, "BVL", "BTC vol USD", "coingecko", "USD", rows_vol)
    upsert_series(conn, "MCP", "BTC mcap USD", "coingecko", "USD", rows_cap)
    # BTC price for CVI proxy
    crypto_dir = EXPORT_DIR / "crypto"
    crypto_dir.mkdir(parents=True, exist_ok=True)
    btc_path = crypto_dir / "BTC.csv"
    with btc_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["DATE", "VALUE"])
        for ymd, val in sorted(rows_px):
            y, m, d = ymd // 10000, (ymd // 100) % 100, ymd % 100
            w.writerow([f"{y:04d}-{m:02d}-{d:02d}", f"{val:.8g}"])
    return len(rows_cap)


def fetch_yahoo_chart(conn, symbol: str, sid: str, label: str) -> int:
    """Yahoo finance chart API (no yfinance dependency)."""
    enc = urllib.parse.quote(symbol, safe="")
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{enc}"
        f"?interval=1d&range=5y"
    )
    data = json.loads(http_get(url).decode("utf-8"))
    result = data.get("chart", {}).get("result")
    if not result:
        raise RuntimeError(f"yahoo empty {symbol}")
    r0 = result[0]
    ts = r0.get("timestamp") or []
    closes = (r0.get("indicators") or {}).get("quote", [{}])[0].get("close") or []
    rows: list[tuple[int, float]] = []
    for t, c in zip(ts, closes):
        if t is None or c is None:
            continue
        gm = time.gmtime(int(t))
        ymd = gm.tm_year * 10000 + gm.tm_mon * 100 + gm.tm_mday
        rows.append((ymd, float(c)))
    return upsert_series(conn, sid, label, f"yahoo:{symbol}", "USD", rows)


def fetch_yfinance(conn, symbol: str, sid: str, label: str) -> int:
    try:
        import yfinance as yf
        t = yf.Ticker(symbol)
        hist = t.history(period="5y", auto_adjust=True)
        if hist.empty:
            raise RuntimeError(f"yfinance empty {symbol}")
        rows: list[tuple[int, float]] = []
        for idx, row in hist.iterrows():
            ymd = idx.year * 10000 + idx.month * 100 + idx.day
            rows.append((ymd, float(row["Close"])))
        return upsert_series(conn, sid, label, f"yfinance:{symbol}", "USD", rows)
    except Exception:
        return fetch_yahoo_chart(conn, symbol, sid, label)


def fetch_gpr_daily(conn) -> int:
    url = "https://www.matteoiacoviello.com/gpr_files/data_gpr_daily_recent.xls"
    raw = http_get(url)
    df = pd.read_excel(io.BytesIO(raw), engine="xlrd")
    rows: list[tuple[int, float]] = []
    for _, r in df.iterrows():
        try:
            day = int(r["DAY"])
            val = float(r["GPRD"])
        except (KeyError, TypeError, ValueError):
            continue
        if day < 19000000 or val != val:
            continue
        rows.append((day, val))
    rows.sort(key=lambda x: x[0])
    return upsert_series(conn, "GPR", "Geopolitical risk", "iacoviello", "index", rows)


def fetch_cpu_monthly(conn) -> int:
    url = "https://www.policyuncertainty.com/media/cpu_base_pos_neg_all_countries_monthly.csv"
    raw = http_get(url).decode("utf-8", errors="replace")
    lines = raw.splitlines()
    # skip citation line
    while lines and not lines[0].startswith("cit,"):
        lines.pop(0)
    reader = csv.DictReader(lines)
    rows: list[tuple[int, float]] = []
    for row in reader:
        try:
            y = int(float(row["year"]))
            m = int(float(row["month"]))
            v = float(row["CPU_US"])
        except (KeyError, ValueError, TypeError):
            continue
        # use month-end ymd
        ymd = y * 10000 + m * 100 + 28
        rows.append((ymd, v))
    return upsert_series(conn, "CPU", "Climate policy unc US", "policyuncertainty", "index", rows)


def fetch_cvi_from_btc_cache(conn) -> int:
    """CVI proxy: 30d annualized realized vol of BTC log returns (%)."""
    btc_path = EXPORT_DIR / "crypto" / "BTC.csv"
    if not btc_path.is_file():
        btc_path = EXPORT_DIR / "BTC.csv"
    if not btc_path.is_file():
        print("SKIP CVI: no BTC.csv", file=sys.stderr)
        return 0
    df = pd.read_csv(btc_path)
    df["DATE"] = pd.to_datetime(df["DATE"])
    df = df.sort_values("DATE")
    df["logp"] = df["VALUE"].astype(float).apply(lambda x: math.log(x) if x > 0 else float("nan"))
    df["ret"] = df["logp"].diff()
    df["cvi"] = df["ret"].rolling(30).std() * (365 ** 0.5) * 100.0
    rows = rows_from_df(df.dropna(subset=["cvi"]), "DATE", "cvi")
    return upsert_series(conn, "CVI", "Crypto vol index proxy", "desk:BTC rv30", "%", rows)


def export_fred_csv(conn, sid: str, out_dir: Path) -> bool:
    cur = conn.execute(
        "SELECT ymd, val FROM series_daily WHERE id=? ORDER BY ymd", (sid,)
    )
    rows = cur.fetchall()
    if len(rows) < 10:
        return False
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"{sid}.csv"
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["DATE", "VALUE"])
        for ymd, val in rows:
            y, m, d = ymd // 10000, (ymd // 100) % 100, ymd % 100
            w.writerow([f"{y:04d}-{m:02d}-{d:02d}", f"{val:.8g}"])
    return True


DESK_SERIES = [
    "CBE", "EMI", "CVI", "FEE", "DIF", "REV", "HAS", "BVL", "MCP",
    "GPR", "CPU", "EUA", "GRN", "DIR", "NGF",
]


def run_fetch() -> None:
    conn = connect(DB_PATH)
    ok, fail = 0, 0
    jobs = [
        ("coingecko", lambda: fetch_coingecko_btc(conn)),
        ("CBECI", lambda: fetch_cbeci(conn)),
        ("fees", lambda: fetch_blockchain_chart(conn, "transaction-fees", "FEE",
                                                "BTC tx fees USD", "USD")),
        ("difficulty", lambda: fetch_blockchain_chart(conn, "difficulty", "DIF",
                                                      "BTC difficulty", "index")),
        ("hash-rate", lambda: fetch_blockchain_chart(conn, "hash-rate", "HAS",
                                                     "Hashrate EH/s", "EH/s")),
        ("miners-revenue", lambda: fetch_blockchain_chart(conn, "miners-revenue", "REV",
                                                          "Miner revenue USD", "USD")),
        ("gpr", lambda: fetch_gpr_daily(conn)),
        ("cpu", lambda: fetch_cpu_monthly(conn)),
        ("ICLN", lambda: fetch_yfinance(conn, "ICLN", "GRN", "Clean energy ICLN")),
        ("XLE", lambda: fetch_yfinance(conn, "XLE", "DIR", "Dirty energy XLE")),
        ("KRBN", lambda: fetch_yfinance(conn, "KRBN", "EUA", "Carbon EUA proxy KRBN")),
        ("NG=F", lambda: fetch_yfinance(conn, "NG=F", "NGF", "Nat gas futures")),
    ]
    for name, fn in jobs:
        try:
            n = fn()
            print(f"OK {name} {n} rows")
            ok += 1
        except Exception as e:
            print(f"FAIL {name}: {e}", file=sys.stderr)
            fail += 1
    try:
        n = fetch_cvi_from_btc_cache(conn)
        print(f"OK CVI {n} rows")
        ok += 1
    except Exception as e:
        print(f"FAIL CVI: {e}", file=sys.stderr)
        fail += 1
    conn.close()
    print(f"fetch done ok={ok} fail={fail}")


def run_export() -> None:
    conn = connect(DB_PATH)
    n = 0
    for sid in DESK_SERIES:
        if export_fred_csv(conn, sid, EXPORT_DIR):
            print(f"export {sid}.csv")
            n += 1
    conn.close()
    print(f"exported {n} series -> {EXPORT_DIR}")


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: fetch_all.py [fetch|export|all]", file=sys.stderr)
        return 2
    cmd = sys.argv[1]
    if cmd in ("fetch", "all"):
        run_fetch()
    if cmd in ("export", "all"):
        run_export()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
