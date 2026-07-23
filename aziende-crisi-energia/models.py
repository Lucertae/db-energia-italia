"""Modello Company e utilità di normalizzazione."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from datetime import date
from typing import Any

SOCIETARY_SUFFIX_RE = re.compile(
    r"\b("
    r"s\.?\s*r\.?\s*l\.?(?:\s*s\.?\s*b\.?)?|"
    r"s\.?\s*p\.?\s*a\.?|"
    r"s\.?\s*a\.?\s*s\.?|"
    r"s\.?\s*n\.?\s*c\.?|"
    r"s\.?\s*c\.?\s*a\.?\s*r\.?\s*l\.?|"
    r"s\.?\s*c\.?\s*r\.?\s*l\.?|"
    r"s\.?\s*s\.?|"
    r"cooperativa|"
    r"coop\.?"
    r")\b",
    re.IGNORECASE,
)


@dataclass
class Company:
    denominazione: str
    piva: str | None = None
    cf: str | None = None
    ateco: str | None = None
    provincia: str | None = None
    stato: str = ""
    fonte: str = ""
    url: str | None = None
    note: str = ""
    data_rilevazione: str = field(default_factory=lambda: date.today().isoformat())

    def identity_key(self) -> str | None:
        p = normalize_piva(self.piva)
        return p if p else None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def merge_from(self, other: Company) -> None:
        if not self.piva and other.piva:
            self.piva = other.piva
        if not self.cf and other.cf:
            self.cf = other.cf
        if not self.ateco and other.ateco:
            self.ateco = other.ateco
        if not self.provincia and other.provincia:
            self.provincia = other.provincia
        if other.fonte and other.fonte not in (self.fonte or "").split("|"):
            self.fonte = "|".join(x for x in [self.fonte, other.fonte] if x)
        if other.note:
            if other.note not in (self.note or ""):
                self.note = " || ".join(x for x in [self.note, other.note] if x)
        if other.url and not self.url:
            self.url = other.url
        # prefer more specific stato if empty
        if other.stato and (not self.stato or len(other.stato) > len(self.stato)):
            if not self.stato:
                self.stato = other.stato


def normalize_piva(value: str | None) -> str | None:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11:
        return digits
    return None


def normalize_cf(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = re.sub(r"[^A-Za-z0-9]", "", value).upper()
    if len(cleaned) == 16 or (cleaned.isdigit() and len(cleaned) == 11):
        return cleaned
    return None


def normalize_denominazione(name: str) -> str:
    text = unicodedata.normalize("NFKD", name or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.upper()
    text = SOCIETARY_SUFFIX_RE.sub(" ", text)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_piva_cf(text: str) -> tuple[str | None, str | None]:
    piva = None
    cf = None
    m = re.search(r"(?:P\.?\s*IVA|Partita\s+IVA)\s*[:\s]*([0-9\s.]{11,15})", text, re.I)
    if m:
        piva = normalize_piva(m.group(1))
    m2 = re.search(r"\b(\d{11})\b", text)
    if not piva and m2:
        piva = normalize_piva(m2.group(1))
    m3 = re.search(
        r"(?:C\.?\s*F\.?|Codice\s+Fiscale)\s*[:\s]*([A-Z0-9]{11,16})",
        text,
        re.I,
    )
    if m3:
        cf = normalize_cf(m3.group(1))
    m4 = re.search(r"\b([A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z])\b", text.upper())
    if not cf and m4:
        cf = normalize_cf(m4.group(1))
    return piva, cf


COMPANY_NAME_RE = re.compile(
    r"([A-Z0-9\"'&.\- ]{3,120}?\s+"
    r"(?:S\.?\s*R\.?\s*L\.?(?:\s*S\.?\s*B\.?)?|S\.?\s*P\.?\s*A\.?|"
    r"S\.?\s*A\.?\s*S\.?|S\.?\s*N\.?\s*C\.?|S\.?\s*C\.?\s*A\.?\s*R\.?\s*L\.?|"
    r"COOPERATIVA|COOP\.?))"
    r"(?:\s+in\s+liquidazione)?",
    re.IGNORECASE,
)


def extract_company_names(text: str) -> list[str]:
    names: list[str] = []
    for m in COMPANY_NAME_RE.finditer(text or ""):
        name = re.sub(r"\s+", " ", m.group(1)).strip(" -|,;")
        if len(name) >= 5:
            names.append(name)
    # dedup preserve order
    seen: set[str] = set()
    out: list[str] = []
    for n in names:
        key = normalize_denominazione(n)
        if key and key not in seen:
            seen.add(key)
            out.append(n)
    return out
