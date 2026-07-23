#!/usr/bin/env python3
"""Harvest near-live Italy economic price feeds into mercati-italia/sources/prezzi_live/."""
from __future__ import annotations

import argparse
import json
import re
import shutil
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parents[1]
OUT = DB / "mercati-italia" / "sources" / "prezzi_live"
ENTSOE_KEY = DB / "entsoe-italia" / "entsoe.key"
UA = {"User-Agent": "prezzi-live-italia/1.0"}

ZONES = {
    "IT-North": "10Y1001A1001A73I",
    "IT-Centre-North": "10Y1001A1001A70O",
    "IT-Centre-South": "10Y1001A1001A71M",
    "IT-South": "10Y1001A1001A788",
    "IT-Sicily": "10Y1001A1001A74G",
    "IT-Sardinia": "10Y1001A1001A75E",
    "IT-Calabria": "10Y1001C--00096J",
}

MANIFEST: list[dict] = []
SNAPSHOT: dict = {"updated_at": None, "feeds": {}}


def log(msg: str) -> None:
    print(msg, flush=True)


def mark(feed: str, status: str, **extra) -> None:
    row = {"feed": feed, "status": status, **extra}
    MANIFEST.append(row)
    if status.startswith("ok"):
        SNAPSHOT["feeds"][feed] = {k: v for k, v in extra.items() if k in ("path", "rows", "latest", "note")}


def download(url: str, dest: Path, *, min_size: int = 200, force: bool = False, timeout: int = 180) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= min_size and not force:
        log(f"  skip {dest.name}")
        return True
    log(f"  GET {url[:140]}")
    req = urllib.request.Request(url, headers=UA)
    tmp = dest.with_suffix(dest.suffix + ".part")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp, open(tmp, "wb") as f:
            shutil.copyfileobj(resp, f)
        head = tmp.read_bytes()[:40].lower()
        if head.startswith(b"<!doctype") or head.startswith(b"<html"):
            tmp.unlink(missing_ok=True)
            log(f"  FAIL HTML {dest.name}")
            return False
        if tmp.stat().st_size < min_size:
            tmp.unlink(missing_ok=True)
            log(f"  FAIL small {dest.name}")
            return False
        tmp.replace(dest)
        log(f"  -> {dest.name} ({dest.stat().st_size/1e6:.2f} MB)")
        return True
    except Exception as e:
        tmp.unlink(missing_ok=True)
        log(f"  FAIL {dest.name}: {e}")
        return False


def harvest_ember(force: bool = False) -> None:
    log("== Ember Italy wholesale daily ==")
    out = OUT / "electricity"
    out.mkdir(parents=True, exist_ok=True)
    raw = out / "ember_european_wholesale_daily.csv"
    url = "https://files.ember-energy.org/public-downloads/european_wholesale_electricity_price_data_daily.csv"
    if not download(url, raw, min_size=1000, force=force, timeout=300):
        mark("ember_daily", "fail")
        return
    try:
        df = pd.read_csv(raw)
        # Ember columns vary: Country / ISO3_code / Date / Price
        cols = {c.lower(): c for c in df.columns}
        country_col = cols.get("country") or cols.get("country_name") or cols.get("area")
        date_col = cols.get("date") or cols.get("datetime")
        price_col = None
        for k, v in cols.items():
            if "price" in k:
                price_col = v
                break
        if not country_col or not date_col or not price_col:
            mark("ember_daily", "fail", note=f"unexpected cols={list(df.columns)}")
            return
        it = df[df[country_col].astype(str).str.contains("Italy|Italia|IT", case=False, na=False)].copy()
        dest = out / "ember_italy_wholesale_daily.csv"
        it.to_csv(dest, index=False)
        latest = str(it[date_col].max()) if len(it) else None
        mark("ember_daily", "ok", path=str(dest.relative_to(DB)), rows=len(it), latest=latest)
        log(f"  IT rows={len(it)} latest={latest}")
    except Exception as e:
        mark("ember_daily", f"fail:{e}")


def harvest_arera(force: bool = False) -> None:
    log("== ARERA Portale Offerte indices ==")
    out = OUT / "gas_indices"
    out.mkdir(parents=True, exist_ok=True)
    url = (
        "https://www.ilportaleofferte.it/portaleOfferte/resources/cms/documents/"
        "5d6f1085b4d5f20821af55764e647671.csv"
    )
    dest = out / "arera_indici_storici.csv"
    if not download(url, dest, min_size=500, force=force):
        mark("arera_indici", "fail")
        return
    try:
        df = None
        for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
            try:
                df = pd.read_csv(dest, sep=None, engine="python", encoding=enc)
                break
            except Exception:
                continue
        if df is None:
            # keep binary copy even if unreadable as table
            mark("arera_indici", "ok", path=str(dest.relative_to(DB)), note="saved raw; parse failed")
            return
        latest = None
        for c in df.columns:
            if re.search(r"data|date|periodo|mese", str(c), re.I):
                latest = str(df[c].dropna().astype(str).iloc[-1]) if len(df) else None
                break
        latest_path = out / "arera_indici_latest.csv"
        shutil.copy2(dest, latest_path)
        mark("arera_indici", "ok", path=str(latest_path.relative_to(DB)), rows=len(df), latest=latest)
    except Exception as e:
        mark("arera_indici", f"fail:{e}")


def harvest_sisen(force: bool = False) -> None:
    log("== SISEN fuel prices ==")
    out = OUT / "fuels"
    out.mkdir(parents=True, exist_ok=True)
    feeds = [
        ("sisen_weekly_prices_all.csv", "https://sisen.mase.gov.it/dgsaie/api/v1/weekly-prices/report/export?type=ALL&format=CSV&lang=it"),
        ("sisen_monthly_prices_all.csv", "https://sisen.mase.gov.it/dgsaie/api/v1/monthly-prices/export?format=CSV&lang=it"),
    ]
    for name, url in feeds:
        dest = out / name
        ok = download(url, dest, min_size=100, force=force)
        if not ok:
            mark(name, "fail")
            continue
        try:
            df = pd.read_csv(dest, sep=";", encoding="utf-8", engine="python")
            if df.shape[1] == 1:
                df = pd.read_csv(dest, sep=",", encoding="utf-8", engine="python")
            mark(name, "ok", path=str(dest.relative_to(DB)), rows=len(df), latest=str(df.iloc[-1, 0]) if len(df) else None)
        except Exception as e:
            mark(name, "ok", path=str(dest.relative_to(DB)), note=f"saved but parse warn:{e}")


def harvest_eua(force: bool = False) -> None:
    log("== EEX EUA auction (current year) ==")
    out = OUT / "carbon"
    out.mkdir(parents=True, exist_ok=True)
    y = date.today().year
    base = "https://public.eex-group.com/eex/eua-auction-report/"
    ok_any = False
    for ext in ("xlsx", "xls"):
        name = f"emission-spot-primary-market-auction-report-{y}-data.{ext}"
        dest = out / name
        if download(base + name, dest, min_size=3000, force=force):
            # also keep under ets_eua archive
            archive = DB / "mercati-italia" / "sources" / "ets_eua" / name
            archive.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, archive)
            stable = out / f"eex_eua_auction_latest.{ext}"
            shutil.copy2(dest, stable)
            mark("eex_eua_auction", "ok", path=str(stable.relative_to(DB)), latest=str(y))
            ok_any = True
            break
    if not ok_any:
        mark("eex_eua_auction", "fail")


def harvest_entsoe_day_ahead(days: int = 90, force: bool = False) -> None:
    log(f"== ENTSO-E day-ahead IT zones (last {days}d) ==")
    out = OUT / "electricity"
    out.mkdir(parents=True, exist_ok=True)
    dest = out / "entsoe_day_ahead_it_zones_rolling.csv"
    if dest.exists() and dest.stat().st_size > 50_000 and not force:
        # refresh if older than 12h
        age_h = (time.time() - dest.stat().st_mtime) / 3600
        if age_h < 12:
            log(f"  skip fresh ({age_h:.1f}h)")
            try:
                df = pd.read_csv(dest)
                mark("entsoe_day_ahead", "ok", path=str(dest.relative_to(DB)), rows=len(df), latest=str(df["datetime"].max()) if "datetime" in df.columns else None)
            except Exception:
                mark("entsoe_day_ahead", "ok", path=str(dest.relative_to(DB)))
            return

    if not ENTSOE_KEY.exists():
        mark("entsoe_day_ahead", "fail", note="missing entsoe.key")
        log("  FAIL missing entsoe.key")
        return
    try:
        from entsoe import EntsoePandasClient
        from entsoe.exceptions import NoMatchingDataError
    except ImportError as e:
        mark("entsoe_day_ahead", f"fail:{e}")
        return

    key = ENTSOE_KEY.read_text(encoding="utf-8").strip().splitlines()[0].strip()
    client = EntsoePandasClient(api_key=key)
    end = pd.Timestamp(datetime.now(tz=timezone.utc)).tz_convert("Europe/Rome") + pd.Timedelta(days=1)
    start = end - pd.Timedelta(days=days)
    frames: list[pd.DataFrame] = []
    for zone, eic in ZONES.items():
        try:
            s = client.query_day_ahead_prices(eic, start=start, end=end)
            if s is None or (hasattr(s, "empty") and s.empty):
                log(f"  empty {zone}")
                time.sleep(1.0)
                continue
            if isinstance(s, pd.Series):
                df = s.rename("price_eur_mwh").reset_index()
                df.columns = ["datetime", "price_eur_mwh"]
            else:
                df = s.reset_index()
                df.columns = ["datetime", "price_eur_mwh"] + list(df.columns[2:])
            df.insert(0, "zone", zone)
            df.insert(1, "eic", eic)
            frames.append(df)
            log(f"  {zone}: {len(df)} rows")
        except NoMatchingDataError:
            log(f"  no data {zone}")
        except Exception as e:
            log(f"  FAIL {zone}: {e}")
        time.sleep(1.2)

    if not frames:
        mark("entsoe_day_ahead", "fail", note="no zone data")
        return
    all_df = pd.concat(frames, ignore_index=True)
    all_df.to_csv(dest, index=False)
    mark(
        "entsoe_day_ahead",
        "ok",
        path=str(dest.relative_to(DB)),
        rows=len(all_df),
        latest=str(all_df["datetime"].max()),
    )


def write_docs() -> None:
    (OUT / "README.txt").write_text(
        "Prezzi live / near-real-time Italia\n"
        "Refresh: python db/scripts/harvest_prezzi_live.py\n"
        "Feeds: ENTSO-E DA zones, Ember IT daily, ARERA indices, SISEN fuels, EEX EUA.\n"
        "Non inclusi: GME MI/MSD/MB, Anno2007 (manuali).\n",
        encoding="utf-8",
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--electricity-only", action="store_true")
    ap.add_argument("--days", type=int, default=90)
    args = ap.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    SNAPSHOT["updated_at"] = datetime.now(timezone.utc).isoformat()

    harvest_entsoe_day_ahead(days=args.days, force=args.force)
    harvest_ember(force=args.force)
    if not args.electricity_only:
        harvest_arera(force=args.force)
        harvest_sisen(force=args.force)
        harvest_eua(force=args.force)

    write_docs()
    (OUT / "manifest.json").write_text(json.dumps(MANIFEST, indent=2), encoding="utf-8")
    (OUT / "snapshot.json").write_text(json.dumps(SNAPSHOT, indent=2), encoding="utf-8")
    ok = sum(1 for m in MANIFEST if str(m.get("status", "")).startswith("ok"))
    log(f"DONE feeds_ok={ok}/{len(MANIFEST)} -> {OUT}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
