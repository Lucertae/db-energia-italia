#!/usr/bin/env python3
"""Harvest Terna public APIs for Italy consumption (IMCEI + sectors)."""
from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCES = ROOT / "sources" / "terna"
CRED = ROOT / "terna.credentials"
UA = {"User-Agent": "consumi-italia/1.0"}
SLEEP = 2.5  # stay under Developer Over Qps / Over Rate


def log(msg: str) -> None:
    try:
        print(msg, flush=True)
    except UnicodeEncodeError:
        print(msg.encode("ascii", "replace").decode("ascii"), flush=True)


def load_creds() -> tuple[str, str]:
    cid = sec = ""
    for line in CRED.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("client_id="):
            cid = line.split("=", 1)[1].strip()
        elif line.startswith("client_secret="):
            sec = line.split("=", 1)[1].strip()
    if not cid or not sec:
        raise SystemExit(f"Missing client_id/client_secret in {CRED}")
    return cid, sec


class TernaClient:
    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self.token = ""
        self.token_ts = 0.0

    def refresh(self) -> str:
        data = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            }
        ).encode()
        last_err: Exception | None = None
        for attempt in range(8):
            req = urllib.request.Request(
                "https://api.terna.it/public-api/access-token",
                data=data,
                headers={**UA, "Content-Type": "application/x-www-form-urlencoded"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=60) as resp:
                    payload = json.loads(resp.read().decode())
                self.token = payload["access_token"]
                self.token_ts = time.time()
                log(f"  token refreshed (expires_in={payload.get('expires_in')})")
                return self.token
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace")
                last_err = e
                if e.code == 403 and ("Over Rate" in body or "Over Qps" in body or "Over Rate" in str(e)):
                    wait = 60 + attempt * 60
                    log(f"  token rate-limit, sleep {wait}s")
                    time.sleep(wait)
                    continue
                raise
        raise RuntimeError(f"token refresh failed: {last_err}")

    def ensure_token(self) -> str:
        if not self.token or time.time() - self.token_ts > 240:
            return self.refresh()
        return self.token

    def get(self, url: str) -> dict:
        for attempt in range(8):
            token = self.ensure_token()
            req = urllib.request.Request(
                url,
                headers={
                    **UA,
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/json",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    return json.loads(resp.read().decode())
            except urllib.error.HTTPError as e:
                body = e.read().decode("utf-8", "replace")
                if e.code == 403 and ("Over Qps" in body or "Over Rate" in body):
                    wait = 15 + attempt * 20
                    log(f"  rate/QPS limit, sleep {wait}s")
                    time.sleep(wait)
                    continue
                if e.code == 401:
                    self.refresh()
                    time.sleep(2)
                    continue
                raise RuntimeError(f"HTTP {e.code}: {body[:300]}") from e
        raise RuntimeError(f"Failed after retries: {url}")


def save_csv(rows: list[dict], dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(dest, index=False)
    log(f"  wrote {dest.relative_to(ROOT)} rows={len(rows)}")


def harvest_imcei(client: TernaClient) -> None:
    log("== IMCEI ==")
    rows: list[dict] = []
    for year in range(2015, 2027):
        for month in range(1, 13):
            if year == 2026 and month > 7:
                break
            url = (
                "https://api.terna.it/load/v2.0/monthly-index-industrial-electrical-consumption"
                f"?year={year}&month={month:02d}"
            )
            try:
                data = client.get(url)
            except Exception as e:
                log(f"  IMCEI {year}-{month:02d} FAIL {e}")
                time.sleep(SLEEP)
                continue
            items = data.get("monthly_index_industrial_electrical_consumption") or []
            rows.extend(items)
            log(f"  IMCEI {year}-{month:02d}: {len(items)}")
            time.sleep(SLEEP)
    save_csv(rows, SOURCES / "imcei" / "imcei_all.csv")


def harvest_yearly(client: TernaClient, path: str, key: str, years: range) -> None:
    log(f"== {path} ==")
    rows: list[dict] = []
    for year in years:
        url = f"https://api.terna.it/load/v2.0/{path}?year={year}"
        try:
            data = client.get(url)
        except Exception as e:
            log(f"  {path} {year} FAIL {e}")
            time.sleep(SLEEP)
            continue
        items = data.get(key) or []
        rows.extend(items)
        log(f"  {path} {year}: {len(items)}")
        time.sleep(SLEEP)
    save_csv(rows, SOURCES / path.replace("-", "_") / f"{path.replace('-', '_')}_all.csv")


def main() -> int:
    cid, sec = load_creds()
    client = TernaClient(cid, sec)
    log("== Terna OAuth ==")
    client.refresh()

    # annual aggregates first (few calls)
    harvest_yearly(
        client,
        "electrical-energy-by-sector",
        "electrical_energy_by_sector",
        range(2015, 2026),
    )
    harvest_yearly(client, "industry-sector", "industry_sector", range(2015, 2026))
    harvest_yearly(client, "services-sector", "services_sector", range(2015, 2026))
    harvest_imcei(client)

    # refresh metadati snippet
    meta = ROOT / "METADATI.txt"
    extra = "\nTerna API harvest: sources/terna/{imcei,industry_sector,services_sector,electrical_energy_by_sector}/\n"
    if meta.exists() and "Terna API harvest" not in meta.read_text(encoding="utf-8"):
        meta.write_text(meta.read_text(encoding="utf-8") + extra, encoding="utf-8")

    log("DONE")
    return 0


if __name__ == "__main__":
    sys.exit(main())
