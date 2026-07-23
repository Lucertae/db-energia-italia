#!/usr/bin/env python3
"""Harvest SISEN/DGSAIE open-data CSV exports discovered from the SPA."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

DB = Path(__file__).resolve().parents[1]
OUT = DB / "consumi-italia" / "sources" / "mase" / "sisen_opendata"
UA = {"User-Agent": "Mozilla/5.0 (compatible; harvest-sisen/1.0)"}

# CSV exports from https://sisen.mase.gov.it/dgsaie/open-data
EXPORTS = [
    ("weekly_prices_all.csv", "https://sisen.mase.gov.it/dgsaie/api/v1/weekly-prices/report/export?type=ALL&format=CSV&lang=it"),
    ("weekly_prices_net.csv", "https://sisen.mase.gov.it/dgsaie/api/v1/weekly-prices/report/export?type=NET&format=CSV&lang=it"),
    ("weekly_prices_variation.csv", "https://sisen.mase.gov.it/dgsaie/api/v1/weekly-prices/report/export?type=VARIATION&format=CSV&lang=it"),
    ("weekly_prices_default.csv", "https://sisen.mase.gov.it/dgsaie/api/v1/weekly-prices/report/export?format=CSV&lang=it"),
    ("monthly_prices_all.csv", "https://sisen.mase.gov.it/dgsaie/api/v1/monthly-prices/export?format=CSV&lang=it"),
    ("monthly_prices_1.csv", "https://sisen.mase.gov.it/dgsaie/api/v1/monthly-prices/1/export?format=CSV&lang=it"),
    ("monthly_prices_2.csv", "https://sisen.mase.gov.it/dgsaie/api/v1/monthly-prices/2/export?format=CSV&lang=it"),
    ("monthly_prices_3.csv", "https://sisen.mase.gov.it/dgsaie/api/v1/monthly-prices/3/export?format=CSV&lang=it"),
    ("monthly_prices_5.csv", "https://sisen.mase.gov.it/dgsaie/api/v1/monthly-prices/5/export?format=CSV&lang=it"),
    ("monthly_prices_6.csv", "https://sisen.mase.gov.it/dgsaie/api/v1/monthly-prices/6/export?format=CSV&lang=it"),
    ("monthly_prices_8.csv", "https://sisen.mase.gov.it/dgsaie/api/v1/monthly-prices/8/export?format=CSV&lang=it"),
    ("monthly_prices_12.csv", "https://sisen.mase.gov.it/dgsaie/api/v1/monthly-prices/12/export?format=CSV&lang=it"),
    ("monthly_prices_13.csv", "https://sisen.mase.gov.it/dgsaie/api/v1/monthly-prices/13/export?format=CSV&lang=it"),
]


def log(msg: str) -> None:
    print(msg, flush=True)


def download(url: str, dest: Path, min_size: int = 100) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= min_size:
        log(f"  skip {dest.name} ({dest.stat().st_size/1e6:.2f} MB)")
        return True
    log(f"  GET {url}")
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = resp.read()
        if len(data) < min_size:
            log(f"  FAIL small {dest.name} {len(data)}")
            return False
        if data[:15].lower().startswith(b"<!doctype") or data[:6].lower().startswith(b"<html"):
            log(f"  FAIL HTML {dest.name}")
            return False
        dest.write_bytes(data)
        log(f"  -> {dest.name} ({dest.stat().st_size/1e6:.2f} MB)")
        return True
    except Exception as e:
        log(f"  FAIL {dest.name}: {e}")
        return False


def probe_extra_apis() -> None:
    """Discover more API paths from JS bundle and try CSV export patterns."""
    bundle = "https://sisen.mase.gov.it/dgsaie/dist/js/main.bundle.491fafa2c9dded3c91b2.js"
    # also try double-slash path seen in HTML
    for url in (bundle, "https://sisen.mase.gov.it/dgsaie//dist/js/main.bundle.491fafa2c9dded3c91b2.js"):
        try:
            req = urllib.request.Request(url, headers=UA)
            text = urllib.request.urlopen(req, timeout=120).read().decode("utf-8", "replace")
            apis = sorted(set(re.findall(r"api/v1/[a-zA-Z0-9_\-/{}]+", text)))
            (OUT / "discovered_api_paths.json").write_text(json.dumps(apis, indent=2), encoding="utf-8")
            log(f"  bundle paths: {len(apis)}")
            # try export endpoints for resource-like prefixes
            prefixes = sorted(
                {
                    p.split("{")[0].rstrip("/")
                    for p in apis
                    if any(k in p for k in ("oil", "gas", "coal", "balance", "bilancio", "consum", "import", "export", "ben", "energy"))
                }
            )
            for p in prefixes:
                for fmt in ("CSV", "JSON"):
                    candidate = f"https://sisen.mase.gov.it/dgsaie/{p}/export?format={fmt}&lang=it"
                    name = re.sub(r"[^\w.\-]+", "_", p.replace("api/v1/", "")) + f".{fmt.lower()}"
                    download(candidate, OUT / "probes" / name, min_size=50)
            return
        except Exception as e:
            log(f"  bundle fail {url}: {e}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    log("== SISEN open-data CSV ==")
    ok = 0
    for name, url in EXPORTS:
        if download(url, OUT / name, min_size=200):
            ok += 1
    probe_extra_apis()
    meta = {
        "source": "https://sisen.mase.gov.it/dgsaie/open-data",
        "license": "IODL 2.0",
        "files_ok": ok,
        "total_targets": len(EXPORTS),
    }
    (OUT / "README.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    log(f"DONE ok={ok}/{len(EXPORTS)}")


if __name__ == "__main__":
    main()
