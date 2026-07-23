"""Modulo 2 — Gazzetta Ufficiale (Foglio delle Inserzioni / ricerca pubblica)."""
from __future__ import annotations

import re
from datetime import date, timedelta
from urllib.parse import quote_plus, urljoin

import warnings

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from loguru import logger

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

import config
from matching import is_energy_related
from models import Company, extract_company_names, extract_piva_cf
from sources.base import Source

# La ricerca full-text GU spesso richiede sessione; usiamo:
# 1) Google News RSS site:gazzettaufficiale.it (pubblico)
# 2) Eventuali URL diretti elenco FOGLIO_INSERZIONI se raggiungibili
GU_RSS_TMPL = (
    "https://news.google.com/rss/search?q={query}&hl=it&gl=IT&ceid=IT:it"
)


class GazzettaUfficialeSource(Source):
    name = "gu"
    expected_min_results = 0

    def fetch(self) -> list[Company]:
        lookback = getattr(self, "lookback_months", config.LOOKBACK_MONTHS)
        cutoff = date.today() - timedelta(days=30 * lookback)
        companies: list[Company] = []
        seen: set[str] = set()

        queries: list[str] = []
        for kw in ["fotovoltaico", "energia", "biogas", "idroelettrico", "eolico", "biometano"]:
            for term in ["liquidazione", "concordato", "fallimento", "liquidazione giudiziale"]:
                queries.append(f'site:gazzettaufficiale.it "{kw}" "{term}"')
        queries = queries[:20]

        for q in queries:
            url = GU_RSS_TMPL.format(query=quote_plus(q))
            try:
                xml = self.get_cached_text(url)
            except Exception as exc:  # noqa: BLE001
                logger.warning("GU RSS fallita ({}): {}", q, exc)
                continue
            soup = BeautifulSoup(xml, "lxml-xml")
            items = soup.find_all("item")
            if not items:
                # fallback parser html
                soup = BeautifulSoup(xml, "lxml")
                items = soup.find_all("item")
            for item in items:
                title = (item.title.get_text(strip=True) if item.title else "") or ""
                link = (item.link.get_text(strip=True) if item.link else "") or ""
                pub = item.pubDate.get_text(strip=True) if item.pubDate else ""
                desc = item.description.get_text(" ", strip=True) if item.description else ""
                blob = f"{title} {desc}"
                ok, tag = is_energy_related(text=blob)
                if not ok:
                    continue
                # lookback soft: se data parsabile e troppo vecchia, skip
                if pub:
                    try:
                        # RFC 2822-ish
                        from email.utils import parsedate_to_datetime

                        dt = parsedate_to_datetime(pub).date()
                        if dt < cutoff:
                            continue
                    except Exception:  # noqa: BLE001
                        pass

                names = extract_company_names(blob)
                if not names:
                    # fallback: titolo troncato
                    names = [re.sub(r"\s+", " ", title)[:120]]
                for name in names[:2]:
                    key = name.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    piva, cf = extract_piva_cf(blob)
                    stato = "in liquidazione"
                    low = blob.lower()
                    if "concordato" in low:
                        stato = "concordato preventivo"
                    elif "liquidazione giudiziale" in low or "fallimento" in low:
                        stato = "liquidazione giudiziale"
                    elif "amministrazione straordinaria" in low:
                        stato = "amministrazione straordinaria"
                    companies.append(
                        Company(
                            denominazione=name,
                            piva=piva,
                            cf=cf,
                            stato=stato,
                            fonte="gazzettaufficiale.it",
                            url=link or None,
                            note=f"{title[:200]}; {tag}; lookback={lookback}m; ricerca via RSS (GU full-text spesso gated)",
                        )
                    )

        # tentativo HTML diretto (può essere bloccato — non crashare)
        try:
            self._try_direct_gu(companies, seen)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "GU HTML diretto non disponibile (WAF/login?). Usare RSS. Dettaglio: {}",
                exc,
            )

        return companies

    def _try_direct_gu(self, companies: list[Company], seen: set[str]) -> None:
        # endpoint storico; se 247 byte "Rejected" interrompe subito
        test = self.get_cached_text(
            "https://www.gazzettaufficiale.it/ricerca/predefinita/2/?reset=true"
        )
        if "Request Rejected" in test or len(test) < 500:
            logger.error(
                "Fonte gu: ricerca HTML GU bloccata (WAF/login). "
                "Aggiornare a sessione autenticata o altro endpoint pubblico."
            )
            return


def main() -> None:
    src = GazzettaUfficialeSource()
    rows = src.run()
    for r in rows[:10]:
        print(f"{r.denominazione} | {r.stato} | {r.note[:120]}")


if __name__ == "__main__":
    main()
