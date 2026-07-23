#!/usr/bin/env python3
"""Download remaining reachable gap proxies: ISPRA energia indicators + SISEN CDN probes."""
from __future__ import annotations

import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

DB = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "Mozilla/5.0 (compatible; fill-ispra-mase/1.0)"}


def log(msg: str) -> None:
    print(msg, flush=True)


def get(url: str, timeout: int = 120) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def download(url: str, dest: Path, min_size: int = 500) -> bool:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size >= min_size:
        log(f"  skip {dest.name}")
        return True
    log(f"  GET {url[:160]}")
    try:
        data = get(url)
        if len(data) < min_size:
            log(f"  FAIL small {len(data)}")
            return False
        if data[:20].lower().startswith(b"<!doctype") or data[:10].lower().startswith(b"<html"):
            log("  FAIL HTML")
            return False
        dest.write_bytes(data)
        log(f"  -> {dest.name} ({dest.stat().st_size/1e6:.2f} MB)")
        return True
    except Exception as e:
        log(f"  FAIL: {e}")
        return False


def harvest_ispra_indicators() -> None:
    log("== ISPRA indicatori ambientali energia ==")
    out = DB / "consumi-italia" / "sources" / "ispra" / "indicatori_energia"
    out.mkdir(parents=True, exist_ok=True)
    pages = [
        "https://indicatoriambientali.isprambiente.it/it/energia/consumi-totali-di-energia-fonti-primarie",
        "https://indicatoriambientali.isprambiente.it/it/energia/dipendenza-energetica",
        "https://indicatoriambientali.isprambiente.it/it/energia",
    ]
    found: set[str] = set()
    for page in pages:
        try:
            html = get(page).decode("utf-8", "replace")
            for m in re.findall(r'href=["\']([^"\']+\.(?:xlsx?|csv|zip))["\']', html, re.I):
                found.add(urllib.parse.urljoin(page, m))
            for m in re.findall(r'https?://[^"\'\s<>]+\.(?:xlsx?|csv)', html, re.I):
                found.add(m.split("?")[0])
            # Drupal private file patterns often in data attributes
            for m in re.findall(r"/system/files/[^\"'\s<>]+\.(?:xlsx?|csv)", html, re.I):
                found.add("https://indicatoriambientali.isprambiente.it" + m)
            for m in re.findall(r"/sites/default/files/[^\"'\s<>]+\.(?:xlsx?|csv)", html, re.I):
                found.add("https://indicatoriambientali.isprambiente.it" + m)
            log(f"  {page}: {len(found)} cumulative")
        except Exception as e:
            log(f"  page fail {page}: {e}")

    (out / "discovered_links.json").write_text(json.dumps(sorted(found), indent=2), encoding="utf-8")
    for url in sorted(found):
        name = urllib.parse.unquote(url.rstrip("/").split("/")[-1])
        name = re.sub(r"[^\w.\-]+", "_", name)[:160]
        download(url, out / name)

    # Known attachment filenames mentioned on pages (try common Drupal paths)
    guesses = [
        "Tabella_1_Consumo_interno_lordo_di_energia_per_fonti_primarie_1990_2024.xlsx",
        "Tabella%201_Consumo%20interno%20lordo%20di%20energia%20per%20fonti%20primarie_1990_2024.xlsx",
        "Tabella%201%20Consumo%20interno%20lordo%20di%20energia%20per%20fonti%20primarie%20(2).xls",
        "Tabella%201%20Dipendenza_energetica_italiana_2025.xls",
    ]
    bases = [
        "https://indicatoriambientali.isprambiente.it/sites/default/files/",
        "https://indicatoriambientali.isprambiente.it/system/files/",
        "https://indicatoriambientali.isprambiente.it/sites/default/files/inline-files/",
    ]
    for base in bases:
        for g in guesses:
            download(base + g, out / urllib.parse.unquote(g).replace(" ", "_"))


def harvest_sisen_api_probe() -> None:
    log("== SISEN / DGSAIE API probe ==")
    out = DB / "consumi-italia" / "sources" / "mase"
    out.mkdir(parents=True, exist_ok=True)
    candidates = [
        "https://sisen.mase.gov.it/dgsaie/assets/index.js",
        "https://sisen.mase.gov.it/api/",
        "https://sisen.mase.gov.it/dgsaie/api/",
        "https://sisen.mase.gov.it/dgsaie/open-data",
        "https://sisen.mase.gov.it/backend/api/",
        "https://api.sisen.mase.gov.it/",
    ]
    notes = []
    for url in candidates:
        try:
            data = get(url, timeout=60)
            notes.append({"url": url, "bytes": len(data), "head": data[:200].decode("utf-8", "replace")})
            # extract absolute URLs ending with data extensions
            text = data.decode("utf-8", "replace")
            links = set(re.findall(r"https?://[^\"'\s]+?\.(?:xlsx?|csv|zip|pdf)", text, re.I))
            apiish = set(re.findall(r"https?://[^\"'\s]{0,120}/api/[^\"'\s]{0,120}", text, re.I))
            if links or apiish:
                log(f"  {url}: files={len(links)} api={len(apiish)}")
                for L in sorted(links)[:30]:
                    name = urllib.parse.unquote(L.rstrip("/").split("/")[-1])[:140]
                    download(L, out / name)
            else:
                log(f"  {url}: {len(data)} bytes, no file urls")
            # if JS bundle, save snippet for inspection
            if url.endswith(".js") and len(data) > 1000:
                (out / "sisen_index_js_head.txt").write_text(text[:5000], encoding="utf-8")
        except Exception as e:
            notes.append({"url": url, "error": str(e)})
            log(f"  fail {url}: {e}")
    (out / "sisen_probe.json").write_text(json.dumps(notes, indent=2), encoding="utf-8")


def harvest_eua_older() -> None:
    log("== EUA older years probe ==")
    out = DB / "mercati-italia" / "sources" / "ets_eua"
    base = "https://public.eex-group.com/eex/eua-auction-report/"
    for y in range(2012, 2017):
        for ext in ("xlsx", "xls"):
            name = f"emission-spot-primary-market-auction-report-{y}-data.{ext}"
            if download(base + name, out / name, min_size=3000):
                break


def main() -> None:
    harvest_eua_older()
    harvest_ispra_indicators()
    harvest_sisen_api_probe()
    log("DONE")


if __name__ == "__main__":
    main()
