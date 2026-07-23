#!/usr/bin/env python3
"""Extract ISPRA indicator HTML tables + MIT open-data mobility datasets."""
from __future__ import annotations

import io
import json
import urllib.parse
import urllib.request
from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parents[1]
UA = {"User-Agent": "territorio-mobilita-italia/1.0"}
OUT = DB / "socio-italia" / "sources" / "mobility"


def log(msg: str) -> None:
    print(msg, flush=True)


def fetch(url: str, timeout: int = 90) -> bytes:
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def ispra_tables() -> None:
    log("== ISPRA indicator tables ==")
    dest = OUT / "ispra"
    dest.mkdir(parents=True, exist_ok=True)
    pages = [
        (
            "https://indicatoriambientali.isprambiente.it/it/trasporti/dimensione-della-flotta-veicolare",
            "flotta_veicolare",
        ),
        (
            "https://indicatoriambientali.isprambiente.it/it/trasporti/quota-della-flotta-veicolare-conforme-determinati-standard-di-emissione",
            "flotta_euro_standards",
        ),
        (
            "https://indicatoriambientali.isprambiente.it/it/trasporti/emissioni-di-inquinanti-atmosferici-dal-trasporto",
            "emissioni_trasporto",
        ),
        (
            "https://indicatoriambientali.isprambiente.it/it/trasporti/consumi-di-carburanti-a-minor-impatto-ambientale",
            "carburanti_minor_impatto",
        ),
        (
            "https://indicatoriambientali.isprambiente.it/it/suolo-e-territorio/consumo-di-suolo",
            "consumo_suolo",
        ),
        (
            "https://indicatoriambientali.isprambiente.it/it/suolo-e-territorio/frammentazione-del-territorio",
            "frammentazione_territorio",
        ),
    ]
    land = DB / "socio-italia" / "sources" / "land_use" / "ispra"
    land.mkdir(parents=True, exist_ok=True)
    for url, slug in pages:
        try:
            html = fetch(url).decode("utf-8", "replace")
            html_path = dest / f"{slug}.html"
            html_path.write_text(html, encoding="utf-8")
            try:
                tables = pd.read_html(io.StringIO(html))
            except ValueError:
                log(f"  {slug}: no HTML tables")
                continue
            log(f"  {slug}: {len(tables)} tables")
            for i, t in enumerate(tables):
                out_dir = land if "suolo" in slug or "framment" in slug else dest
                path = out_dir / f"{slug}_t{i}.csv"
                t.to_csv(path, index=False)
                log(f"    -> {path.relative_to(DB)} rows={len(t)}")
        except Exception as e:
            log(f"  FAIL {slug}: {type(e).__name__}: {e}")


def mit_ckan() -> None:
    log("== MIT / dati.gov mobility ==")
    dest = OUT / "mit_opendata"
    dest.mkdir(parents=True, exist_ok=True)
    # CKAN search
    queries = ["traffico", "veicoli", "mobilita", "trasporti", "incidenti stradali"]
    api = "https://dati.mit.gov.it/catalog/api/3/action/package_search"
    found = []
    for q in queries:
        url = api + "?" + urllib.parse.urlencode({"q": q, "rows": 20})
        try:
            payload = json.loads(fetch(url, timeout=60).decode())
            for pkg in payload.get("result", {}).get("results", []):
                found.append(pkg)
        except Exception as e:
            log(f"  search {q}: {e}")

    # also national dati.gov
    api2 = "https://www.dati.gov.it/opendata/api/3/action/package_search"
    for q in ["traffico Italia", "parco veicolare", "ACI veicoli"]:
        url = api2 + "?" + urllib.parse.urlencode({"q": q, "rows": 15})
        try:
            payload = json.loads(fetch(url, timeout=60).decode())
            for pkg in payload.get("result", {}).get("results", []):
                found.append(pkg)
        except Exception as e:
            log(f"  dati.gov {q}: {e}")

    seen = set()
    meta_rows = []
    downloads = 0
    for pkg in found:
        pid = pkg.get("id") or pkg.get("name")
        if pid in seen:
            continue
        seen.add(pid)
        title = pkg.get("title") or pkg.get("name")
        for res in pkg.get("resources") or []:
            fmt = (res.get("format") or "").lower()
            url = res.get("url") or ""
            if not url:
                continue
            meta_rows.append(
                {
                    "package": title,
                    "resource": res.get("name"),
                    "format": fmt,
                    "url": url,
                }
            )
            if fmt not in ("csv", "xlsx", "xls", "json", "zip", "geojson") and not any(
                url.lower().endswith(ext) for ext in (".csv", ".xlsx", ".xls", ".json", ".zip", ".geojson")
            ):
                continue
            name = urllib.parse.unquote(url.rstrip("/").split("/")[-1].split("?")[0])
            name = "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in name)[:120]
            if not name or name == "download":
                name = f"{pid}_{res.get('id','r')[:8]}.{fmt or 'bin'}"
            path = dest / name
            if path.exists() and path.stat().st_size > 500:
                continue
            try:
                data = fetch(url, timeout=180)
                if data[:15].lower().startswith(b"<!doctype") or len(data) < 200:
                    continue
                path.write_bytes(data)
                downloads += 1
                log(f"  -> {path.name} ({len(data)/1e6:.2f} MB) [{title[:40]}]")
                if downloads >= 25:
                    break
            except Exception as e:
                log(f"  FAIL {name}: {e}")
        if downloads >= 25:
            break
    if meta_rows:
        pd.DataFrame(meta_rows).drop_duplicates().to_csv(dest / "catalog_hits.csv", index=False)
        log(f"  catalog hits={len(meta_rows)} downloaded={downloads}")


def main() -> None:
    ispra_tables()
    mit_ckan()
    log("DONE ispra/mit")


if __name__ == "__main__":
    main()
