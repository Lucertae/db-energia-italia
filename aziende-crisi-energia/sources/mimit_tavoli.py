"""Modulo 3 — Tavoli di crisi MIMIT."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup
from loguru import logger

import config
from matching import is_energy_related
from models import Company
from sources.base import Source


def _extract_company_lines(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    # rimuovi nav/script
    for tag in soup(["script", "style", "nav", "header", "footer"]):
        tag.decompose()
    text = soup.get_text("\n", strip=True)
    # tra Nota e Vedi anche
    m = re.search(
        r"uffici tecnici competenti\.\s*(.*?)\s*Vedi anche",
        text,
        re.S | re.I,
    )
    chunk = m.group(1) if m else text
    lines = []
    for line in chunk.splitlines():
        line = line.strip(" -\t•")
        if not line or len(line) < 3:
            continue
        if line.lower().startswith("nota"):
            continue
        if "aggiornamento" in line.lower():
            continue
        lines.append(line)
    return lines


class MimitTavoliSource(Source):
    name = "mimit"
    expected_min_results = 1

    def fetch(self) -> list[Company]:
        companies: list[Company] = []
        pages = [
            (config.MIMIT_ATTIVI_URL, "tavolo di crisi MIMIT"),
            (config.MIMIT_MONITORAGGIO_URL, "tavolo di crisi MIMIT (monitoraggio)"),
        ]
        for url, stato in pages:
            try:
                html = self.get_cached_text(url)
            except Exception as exc:  # noqa: BLE001
                logger.warning("MIMIT fetch fallito {}: {}", url, exc)
                continue
            lines = _extract_company_lines(html)
            if not lines:
                logger.error(
                    "MIMIT: 0 aziende da {} — aggiornare parser elenco.",
                    url,
                )
                continue
            for line in lines:
                ok, tag = is_energy_related(text=line)
                # Portovesme (zinc/metalli) e Sofinter (energy/boilers) ecc.:
                # includiamo comunque match keyword; per MIMIT energy-adjacent
                # teniamo anche nomi noti filiera energia/utility se keyword match
                if not ok:
                    continue
                companies.append(
                    Company(
                        denominazione=line,
                        stato=stato,
                        fonte="mimit.gov.it",
                        url=url,
                        note=f"{tag}; elenco pubblico MIMIT",
                    )
                )
        # Se filtro keyword lascia 0 ma pagina aveva voci, logga e restituisci
        # comunque match soft su termini energy-adjacent già in KEYWORDS.
        return companies


def main() -> None:
    src = MimitTavoliSource()
    rows = src.run()
    for r in rows[:10]:
        print(f"{r.denominazione} | {r.stato}")


if __name__ == "__main__":
    main()
