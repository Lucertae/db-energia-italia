#!/usr/bin/env python3
"""Harvest GIE AGSI (storage) + ALSI (LNG) for Italy."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parents[1]
ROOT = DB / "mercati-italia"
KEY_FILE = ROOT / "gie.key"
AGSI_OUT = ROOT / "sources" / "agsi"
ALSI_OUT = ROOT / "sources" / "alsi"
UA = {"User-Agent": "Mozilla/5.0 (compatible; mercati-italia-agsi/1.0)"}


def log(msg: str) -> None:
    print(msg, flush=True)


def load_key() -> str:
    if not KEY_FILE.exists():
        raise SystemExit(f"Missing {KEY_FILE} — put GIE API key there (one line).")
    return KEY_FILE.read_text(encoding="utf-8").strip()


def sanitize(msg: str, key: str) -> str:
    return msg.replace(key, "***") if key else msg


def api_get(base: str, key: str, params: dict | None = None) -> dict | list:
    q = urllib.parse.urlencode(params or {})
    url = f"{base}?{q}" if q else base
    req = urllib.request.Request(
        url,
        headers={**UA, "x-key": key, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_get_all_pages(base: str, key: str, params: dict) -> list[dict]:
    """Fetch all pages for a date range query (size default 300 = API max)."""
    rows: list[dict] = []
    page = 1
    last_page = 1
    base_params = {"size": 300, **params}
    while page <= last_page:
        payload = api_get(base, key, {**base_params, "page": page})
        if not isinstance(payload, dict):
            break
        if payload.get("error"):
            raise RuntimeError(sanitize(json.dumps(payload)[:400], key))
        last_page = int(payload.get("last_page") or 1)
        chunk = payload.get("data") or []
        if isinstance(chunk, list):
            rows.extend(chunk)
        if page >= last_page:
            break
        page += 1
        time.sleep(0.25)
    return rows


def flatten_rows(payload: dict) -> list[dict]:
    data = payload.get("data")
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        rows = []
        for k, v in data.items():
            if isinstance(v, list):
                for item in v:
                    if isinstance(item, dict):
                        rows.append({"_group": k, **item})
            elif isinstance(v, dict):
                rows.append({"_group": k, **v})
        return rows
    return []


def harvest_series(base: str, key: str, out_dir: Path, label: str, country: str = "IT") -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    start_year = 2015
    end_year = date.today().year
    all_frames: list[pd.DataFrame] = []
    for year in range(start_year, end_year + 1):
        csv_dest = out_dir / f"{label}_{country.lower()}_{year}.csv"
        json_dest = out_dir / f"{label}_{country.lower()}_{year}.json"
        if csv_dest.exists() and csv_dest.stat().st_size > 5_000:
            try:
                existing = pd.read_csv(csv_dest)
                days = (
                    existing["gasDayStart"].nunique()
                    if "gasDayStart" in existing.columns
                    else len(existing)
                )
                need = 300 if year < end_year else 30
                if days >= need:
                    log(f"  skip {csv_dest.name} days={days}")
                    all_frames.append(existing)
                    continue
                log(f"  refetch incomplete {csv_dest.name} days={days}")
            except Exception:
                log(f"  refetch unreadable {csv_dest.name}")
            csv_dest.unlink(missing_ok=True)
            json_dest.unlink(missing_ok=True)
        d_from = f"{year}-01-01"
        d_to = f"{year}-12-31" if year < end_year else date.today().isoformat()
        try:
            rows = api_get_all_pages(
                base,
                key,
                {"country": country, "from": d_from, "to": d_to},
            )
        except Exception as e:
            log(f"  FAIL {label} {year}: {e}")
            continue
        json_dest.write_text(json.dumps({"year": year, "rows": len(rows), "data": rows}, ensure_ascii=False), encoding="utf-8")
        if not rows:
            log(f"  {label} {year}: empty")
            continue
        df = pd.json_normalize(rows)
        df.to_csv(csv_dest, index=False)
        all_frames.append(df)
        dates = sorted(df["gasDayStart"].dropna().unique()) if "gasDayStart" in df.columns else []
        log(f"  {label} {year}: rows={len(df)} days={len(dates)} {dates[0] if dates else ''}..{dates[-1] if dates else ''}")
        time.sleep(0.3)

    if all_frames:
        merged = out_dir / f"{label}_{country.lower()}_all.csv"
        all_df = pd.concat(all_frames, ignore_index=True)
        if "gasDayStart" in all_df.columns:
            all_df = all_df.drop_duplicates(subset=["gasDayStart", "code"], keep="last")
            all_df = all_df.sort_values("gasDayStart")
        all_df.to_csv(merged, index=False)
        log(f"  merged {merged.name} rows={len(all_df)}")


def extract_italy_entities(about: dict | None, roots: tuple[str, ...] = ("SSO", "LSO", "Non-SSO")) -> list[dict]:
    """Build company/facility jobs for Italy from /api/about (needs country+company[+facility])."""
    jobs: list[dict] = []
    if not isinstance(about, dict):
        return jobs
    italy = None
    for root in roots:
        try:
            italy = about.get(root, {}).get("Europe", {}).get("Italy")
        except Exception:
            italy = None
        if isinstance(italy, list):
            break
    if not isinstance(italy, list):
        return jobs
    for op in italy:
        if not isinstance(op, dict) or not op.get("eic"):
            continue
        company = str(op["eic"])
        cname = str(op.get("name") or "")
        jobs.append(
            {
                "kind": "company",
                "country": "IT",
                "company": company,
                "facility": None,
                "name": cname,
            }
        )
        for fac in op.get("facilities") or []:
            if not isinstance(fac, dict) or not fac.get("eic"):
                continue
            jobs.append(
                {
                    "kind": "facility",
                    "country": "IT",
                    "company": company,
                    "facility": str(fac["eic"]),
                    "name": str(fac.get("name") or ""),
                }
            )
    return jobs


def harvest_entities(base: str, key: str, out_dir: Path, label: str) -> None:
    """Historical series per company/facility using GIE docs: country+company[+facility], size<=300."""
    about_path = out_dir / f"{label}_about.json"
    about: dict | None = None
    try:
        about = api_get(f"{base.rstrip('/').rsplit('/api', 1)[0]}/api/about", key)  # type: ignore[assignment]
        if isinstance(about, dict):
            about_path.write_text(json.dumps(about, ensure_ascii=False), encoding="utf-8")
            log(f"  wrote {about_path.name}")
    except Exception as e:
        log(f"  about: {sanitize(str(e), key)}")
        if about_path.exists():
            about = json.loads(about_path.read_text(encoding="utf-8"))

    jobs = extract_italy_entities(about if isinstance(about, dict) else None)
    log(f"  entity jobs IT: {len(jobs)}")
    if not jobs:
        return

    ent_dir = out_dir / "entities"
    ent_dir.mkdir(parents=True, exist_ok=True)
    (ent_dir / "italy_eic_jobs.json").write_text(json.dumps(jobs, indent=2, ensure_ascii=False), encoding="utf-8")

    end_year = date.today().year
    for job in jobs:
        kind = job["kind"]
        company = job["company"]
        facility = job.get("facility")
        name = job["name"]
        tag = facility or company
        safe = str(tag).replace("/", "_")
        csv_dest = ent_dir / f"{kind}_{safe}_2015_2026.csv"
        if csv_dest.exists() and csv_dest.stat().st_size > 30_000:
            try:
                ex = pd.read_csv(csv_dest)
                if "gasDayStart" in ex.columns and ex["gasDayStart"].nunique() >= 1000:
                    log(f"  skip {kind} {tag}")
                    continue
            except Exception:
                pass

        frames: list[pd.DataFrame] = []
        for year in range(2015, end_year + 1):
            d_from = f"{year}-01-01"
            d_to = f"{year}-12-31" if year < end_year else date.today().isoformat()
            params: dict = {
                "country": "IT",
                "company": company,
                "from": d_from,
                "to": d_to,
                "size": 300,
            }
            if facility:
                params["facility"] = facility
            try:
                rows = api_get_all_pages(base, key, params)
            except Exception as e:
                log(f"  FAIL {kind} {tag} {year}: {sanitize(str(e), key)}")
                time.sleep(1.0)
                continue
            if not rows:
                continue
            df = pd.json_normalize(rows)
            df.insert(0, "entity_kind", kind)
            df.insert(1, "company_eic", company)
            df.insert(2, "facility_eic", facility or "")
            df.insert(3, "entity_name", name)
            frames.append(df)
            time.sleep(0.25)

        if not frames:
            log(f"  empty {kind} {tag} ({name[:50]})")
            continue
        all_df = pd.concat(frames, ignore_index=True)
        if "gasDayStart" in all_df.columns:
            all_df = all_df.drop_duplicates(subset=["gasDayStart"], keep="last").sort_values("gasDayStart")
        all_df.to_csv(csv_dest, index=False)
        days = all_df["gasDayStart"].nunique() if "gasDayStart" in all_df.columns else len(all_df)
        log(f"  {kind} {tag}: rows={len(all_df)} days={days}")

    # merge all entity CSVs
    parts = sorted(ent_dir.glob("*_2015_2026.csv"))
    if parts:
        merged = pd.concat([pd.read_csv(p) for p in parts], ignore_index=True)
        merged.to_csv(ent_dir / f"{label}_it_entities_all.csv", index=False)
        log(f"  merged entities {len(merged)} rows from {len(parts)} files")


def harvest_facilities(base: str, key: str, out_dir: Path, label: str, country: str = "IT") -> None:
    # backward-compatible name used by main()
    harvest_entities(base, key, out_dir, label)


def main() -> int:
    key = load_key()
    log(f"GIE key loaded from {KEY_FILE}")

    # smoke test
    try:
        probe = api_get("https://agsi.gie.eu/api", key, {"country": "IT"})
        err = probe.get("error") if isinstance(probe, dict) else None
        if err:
            raise RuntimeError(json.dumps(probe)[:400])
        AGSI_OUT.mkdir(parents=True, exist_ok=True)
        (AGSI_OUT / "italy_agsi_latest.json").write_text(
            json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        log(f"  AGSI smoke OK total={probe.get('total') if isinstance(probe, dict) else '?'}")
    except Exception as e:
        log(f"AGSI smoke FAIL: {e}")
        return 1

    log("== AGSI Italy historical ==")
    harvest_series("https://agsi.gie.eu/api", key, AGSI_OUT, "agsi")
    harvest_facilities("https://agsi.gie.eu/api", key, AGSI_OUT, "agsi")

    log("== ALSI Italy historical ==")
    try:
        probe = api_get("https://alsi.gie.eu/api", key, {"country": "IT"})
        err = probe.get("error") if isinstance(probe, dict) else None
        if err:
            raise RuntimeError(json.dumps(probe)[:400])
        ALSI_OUT.mkdir(parents=True, exist_ok=True)
        (ALSI_OUT / "italy_alsi_latest.json").write_text(
            json.dumps(probe, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        log(f"  ALSI smoke OK total={probe.get('total') if isinstance(probe, dict) else '?'}")
        harvest_series("https://alsi.gie.eu/api", key, ALSI_OUT, "alsi")
        harvest_facilities("https://alsi.gie.eu/api", key, ALSI_OUT, "alsi")
    except Exception as e:
        log(f"ALSI skipped/fail: {e}")

    log("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
