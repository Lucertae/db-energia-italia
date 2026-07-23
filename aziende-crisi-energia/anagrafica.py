"""Caricamento anagrafica locale ARERA (aziende-energetiche-it.txt) per enrichment."""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from loguru import logger
from rapidfuzz import fuzz, process

from models import normalize_denominazione, normalize_piva


LINE_RE = re.compile(
    r"^(?P<name>.+?)\s*\|\s*P\.IVA\s+(?P<piva>\d{11})\s*\|\s*(?P<addr>.*)$"
)
PROV_RE = re.compile(r"\(([^)]+)\)\s*$")


@dataclass
class AnagraficaRow:
    denominazione: str
    piva: str
    provincia: str | None
    indirizzo: str


@lru_cache(maxsize=1)
def load_anagrafica(path: str) -> tuple[AnagraficaRow, ...]:
    p = Path(path)
    if not p.exists():
        logger.warning("Anagrafica locale non trovata: {}", p)
        return tuple()
    rows: list[AnagraficaRow] = []
    for line in p.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("="):
            continue
        if "P.IVA" not in line:
            continue
        m = LINE_RE.match(line)
        if not m:
            continue
        addr = m.group("addr").strip()
        prov_m = PROV_RE.search(addr)
        provincia = prov_m.group(1).strip() if prov_m else None
        rows.append(
            AnagraficaRow(
                denominazione=m.group("name").strip().strip('"'),
                piva=m.group("piva"),
                provincia=provincia,
                indirizzo=addr,
            )
        )
    logger.info("Anagrafica locale: {} imprese da {}", len(rows), p)
    return tuple(rows)


def index_by_piva(path: str) -> dict[str, AnagraficaRow]:
    return {r.piva: r for r in load_anagrafica(path)}


def resolve_from_anagrafica(
    *,
    path: str,
    denominazione: str,
    provincia: str | None = None,
    score_cutoff: int = 92,
) -> AnagraficaRow | None:
    rows = load_anagrafica(path)
    if not rows:
        return None
    choices = {normalize_denominazione(r.denominazione): r for r in rows}
    query = normalize_denominazione(denominazione)
    if not query:
        return None
    match = process.extractOne(
        query,
        list(choices.keys()),
        scorer=fuzz.ratio,
        score_cutoff=score_cutoff,
    )
    if not match:
        return None
    row = choices[match[0]]
    if provincia and row.provincia:
        if normalize_denominazione(provincia) not in normalize_denominazione(row.provincia) and normalize_denominazione(
            row.provincia
        ) not in normalize_denominazione(provincia):
            # soft check — still accept high score
            if match[1] < 96:
                return None
    return row


def enrich_company_from_anagrafica(company, path: str) -> None:
    """Mutates company in place."""
    idx = index_by_piva(path)
    piva = normalize_piva(company.piva)
    if piva and piva in idx:
        row = idx[piva]
        if not company.provincia:
            company.provincia = row.provincia
        note_tag = "anagrafica_energia=1"
        if note_tag not in (company.note or ""):
            company.note = (
                f"{company.note}; {note_tag}" if company.note else note_tag
            )
        return
    if not company.piva and company.denominazione:
        row = resolve_from_anagrafica(
            path=path,
            denominazione=company.denominazione,
            provincia=company.provincia,
        )
        if row:
            company.piva = row.piva
            if not company.provincia:
                company.provincia = row.provincia
            tag = "anagrafica_energia=1; piva_da_anagrafica"
            company.note = f"{company.note}; {tag}" if company.note else tag
