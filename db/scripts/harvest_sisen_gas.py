#!/usr/bin/env python3
"""Harvest remaining SISEN gas/coal/bulletin CMIS folders."""
from __future__ import annotations

import json
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

DB = Path(__file__).resolve().parents[1]
OUT = DB / "consumi-italia" / "sources" / "mase" / "sisen_cmis"
UA = {"User-Agent": "Mozilla/5.0 (compatible; harvest-sisen-gas/1.0)"}


def log(msg: str) -> None:
    print(msg, flush=True)


def get_json(url: str):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def list_folders(folder: str) -> list[str]:
    url = (
        "https://sisen.mase.gov.it/dgsaie/api/v1/cmis/folders?folder="
        + urllib.parse.quote(folder, safe="")
    )
    try:
        data = get_json(url)
        # expect list of folder names or objects
        out = []
        if isinstance(data, list):
            for item in data:
                if isinstance(item, str):
                    out.append(item if item.startswith("/") else folder.rstrip("/") + "/" + item.strip("/") + "/")
                elif isinstance(item, dict):
                    name = item.get("name") or item.get("path") or item.get("id")
                    if name:
                        if str(name).startswith("/"):
                            out.append(str(name) if str(name).endswith("/") else str(name) + "/")
                        else:
                            out.append(folder.rstrip("/") + "/" + str(name).strip("/") + "/")
        return out
    except Exception as e:
        log(f"  folders fail {folder}: {e}")
        return []


def list_docs(folder: str) -> list[dict]:
    url = (
        "https://sisen.mase.gov.it/dgsaie/api/v1/cmis/documents?folder="
        + urllib.parse.quote(folder, safe="")
    )
    try:
        data = get_json(url)
        return data if isinstance(data, list) else []
    except Exception as e:
        log(f"  docs fail {folder}: {e}")
        return []


def download_doc(doc_id: str, file_name: str, dest_dir: Path) -> bool:
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^\w.\-]+", "_", file_name)
    dest = dest_dir / safe
    if dest.exists() and dest.stat().st_size > 800:
        log(f"  skip {safe}")
        return True
    url = f"https://sisen.mase.gov.it/dgsaie/api/v1/cmis/documents/{doc_id}"
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=180) as resp:
            data = resp.read()
        if len(data) < 800 or data[:6].lower().startswith(b"<html"):
            log(f"  FAIL {safe} {len(data)}")
            return False
        dest.write_bytes(data)
        log(f"  -> {safe} ({dest.stat().st_size/1e6:.2f} MB)")
        return True
    except Exception as e:
        log(f"  FAIL {safe}: {e}")
        return False


ROOTS = [
    "/sg_dgsaie/gas_naturale/bilancio/",
    "/sg_dgsaie/gas_naturale/importazioni/",
    "/sg_dgsaie/gas_naturale/consumi_regionali/",
    "/sg_dgsaie/gas_naturale/consumi_provinciali/",
    "/sg_dgsaie/bollettino_petrolifero/",
    "/sg_dgsaie/bollettino_petrolio/",
    "/sg_dgsaie/bollettino_carbone/",
    "/sg_dgsaie/carbone/",
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    # also year folders known from browser
    year_folders = [f"/sg_dgsaie/gas_naturale/bilancio/{y}" for y in range(2004, 2027)]
    folders: list[str] = []
    for root in ROOTS:
        sub = list_folders(root)
        log(f"ROOT {root}: subfolders={len(sub)}")
        folders.append(root)
        folders.extend(sub)
    folders.extend(year_folders)
    folders = sorted(set(folders))

    catalog = {}
    ok = total = 0
    for folder in folders:
        docs = list_docs(folder if folder.endswith("/") else folder + "/")
        # also try without trailing slash
        if not docs and not folder.endswith("/"):
            docs = list_docs(folder)
        if not docs and folder.endswith("/"):
            docs = list_docs(folder.rstrip("/"))
        if not docs:
            continue
        log(f"FOLDER {folder}: {len(docs)}")
        catalog[folder] = [{"id": d.get("id"), "fileName": d.get("fileName")} for d in docs]
        slug = folder.strip("/").replace("sg_dgsaie/", "").replace("/", "__")
        dest = OUT / slug
        for d in docs:
            doc_id = d.get("id")
            name = d.get("fileName") or f"{doc_id}.bin"
            if not doc_id:
                continue
            total += 1
            if download_doc(doc_id, name, dest):
                ok += 1
            time.sleep(0.1)

    (OUT / "catalog_gas_extra.json").write_text(json.dumps(catalog, indent=2), encoding="utf-8")
    log(f"DONE ok={ok}/{total}")


if __name__ == "__main__":
    main()
