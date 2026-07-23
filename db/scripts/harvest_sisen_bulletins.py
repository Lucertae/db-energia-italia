#!/usr/bin/env python3
"""Harvest SISEN bollettino petrolifero / carbone yearly CMIS folders."""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "consumi-italia" / "sources" / "mase" / "sisen_cmis"
UA = {"User-Agent": "Mozilla/5.0 (compatible; harvest-sisen-bulletins/1.0)"}

PREFIXES = [
    "/sg_dgsaie/bollettino/{y}/",
    "/sg_dgsaie/bollettino_carbone/{y}/",
    "/sg_dgsaie/carbone/bollettino/{y}/",
    "/sg_dgsaie/bollettino/carbone/{y}/",
]


def log(msg: str) -> None:
    print(msg, flush=True)


def list_docs(folder: str) -> list[dict]:
    url = (
        "https://sisen.mase.gov.it/dgsaie/api/v1/cmis/documents?folder="
        + urllib.parse.quote(folder, safe="")
    )
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8", "replace"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def download(doc_id: str, name: str, dest_dir: Path) -> bool:
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w.\-]+", "_", name)
    dest = dest_dir / safe
    if dest.exists() and dest.stat().st_size > 800:
        return True
    url = f"https://sisen.mase.gov.it/dgsaie/api/v1/cmis/documents/{doc_id}"
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=180) as resp:
        data = resp.read()
    if len(data) < 800:
        return False
    dest.write_bytes(data)
    log(f"  -> {safe} ({len(data)/1e6:.2f} MB)")
    return True


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ok = total = 0
    for y in range(2003, 2027):
        for tmpl in PREFIXES:
            folder = tmpl.format(y=y)
            docs = list_docs(folder)
            if not docs:
                continue
            log(f"{folder}: {len(docs)}")
            slug = folder.strip("/").replace("sg_dgsaie/", "").replace("/", "__")
            dest = OUT / slug
            for d in docs:
                total += 1
                if download(d["id"], d.get("fileName") or d["id"], dest):
                    ok += 1
                time.sleep(0.08)
    log(f"DONE ok={ok}/{total}")


if __name__ == "__main__":
    main()
