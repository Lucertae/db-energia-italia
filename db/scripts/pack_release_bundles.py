#!/usr/bin/env python3
"""Pack gitignored local data into GitHub-Release-sized pieces (<1.8 GB each).

Excludes secrets. Skips Rust target/ build artifacts.
Output: _release_bundles/ + manifest.json
"""
from __future__ import annotations

import json
import subprocess
import zipfile
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "_release_bundles"
MAX_BYTES = int(1.7 * 1024**3)  # 1.7 GiB safety under GitHub 2GB asset limit
SECRET_SUFFIX = {".key", ".credentials", ".token", ".pem"}
SKIP_PARTS = {".git", "target", "__pycache__", ".venv", "venv", "_release_bundles"}


def is_secret(p: Path) -> bool:
    return p.suffix.lower() in SECRET_SUFFIX or p.name in {".env"} or p.name.endswith(".credentials")


def ignored_files() -> list[Path]:
    out = subprocess.check_output(
        ["git", "ls-files", "-o", "-i", "--exclude-standard"],
        cwd=ROOT,
        text=True,
        errors="replace",
    )
    files = []
    for line in out.splitlines():
        p = ROOT / line
        if not p.is_file():
            continue
        if is_secret(p):
            continue
        if any(part in SKIP_PARTS for part in p.parts):
            continue
        if p.suffix.lower() in {".rlib", ".rmeta"}:
            continue
        files.append(p)
    return files


def group_key(rel: str) -> str:
    parts = rel.split("/")
    if parts[0] == "db" and len(parts) > 1:
        return f"db-{parts[1]}"
    return parts[0].replace(" ", "_")


def split_file(src: Path, dest_dir: Path, prefix: str) -> list[Path]:
    dest_dir.mkdir(parents=True, exist_ok=True)
    parts: list[Path] = []
    size = src.stat().st_size
    n = (size + MAX_BYTES - 1) // MAX_BYTES
    with open(src, "rb") as fh:
        for i in range(n):
            part = dest_dir / f"{prefix}.part{i+1:02d}of{n:02d}"
            with open(part, "wb") as out:
                remaining = MAX_BYTES
                while remaining > 0:
                    chunk = fh.read(min(8 * 1024 * 1024, remaining))
                    if not chunk:
                        break
                    out.write(chunk)
                    remaining -= len(chunk)
            parts.append(part)
            print(f"  split {part.name} ({part.stat().st_size/1e6:.1f} MB)", flush=True)
    return parts


def write_zip(paths: list[Path], zip_path: Path) -> Path:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_STORED) as zf:
        for p in paths:
            arc = p.relative_to(ROOT).as_posix()
            zf.write(p, arcname=arc)
    print(f"  zip {zip_path.name} ({zip_path.stat().st_size/1e6:.1f} MB, {len(paths)} files)", flush=True)
    return zip_path


def pack_group(name: str, files: list[Path]) -> list[dict]:
    """Return manifest entries for assets produced."""
    assets: list[dict] = []
    files = sorted(files, key=lambda p: p.stat().st_size, reverse=True)
    # Handle oversized single files via split
    normal: list[Path] = []
    for p in files:
        if p.stat().st_size > MAX_BYTES:
            print(f"== split oversized {p.relative_to(ROOT)}", flush=True)
            prefix = p.name.replace(" ", "_")
            parts = split_file(p, OUT, f"{name}__{prefix}")
            for part in parts:
                assets.append(
                    {
                        "asset": part.name,
                        "kind": "split-part",
                        "source": p.relative_to(ROOT).as_posix(),
                        "bytes": part.stat().st_size,
                    }
                )
            # join instructions
            join = OUT / f"{name}__{prefix}.JOIN.txt"
            join.write_text(
                "Windows PowerShell:\n"
                f"  Get-Content -Encoding Byte -ReadCount 0 "
                + ", ".join(f"'{x.name}'" for x in parts)
                + f" | Set-Content -Encoding Byte '{p.name}'\n"
                "Or cmd:\n"
                f"  copy /b "
                + "+".join(x.name for x in parts)
                + f" {p.name}\n",
                encoding="utf-8",
            )
            assets.append({"asset": join.name, "kind": "join-instructions", "source": p.relative_to(ROOT).as_posix(), "bytes": join.stat().st_size})
        else:
            normal.append(p)

    # Batch normal files into zips under MAX_BYTES (approx by uncompressed sum)
    batch: list[Path] = []
    batch_size = 0
    idx = 1
    def flush():
        nonlocal batch, batch_size, idx
        if not batch:
            return
        zpath = OUT / f"{name}__part{idx:02d}.zip"
        write_zip(batch, zpath)
        assets.append(
            {
                "asset": zpath.name,
                "kind": "zip",
                "files": [p.relative_to(ROOT).as_posix() for p in batch],
                "bytes": zpath.stat().st_size,
            }
        )
        idx += 1
        batch = []
        batch_size = 0

    for p in normal:
        sz = p.stat().st_size
        if batch and batch_size + sz > MAX_BYTES:
            flush()
        batch.append(p)
        batch_size += sz
    flush()
    return assets


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    files = ignored_files()
    groups: dict[str, list[Path]] = defaultdict(list)
    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        groups[group_key(rel)].append(p)

    print(f"Groups: {len(groups)} files={len(files)} GB={sum(p.stat().st_size for p in files)/1e9:.2f}", flush=True)
    manifest = {"max_bytes": MAX_BYTES, "groups": {}, "assets": []}
    for name in sorted(groups, key=lambda k: sum(p.stat().st_size for p in groups[k]), reverse=True):
        gfiles = groups[name]
        gbytes = sum(p.stat().st_size for p in gfiles)
        print(f"\n## {name}  {gbytes/1e9:.2f} GB  {len(gfiles)} files", flush=True)
        assets = pack_group(name, gfiles)
        manifest["groups"][name] = {"bytes": gbytes, "n_files": len(gfiles), "assets": [a["asset"] for a in assets]}
        manifest["assets"].extend(assets)

    man_path = OUT / "manifest.json"
    man_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nWrote {man_path} assets={len(manifest['assets'])}", flush=True)


if __name__ == "__main__":
    main()
