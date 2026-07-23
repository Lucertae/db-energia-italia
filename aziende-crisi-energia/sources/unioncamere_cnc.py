"""Modulo 7 — Composizione negoziata / misure protettive (Unioncamere / Telemaco stub)."""
from __future__ import annotations

from urllib.parse import quote_plus

from bs4 import BeautifulSoup
from loguru import logger

import config
from matching import is_energy_related
from models import Company, extract_company_names, extract_piva_cf
from sources.base import Source

RSS = "https://news.google.com/rss/search?q={q}&hl=it&gl=IT&ceid=IT:it"


class UnioncamereCncSource(Source):
    name = "cnc"
    expected_min_results = 0

    def fetch(self) -> list[Company]:
        if config.TELEMACO_USER and config.TELEMACO_PASS:
            logger.warning(
                "TELEMACO_USER/PASS presenti ma connettore Telemaco non implementato "
                "(API InfoCamere a pagamento/convenzione). "
                "Documentare accesso e endpoint nel README; fallback su news/GU."
            )
            # stub intenzionale: nessuna chiamata fittizia
        else:
            logger.warning(
                "TELEMACO_USER/PASS assenti: composizione negoziata non è in elenco aperto. "
                "Fallback: news/GU su 'misure protettive' + keyword energia. "
                "Per dati ufficiali: convenzione Telemaco/InfoCamere o visure."
            )

        companies: list[Company] = []
        seen: set[str] = set()
        queries = [
            'misure protettive energia OR fotovoltaico OR biogas',
            '"composizione negoziata" fotovoltaico OR energia srl',
            '"misure protettive" "rinnovabili" OR idroelettrico',
            '"conferma delle misure protettive" energia',
        ]
        for q in queries:
            url = RSS.format(q=quote_plus(q))
            try:
                xml = self.get_cached_text(url)
            except Exception as exc:  # noqa: BLE001
                logger.warning("CNC news fallita: {}", exc)
                continue
            soup = BeautifulSoup(xml, "lxml-xml")
            items = soup.find_all("item") or BeautifulSoup(xml, "lxml").find_all("item")
            for item in items:
                title = item.title.get_text(strip=True) if item.title else ""
                link = item.link.get_text(strip=True) if item.link else ""
                desc = item.description.get_text(" ", strip=True) if item.description else ""
                blob = f"{title} {desc}"
                ok, tag = is_energy_related(text=blob)
                if not ok:
                    continue
                if any(x in blob.lower() for x in ("spagna", "sánchez", "sanchez")):
                    continue
                names = extract_company_names(blob)
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
                            stato="composizione negoziata / misure protettive",
                            fonte="unioncamere_cnc_proxy",
                            url=link or None,
                            note=(
                                f"{title[:180]}; {tag}; "
                                "proxy news — verificare Registro Imprese / Telemaco"
                            ),
                        )
                    )
        return companies


def main() -> None:
    src = UnioncamereCncSource()
    rows = src.run()
    for r in rows[:10]:
        print(f"{r.denominazione} | {r.stato}")


if __name__ == "__main__":
    main()
