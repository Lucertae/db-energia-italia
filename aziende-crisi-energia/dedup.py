"""Deduplicazione su P.IVA e fuzzy denominazione+provincia."""
from __future__ import annotations

from rapidfuzz import fuzz

import config
from models import Company, normalize_denominazione


def dedup_companies(companies: list[Company]) -> list[Company]:
    by_piva: dict[str, Company] = {}
    no_piva: list[Company] = []

    for c in companies:
        key = c.identity_key()
        if key:
            if key in by_piva:
                by_piva[key].merge_from(c)
            else:
                by_piva[key] = c
        else:
            no_piva.append(c)

    merged_no_piva: list[Company] = []
    for c in no_piva:
        matched: Company | None = None
        c_name = normalize_denominazione(c.denominazione)
        c_prov = (c.provincia or "").strip().upper()
        # match against known piva records
        for existing in list(by_piva.values()) + merged_no_piva:
            e_name = normalize_denominazione(existing.denominazione)
            e_prov = (existing.provincia or "").strip().upper()
            if c_prov and e_prov and c_prov != e_prov:
                continue
            score = fuzz.ratio(c_name, e_name)
            if score >= config.FUZZY_RATIO_THRESHOLD:
                matched = existing
                break
        if matched:
            matched.merge_from(c)
            # if matched was in no_piva list and c somehow got piva via merge — already handled
            if matched.identity_key() and matched.identity_key() not in by_piva:
                by_piva[matched.identity_key()] = matched  # type: ignore[index]
                if matched in merged_no_piva:
                    merged_no_piva.remove(matched)
        else:
            merged_no_piva.append(c)

    return list(by_piva.values()) + merged_no_piva


def stato_sort_key(stato: str) -> tuple[int, str]:
    s = (stato or "").lower().strip()
    best = 99
    for key, prio in config.STATO_PRIORITY.items():
        if key in s:
            best = min(best, prio)
    return best, s


def sort_companies(companies: list[Company]) -> list[Company]:
    return sorted(
        companies,
        key=lambda c: (
            stato_sort_key(c.stato),
            (c.provincia or "").upper(),
            (c.denominazione or "").upper(),
        ),
    )
