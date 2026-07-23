"""Modulo 5 — AstaLegale / fallback Fallcoaste."""
from __future__ import annotations

import re
from urllib.parse import quote_plus, urljoin

from bs4 import BeautifulSoup
from loguru import logger

import config
from matching import is_energy_related
from models import Company, extract_company_names, extract_piva_cf
from sources.base import Source


class AstaLegaleSource(Source):
    name = "astalegale"
    expected_min_results = 0

    def fetch(self) -> list[Company]:
        companies: list[Company] = []
        try:
            companies.extend(self._scrape_astalegale())
        except Exception as exc:  # noqa: BLE001
            logger.warning("astalegale.net bloccato/errore: {} — fallback fallcoaste", exc)
            try:
                companies.extend(self._scrape_fallcoaste())
            except Exception as exc2:  # noqa: BLE001
                logger.error(
                    "Anche fallcoaste fallita: {}. Aggiornare selettori.",
                    exc2,
                )
        return companies

    def _scrape_astalegale(self) -> list[Company]:
        out: list[Company] = []
        for kw in ["fotovoltaico", "energia", "biogas", "eolico", "impianto elettrico"]:
            url = f"https://www.astalegale.net/?s={quote_plus(kw)}"
            html = self.get_cached_text(url)
            if "Request Rejected" in html or len(html) < 400:
                # prova path alternativo
                url = f"https://www.astalegale.net/ricerca?testo={quote_plus(kw)}"
                html = self.get_cached_text(url)
            if "Request Rejected" in html or len(html) < 400:
                raise RuntimeError("astalegale WAF/empty")
            soup = BeautifulSoup(html, "lxml")
            cards = soup.select("a[href*='/Asta'], .asta, .annuncio, .result, article")
            if not cards:
                # generic links
                cards = soup.find_all("a", href=True)
            for a in cards[:80]:
                text = a.get_text(" ", strip=True)
                href = a.get("href") or ""
                if not text or len(text) < 15:
                    continue
                ok, tag = is_energy_related(text=text)
                if not ok:
                    continue
                names = extract_company_names(text)
                name = names[0] if names else text[:120]
                piva, cf = extract_piva_cf(text)
                full = urljoin(url, href)
                out.append(
                    Company(
                        denominazione=name,
                        piva=piva,
                        cf=cf,
                        stato="vendita giudiziaria / asta",
                        fonte="astalegale.net",
                        url=full,
                        note=f"{text[:200]}; {tag}",
                    )
                )
        return out

    def _scrape_fallcoaste(self) -> list[Company]:
        out: list[Company] = []
        for kw in ["fotovoltaico", "energia", "biogas"]:
            url = f"https://www.fallcoaste.it/?s={quote_plus(kw)}"
            html = self.get_cached_text(url)
            soup = BeautifulSoup(html, "lxml")
            for a in soup.find_all("a", href=True)[:100]:
                text = a.get_text(" ", strip=True)
                if len(text) < 20:
                    continue
                ok, tag = is_energy_related(text=text)
                if not ok:
                    continue
                names = extract_company_names(text)
                name = names[0] if names else text[:120]
                out.append(
                    Company(
                        denominazione=name,
                        stato="vendita giudiziaria / asta",
                        fonte="fallcoaste.it",
                        url=urljoin(url, a["href"]),
                        note=f"{text[:200]}; {tag}; fallback",
                    )
                )
        return out


def main() -> None:
    src = AstaLegaleSource()
    rows = src.run()
    for r in rows[:10]:
        print(f"{r.denominazione} | {r.fonte} | {r.note[:100]}")


if __name__ == "__main__":
    main()
