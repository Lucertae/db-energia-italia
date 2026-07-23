"""Modulo 4 — openapi.it / company.openapi.com (richiede OPENAPI_IT_KEY)."""
from __future__ import annotations

from typing import Any

from loguru import logger

import config
from matching import ateco_matches
from models import Company, normalize_piva
from sources.base import Source


class OpenApiItSource(Source):
    name = "openapi"
    expected_min_results = 0

    def fetch(self) -> list[Company]:
        if not config.OPENAPI_IT_KEY:
            logger.warning(
                "OPENAPI_IT_KEY assente: salto modulo openapi. "
                "Registrati su https://openapi.com / company.openapi.com, "
                "crea una API key e inseriscila in .env. "
                "Costo orientativo IT-search: da ~0.001€/hit (name) a pochi centesimi con enrichment."
            )
            return []

        self.session.headers["Authorization"] = f"Bearer {config.OPENAPI_IT_KEY}"
        companies: list[Company] = []
        seen: set[str] = set()

        for ateco in config.ATECO_TARGET:
            ateco_q = ateco.replace(".", "")
            try:
                page = 1
                while page <= 50:
                    params = {
                        "atecoCode": ateco_q,
                        "page": page,
                        "limit": 50,
                    }
                    # dry_run non consuma — utile se supportato; altrimenti chiamata reale
                    data = self.get_cached_json(
                        config.OPENAPI_SEARCH,
                        params=params,
                        headers={"Authorization": f"Bearer {config.OPENAPI_IT_KEY}"},
                    )
                    rows = self._extract_rows(data)
                    if not rows:
                        if page == 1:
                            logger.info("openapi: nessun risultato ATECO {}", ateco)
                        break
                    for row in rows:
                        c = self._row_to_company(row, ateco)
                        if not c or not c.piva or c.piva in seen:
                            continue
                        if not self._is_crisis(row, c):
                            continue
                        seen.add(c.piva)
                        companies.append(c)
                    if len(rows) < 50:
                        break
                    page += 1
            except Exception as exc:  # noqa: BLE001
                logger.warning("openapi ATECO {} errore: {}", ateco, exc)
                continue
        return companies

    def _extract_rows(self, data: Any) -> list[dict]:
        if data is None:
            return []
        if isinstance(data, list):
            return [x for x in data if isinstance(x, dict)]
        if isinstance(data, dict):
            for key in ("data", "items", "results", "companies", "content"):
                val = data.get(key)
                if isinstance(val, list):
                    return [x for x in val if isinstance(x, dict)]
            if "companyName" in data or "vatCode" in data:
                return [data]
        return []

    def _is_crisis(self, row: dict, company: Company) -> bool:
        blob = " ".join(
            str(row.get(k) or "")
            for k in (
                "activityStatus",
                "status",
                "companyStatus",
                "cessationDate",
                "detailedStatus",
                "atecoDescription",
            )
        ).lower()
        blob += " " + (company.stato or "").lower() + " " + (company.note or "").lower()
        return any(h in blob for h in config.OPENAPI_CRISIS_ACTIVITY_HINTS)

    def _row_to_company(self, row: dict, ateco_fallback: str) -> Company | None:
        name = (
            row.get("companyName")
            or row.get("denomination")
            or row.get("name")
            or row.get("ragioneSociale")
            or ""
        )
        if not name:
            return None
        piva = normalize_piva(
            str(row.get("vatCode") or row.get("piva") or row.get("vat") or "")
        )
        cf = row.get("taxCode") or row.get("cf")
        ateco = (
            row.get("atecoCode")
            or row.get("ateco")
            or ateco_fallback
        )
        if isinstance(ateco, dict):
            ateco = ateco.get("code") or ateco_fallback
        provincia = None
        addr = row.get("address") or row.get("registeredOffice") or {}
        if isinstance(addr, dict):
            provincia = addr.get("province") or addr.get("provincia")
        status = (
            row.get("activityStatus")
            or row.get("status")
            or row.get("companyStatus")
            or "stato attività openapi"
        )
        return Company(
            denominazione=str(name),
            piva=piva,
            cf=str(cf) if cf else None,
            ateco=str(ateco) if ateco else None,
            provincia=str(provincia) if provincia else None,
            stato=str(status),
            fonte="openapi.it",
            note="match=ateco; da Company API",
        )


def resolve_piva_by_name(session_source: Source, denominazione: str) -> str | None:
    """Arricchimento opzionale post-merge."""
    if not config.OPENAPI_IT_KEY:
        return None
    try:
        data = session_source.get_cached_json(
            config.OPENAPI_SEARCH,
            params={"companyName": denominazione, "limit": 5},
            headers={"Authorization": f"Bearer {config.OPENAPI_IT_KEY}"},
        )
        src = OpenApiItSource()
        rows = src._extract_rows(data)
        if not rows:
            return None
        return normalize_piva(str(rows[0].get("vatCode") or rows[0].get("piva") or ""))
    except Exception as exc:  # noqa: BLE001
        logger.debug("resolve_piva_by_name fallita: {}", exc)
        return None


def main() -> None:
    src = OpenApiItSource()
    rows = src.run()
    for r in rows[:10]:
        print(f"{r.denominazione} | {r.piva} | {r.stato}")


if __name__ == "__main__":
    main()
