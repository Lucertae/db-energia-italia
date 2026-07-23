#!/usr/bin/env python3
"""Create db/terna-italia: dedicated Terna package with data links/copies + harvest entrypoints."""
from __future__ import annotations

import shutil
from pathlib import Path

DB = Path(__file__).resolve().parents[1]
SRC = DB / "consumi-italia" / "sources" / "terna"
ROOT = DB / "terna-italia"
CRED_SRC = DB / "consumi-italia" / "terna.credentials"
SCRIPT_SRC = DB / "consumi-italia" / "scripts" / "harvest_terna_api.py"
BACKFILL = DB / "scripts" / "terna_total_load_backfill.py"


def log(msg: str) -> None:
    print(msg, flush=True)


def link_or_copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() or dest.is_symlink():
        return
    try:
        # Windows: try junction/symlink directory; file hardlink/symlink
        if src.is_dir():
            dest.symlink_to(src, target_is_directory=True)
            log(f"  link dir {dest.relative_to(DB)} -> {src.relative_to(DB)}")
        else:
            dest.symlink_to(src)
            log(f"  link file {dest.name}")
    except OSError:
        if src.is_dir():
            shutil.copytree(src, dest, dirs_exist_ok=True)
            log(f"  copy dir {dest.relative_to(DB)}")
        else:
            shutil.copy2(src, dest)
            log(f"  copy file {dest.name}")


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "scripts").mkdir(exist_ok=True)
    (ROOT / "sources").mkdir(exist_ok=True)

    if not SRC.exists():
        raise SystemExit(f"missing {SRC}")

    # Link each dataset folder into terna-italia/sources/
    for child in sorted(SRC.iterdir()):
        if child.name.startswith("."):
            continue
        link_or_copy(child, ROOT / "sources" / child.name)

    # Credentials (gitignored later)
    if CRED_SRC.exists():
        link_or_copy(CRED_SRC, ROOT / "terna.credentials")

    # Scripts: copy so package is self-contained for edits
    if SCRIPT_SRC.exists():
        shutil.copy2(SCRIPT_SRC, ROOT / "scripts" / "harvest_terna_api.py")
    if BACKFILL.exists():
        shutil.copy2(BACKFILL, ROOT / "scripts" / "terna_total_load_backfill.py")
        # fix paths in backfill copy to use terna-italia as DB parent for OUT
        text = (ROOT / "scripts" / "terna_total_load_backfill.py").read_text(encoding="utf-8")
        text = text.replace(
            'DB / "consumi-italia" / "sources" / "terna" / "total_load"',
            'Path(__file__).resolve().parents[1] / "sources" / "total_load"',
        )
        # load harvest from local scripts
        text = text.replace(
            'DB / "consumi-italia" / "scripts" / "harvest_terna_api.py"',
            'Path(__file__).resolve().parent / "harvest_terna_api.py"',
        )
        (ROOT / "scripts" / "terna_total_load_backfill.py").write_text(text, encoding="utf-8")

    # Patch harvest_terna_api ROOT to terna-italia
    api = ROOT / "scripts" / "harvest_terna_api.py"
    if api.exists():
        t = api.read_text(encoding="utf-8")
        t = t.replace(
            "ROOT = Path(__file__).resolve().parents[1]",
            "ROOT = Path(__file__).resolve().parents[1]  # terna-italia/",
        )
        # CRED and SOURCES already relative to ROOT — good if parents[1] is terna-italia
        # Original parents[1] was consumi-italia; now parents[1] is terna-italia. OK.
        api.write_text(t, encoding="utf-8")

    (ROOT / ".gitignore").write_text(
        "terna.credentials\n*.credentials\n*.key\n*.secret\n",
        encoding="utf-8",
    )

    (ROOT / "README.md").write_text(
        "# Terna Italia\n\n"
        "Database dedicato ai dati **Terna** (carico, IMCEI, settori, capacità).\n\n"
        "I CSV sotto `sources/` puntano (symlink/copia) a quelli già harvestati in "
        "`consumi-italia/sources/terna/`. Refresh da questa cartella.\n\n"
        "## Credenziali\n\n"
        "Metti `client_id` / `client_secret` in `terna.credentials` "
        "(non commit — già in `.gitignore`).\n\n"
        "## Refresh\n\n```powershell\n"
        "python db/terna-italia/scripts/harvest_terna_api.py\n"
        "python db/terna-italia/scripts/terna_total_load_backfill.py   # 2021-22 se rate-limit ok\n"
        "```\n\n"
        "## Contenuto tipico\n\n"
        "- `sources/total_load/` — carico orario\n"
        "- `sources/imcei/` — indice consumi industriali\n"
        "- `sources/industry_sector/`, `services_sector/`\n"
        "- `sources/electrical_energy_*`, `renewable_source_capacity/`\n"
        "- `sources/bilanci/` — bilanci ISPRA/Terna se presenti\n",
        encoding="utf-8",
    )

    (ROOT / "METADATI.txt").write_text(
        "METADATI — terna-italia\n"
        "Path: db/terna-italia/\n"
        "Origine dati: API Terna Developer + bilanci ISPRA/Terna già in consumi-italia.\n"
        "Nota: total-load 2021-22 può fallire per Developer Over Rate; ritentare.\n"
        "Licenza: termini Terna Developer Portal / open data collegati.\n",
        encoding="utf-8",
    )

    log(f"DONE {ROOT}")


if __name__ == "__main__":
    main()
