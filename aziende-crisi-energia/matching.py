"""Matching settore ATECO / keyword."""
from __future__ import annotations

import re

import config


def ateco_matches(ateco: str | None) -> bool:
    if not ateco:
        return False
    # gestisce anche rappresentazioni tipo "['35.11']"
    code = str(ateco).strip().replace(" ", "").replace("[", "").replace("]", "").replace("'", "").replace('"', "")
    for target in config.ATECO_TARGET:
        t = target.replace(" ", "")
        if code.startswith(t) or t.startswith(code):
            return True
        if code.replace(".", "").startswith(t.replace(".", "")):
            return True
    return False


def is_non_energy_ateco(ateco: str | None) -> bool:
    if not ateco:
        return False
    code = str(ateco).strip().replace(" ", "").replace("[", "").replace("]", "").replace("'", "").replace('"', "")
    # ristorazione, commercio al dettaglio, ecc. chiaramente fuori
    return code.startswith("56") or code.startswith("47") or code.startswith("55")


def scrub_boilerplate(text: str) -> str:
    """Rimuove frasi generiche che falsano il match energia (utenze, ecc.)."""
    t = text or ""
    t = re.sub(
        r"contratti?\s+di\s+utenza.{0,100}",
        " ",
        t,
        flags=re.IGNORECASE | re.DOTALL,
    )
    t = re.sub(
        r"utenza\s+per\s+l['\u2019]?\s*energia.{0,60}",
        " ",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"energia\s+elettrica\s*,\s*gas\s+e\s+acqua",
        " ",
        t,
        flags=re.IGNORECASE,
    )
    return t


def keyword_matches(text: str | None) -> bool:
    if not text:
        return False
    blob = f" {scrub_boilerplate(text).lower()} "
    for kw in config.KEYWORDS_ENERGIA:
        k = kw.lower()
        if k.strip() == "gas":
            if re.search(r"(?<![a-z])gas(?![a-zolio])", blob):
                return True
            continue
        if k == "solar":
            if re.search(r"(?<![a-z])solar(?![aoin])", blob):
                return True
            continue
        if k in blob:
            return True
    return False


def has_procedure_signal(text: str | None) -> bool:
    if not text:
        return False
    low = text.lower()
    return any(t in low for t in config.PROCEDURE_TERMS)


def is_energy_related(
    *,
    ateco: str | None = None,
    text: str | None = None,
    ateco_only: bool = False,
) -> tuple[bool, str]:
    if ateco_matches(ateco):
        return True, "match=ateco"
    if ateco_only:
        return False, ""
    if keyword_matches(text):
        return True, "match=keyword"
    return False, ""
