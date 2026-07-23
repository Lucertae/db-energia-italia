"""Modulo 6 — Rassegna news fallimenti (Google News RSS)."""
from __future__ import annotations

from urllib.parse import quote_plus

import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from loguru import logger

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

import config
from matching import has_procedure_signal, is_energy_related
from models import Company, extract_company_names, extract_piva_cf
from sources.base import Source

RSS = "https://news.google.com/rss/search?q={q}&hl=it&gl=IT&ceid=IT:it"


class FallimentiNewsSource(Source):
    name = "news"
    expected_min_results = 0

    def fetch(self) -> list[Company]:
        companies: list[Company] = []
        seen: set[str] = set()
        energy_kw = [
            "fotovoltaico",
            "energia",
            "eolico",
            "biogas",
            "biometano",
            "idroelettrico",
            "teleriscaldamento",
            "utility",
            "rinnovabili",
            "idrogeno",
        ]
        proc_kw = [
            "liquidazione giudiziale",
            "fallimento",
            "concordato",
            "in liquidazione",
            "amministrazione straordinaria",
        ]
        queries: list[str] = []
        for e in energy_kw:
            for p in proc_kw:
                queries.append(f'"{p}" {e} srl OR spa')
        queries = queries[: config.NEWS_MAX_QUERIES]

        for q in queries:
            url = RSS.format(q=quote_plus(q))
            try:
                xml = self.get_cached_text(url)
            except Exception as exc:  # noqa: BLE001
                logger.warning("News RSS fallita: {} ({})", q, exc)
                continue
            soup = BeautifulSoup(xml, "lxml-xml")
            items = soup.find_all("item")
            if not items:
                soup = BeautifulSoup(xml, "lxml")
                items = soup.find_all("item")
            for item in items:
                title = item.title.get_text(strip=True) if item.title else ""
                link = item.link.get_text(strip=True) if item.link else ""
                desc = item.description.get_text(" ", strip=True) if item.description else ""
                blob = f"{title} {desc}"
                if not has_procedure_signal(blob):
                    continue
                ok, tag = is_energy_related(text=blob)
                if not ok:
                    continue
                names = extract_company_names(blob)
                if not names:
                    continue
                low = blob.lower()
                stato = "distress / news"
                if "concordato" in low:
                    stato = "concordato preventivo"
                elif "liquidazione giudiziale" in low:
                    stato = "liquidazione giudiziale"
                elif "fallimento" in low or "fallita" in low:
                    stato = "fallimento"
                elif "amministrazione straordinaria" in low:
                    stato = "amministrazione straordinaria"
                elif "in liquidazione" in low:
                    stato = "in liquidazione"
                for name in names[:2]:
                    key = name.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    piva, cf = extract_piva_cf(blob)
                    companies.append(
                        Company(
                            denominazione=name,
                            piva=piva,
                            cf=cf,
                            stato=stato,
                            fonte="google_news_rss",
                            url=link or None,
                            note=(
                                f"{title[:180]}; {tag}; "
                                "fonte giornalistica, da verificare in visura"
                            ),
                        )
                    )
        return companies


def main() -> None:
    src = FallimentiNewsSource()
    rows = src.run()
    for r in rows[:10]:
        print(f"{r.denominazione} | {r.stato} | {r.note[:100]}")


if __name__ == "__main__":
    main()
