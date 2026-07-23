#!/usr/bin/env python3
"""Download EEX EUA auction reports + MASE relazione / SISEN links."""
from __future__ import annotations

import re
import shutil
import urllib.parse
import urllib.request
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (compatible; fill-eua-mase/1.0)"}
DB = Path(__file__).resolve().parents[1]


def log(msg: str) -> None:
    print(msg, flush=True)


def get(url: str) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as resp:
        return resp.read()


def download(url: str, dest: Path, min_size: int = 1000) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= min_size:
        log(f"  skip {dest.name}")
        return True
    log(f"  GET {url[:140]}")
    try:
        data = get(url)
        if len(data) < min_size:
            log(f"  FAIL small {dest.name} {len(data)}")
            return False
        if data[:20].lower().startswith(b"<!doctype") or data[:10].lower().startswith(b"<html"):
            log(f"  FAIL HTML {dest.name}")
            return False
        dest.write_bytes(data)
        log(f"  -> {dest.name} ({dest.stat().st_size/1e6:.2f} MB)")
        return True
    except Exception as e:
        log(f"  FAIL {dest.name}: {e}")
        return False


def harvest_eua() -> None:
    out = DB / "mercati-italia" / "sources" / "ets_eua"
    out.mkdir(parents=True, exist_ok=True)
    base = "https://public.eex-group.com/eex/eua-auction-report/"
    html = get(base).decode("utf-8", "replace")
    files = re.findall(r'href="(emission-spot-primary-market-auction-report-[^"]+)"', html)
    log(f"EEX files: {len(files)}")
    for f in files:
        download(base + f, out / f, min_size=5000)
    # also history zip from EEX downloads if discoverable
    download(
        "https://www.eex.com/fileadmin/EEX/Downloads/Trading/Market_Data/Environmentals/"
        "History_Emission_Spot_Primary_Market_Auction_Report_2012-2025.zip",
        out / "History_Emission_Spot_Primary_Market_Auction_Report_2012-2025.zip",
        min_size=10_000,
    )


def harvest_mase() -> None:
    out = DB / "consumi-italia" / "sources" / "mase"
    out.mkdir(parents=True, exist_ok=True)
    # Relazione situazione energetica 2023 (PDF document id)
    candidates = [
        "https://www.mase.gov.it/portale/documents/d/guest/relazione-situazione-energetica-nazionale_-2023-pdf",
        "https://www.mase.gov.it/portale/documents/d/guest/relazione_situazione_energetica_nazionale_2023",
    ]
    for url in candidates:
        if download(url, out / "relazione_situazione_energetica_nazionale_2023.pdf", min_size=50_000):
            break

    pages = [
        "https://sisen.mase.gov.it/dgsaie/",
        "https://sisen.mase.gov.it/dgsaie/consumi-petroliferi",
        "https://sisen.mase.gov.it/dgsaie/bilancio-energetico-nazionale",
        "https://dgsaie.mise.gov.it/bilancio-energetico-nazionale",
        "https://dgsaie.mise.gov.it/consumi-petroliferi",
    ]
    found: list[str] = []
    for page in pages:
        try:
            html = get(page).decode("utf-8", "replace")
            links = re.findall(r'href=["\']([^"\']+\.(?:xlsx?|csv|pdf|zip|xls))["\']', html, re.I)
            log(f"  {page}: {len(links)} file links")
            for L in links:
                found.append(urllib.parse.urljoin(page, L))
        except Exception as e:
            log(f"  page fail {page}: {e}")

    (out / "discovered_links.json").write_text(
        __import__("json").dumps(sorted(set(found)), indent=2), encoding="utf-8"
    )
    for url in sorted(set(found))[:50]:
        name = urllib.parse.unquote(url.rstrip("/").split("/")[-1])
        name = re.sub(r"[^\w.\-]+", "_", name)[:140]
        download(url, out / name, min_size=800)


def main() -> None:
    harvest_eua()
    harvest_mase()
    log("DONE")


if __name__ == "__main__":
    main()
