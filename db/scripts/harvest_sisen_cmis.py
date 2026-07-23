#!/usr/bin/env python3
"""Harvest SISEN CMIS documents via folder listing API."""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

DB = Path(__file__).resolve().parents[1]
OUT = DB / "consumi-italia" / "sources" / "mase" / "sisen_cmis"
UA = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
}

# Known folders from network traffic on the SISEN SPA
FOLDERS = [
    "/sg_dgsaie/ben/",
    "/sg_dgsaie/ben_eurostat/",
    "/sg_dgsaie/consumi_petroliferi/definitivi/",
    "/sg_dgsaie/consumi_petroliferi/preconsuntivi/2024/",
    "/sg_dgsaie/consumi_petroliferi/preconsuntivi/2025/",
    "/sg_dgsaie/consumi_petroliferi/preconsuntivi/2026/",
]

# Extra guesses to try once (gas/coal bulletins etc.)
EXTRA = [
    "/sg_dgsaie/gas_naturale/",
    "/sg_dgsaie/gas_naturale/bilancio/",
    "/sg_dgsaie/gas_naturale/importazioni/",
    "/sg_dgsaie/gas_naturale/consumi_regionali/",
    "/sg_dgsaie/gas_naturale/consumi_provinciali/",
    "/sg_dgsaie/bollettino_petrolifero/",
    "/sg_dgsaie/bollettino_petrolio/",
    "/sg_dgsaie/petrolio/bollettino/",
    "/sg_dgsaie/bollettino_carbone/",
    "/sg_dgsaie/carbone/bollettino/",
    "/sg_dgsaie/carbone/",
    "/sg_dgsaie/situazione_energetica/",
    "/sg_dgsaie/prezzi_annuali/",
]


def log(msg: str) -> None:
    print(msg, flush=True)


def get_json(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def list_folder(folder: str) -> list[dict]:
    url = (
        "https://sisen.mase.gov.it/dgsaie/api/v1/cmis/documents?folder="
        + urllib.parse.quote(folder, safe="")
    )
    try:
        data = get_json(url)
        if isinstance(data, list):
            return data
        return []
    except Exception as e:
        log(f"  folder fail {folder}: {e}")
        return []


def download_doc(doc_id: str, file_name: str, dest_dir: Path) -> bool:
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w.\-]+", "_", file_name)
    dest = dest_dir / safe
    if dest.exists() and dest.stat().st_size > 800:
        log(f"  skip {safe}")
        return True
    url = f"https://sisen.mase.gov.it/dgsaie/api/v1/cmis/documents/{doc_id}"
    req = urllib.request.Request(url, headers=UA)
    try:
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = resp.read()
        if len(data) < 800:
            log(f"  FAIL small {safe} {len(data)}")
            return False
        if data[:15].lower().startswith(b"<!doctype") or data[:6].lower().startswith(b"<html"):
            log(f"  FAIL HTML {safe}")
            return False
        dest.write_bytes(data)
        log(f"  -> {safe} ({dest.stat().st_size/1e6:.2f} MB)")
        return True
    except Exception as e:
        log(f"  FAIL {safe}: {e}")
        return False


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    folders = list(FOLDERS)
    for f in EXTRA:
        docs = list_folder(f)
        if docs:
            log(f"EXTRA hit {f}: {len(docs)}")
            folders.append(f)
        else:
            log(f"EXTRA miss {f}")

    catalog: dict[str, list[dict]] = {}
    ok = 0
    total = 0
    for folder in folders:
        docs = list_folder(folder)
        log(f"FOLDER {folder}: {len(docs)}")
        catalog[folder] = [
            {"id": d.get("id"), "fileName": d.get("fileName"), "size": d.get("size")}
            for d in docs
        ]
        slug = folder.strip("/").replace("sg_dgsaie/", "").replace("/", "__")
        dest_dir = OUT / slug
        for d in docs:
            doc_id = d.get("id")
            name = d.get("fileName") or f"{doc_id}.bin"
            if not doc_id:
                continue
            total += 1
            if download_doc(doc_id, name, dest_dir):
                ok += 1
            time.sleep(0.12)

    (OUT / "catalog.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    (OUT / "README.txt").write_text(
        "SISEN/DGSAIE CMIS harvest via /api/v1/cmis/documents?folder=...\n"
        "Source: https://sisen.mase.gov.it/dgsaie/\n"
        "License: IODL 2.0\n",
        encoding="utf-8",
    )
    log(f"DONE ok={ok}/{total}")


if __name__ == "__main__":
    main()
