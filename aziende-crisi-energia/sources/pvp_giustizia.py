"""Modulo 1 — Portale Vendite Pubbliche (pvp.giustizia.it)."""
from __future__ import annotations

from typing import Any

from loguru import logger

import config
from matching import is_energy_related, is_non_energy_ateco
from models import Company, extract_company_names, extract_piva_cf
from sources.base import Source

PVP_DETAIL = "https://pvp.giustizia.it/ve-3f723b85-986a1b71/ve-ms/vendite/{id}"

PVP_CATEGORIES = [
    "CESSIONE_AFFITTO",
    "QUOTA_SOCIETARIA",
    "AZIONI_TITOLI",
    "IMMOBILE_INDUSTRIALE",
    "MACCHINARI_UT_MAT_PRIME",
    "INFORMATICA_E_ELET",
]


def _map_rito_to_stato(desc_rito: str | None, cod_registro: str | None) -> str:
    blob = f"{desc_rito or ''} {cod_registro or ''}".lower()
    if "falliment" in blob or "liquidazione giudiziale" in blob:
        return "liquidazione giudiziale"
    if "concordato" in blob:
        return "concordato preventivo"
    if "amministrazione straordinaria" in blob:
        return "amministrazione straordinaria"
    if "coatta" in blob:
        return "liquidazione coatta"
    if "esecuzion" in blob:
        return "esecuzione giudiziaria (PVP)"
    return desc_rito or "vendita giudiziaria PVP"


def _detail_blob(detail: dict[str, Any]) -> str:
    parts: list[str] = []
    for bene in detail.get("beni") or []:
        parts.append(str(bene.get("descrizione") or ""))
        parts.append(str(bene.get("codDescAteco") or ""))
    for sog in detail.get("soggetti") or []:
        parts.append(str(sog.get("nome") or ""))
        parts.append(str(sog.get("cognome") or ""))
    for allg in detail.get("allegati") or []:
        parts.append(str(allg.get("nomeFile") or ""))
    return " ".join(parts)


class PvpGiustiziaSource(Source):
    name = "pvp"
    expected_min_results = 0

    def fetch(self) -> list[Company]:
        companies: list[Company] = []
        seen_ids: set[int] = set()
        for categoria in PVP_CATEGORIES:
            self._scan_categoria(categoria, companies, seen_ids)
        return companies

    def _scan_categoria(
        self,
        categoria: str,
        companies: list[Company],
        seen_ids: set[int],
    ) -> None:
        max_pages = min(config.PVP_MAX_PAGES, 30)
        for page in range(max_pages):
            url = f"{config.PVP_SEARCH_URL}&page={page}&size=20"
            payload = {
                "filtroAnnunci": 0,
                "ricercaLibera": None,
                "categoriaLotto": categoria,
            }
            data = self.get_cached_json(url, method="POST", json=payload)
            body = (data or {}).get("body") or {}
            content = body.get("content") or []
            total = body.get("totalElements") or 0
            if page == 0:
                logger.info("PVP categoria {}: {} annunci", categoria, total)
            if not content:
                break

            for item in content:
                aid = item.get("id")
                if aid in seen_ids:
                    continue
                seen_ids.add(aid)
                desc = item.get("descLotto") or ""
                cat = " ".join(item.get("categoriaBene") or [])
                blob_list = f"{desc} {cat} {categoria}"
                ok, match_tag = is_energy_related(text=blob_list)

                need_detail = categoria in {
                    "CESSIONE_AFFITTO",
                    "QUOTA_SOCIETARIA",
                    "AZIONI_TITOLI",
                } or ok
                detail = self._safe_detail(aid) if need_detail else None
                if detail and not ok:
                    ok, match_tag = is_energy_related(text=_detail_blob(detail))
                if not ok:
                    continue
                if detail:
                    for bene in detail.get("beni") or []:
                        code = bene.get("codDescAteco") or bene.get("codiciAteco")
                        if is_non_energy_ateco(str(code) if code is not None else None):
                            ok = False
                            break
                if not ok:
                    continue

                company = self._to_company(item, detail, match_tag, categoria)
                if company is not None:
                    companies.append(company)

            if body.get("last") or page + 1 >= (body.get("totalPages") or 1):
                break

    def _safe_detail(self, aid: int) -> dict[str, Any] | None:
        try:
            data = self.get_cached_json(PVP_DETAIL.format(id=aid))
            return (data or {}).get("body")
        except Exception as exc:  # noqa: BLE001
            logger.debug("PVP dettaglio {} non disponibile: {}", aid, exc)
            return None

    def _to_company(
        self,
        item: dict[str, Any],
        detail: dict[str, Any] | None,
        match_tag: str,
        categoria: str,
    ) -> Company | None:
        desc = (item.get("descLotto") or "")[:200]
        tribunale = item.get("tribunale") or ""
        procedura_num = str(item.get("procedura") or "")
        provincia = None
        indirizzo = item.get("indirizzo") or {}
        if isinstance(indirizzo, dict):
            provincia = indirizzo.get("provincia") or indirizzo.get("descProvincia")

        stato = "vendita giudiziaria PVP"
        denominazione = ""
        ateco = None
        piva = None
        cf = None
        note_bits = [tribunale, f"n.proc={procedura_num}", f"cat={categoria}", desc]

        if detail:
            proc = detail.get("procedura") or {}
            stato = _map_rito_to_stato(proc.get("descTipoRito"), proc.get("descTipoRegistro"))
            anno = proc.get("numeAnnoRg")
            rg = proc.get("numeRg")
            if anno and rg:
                note_bits.append(f"RG {rg}/{anno}")
            for bene in detail.get("beni") or []:
                if bene.get("codDescAteco"):
                    ateco = str(bene["codDescAteco"])
                elif bene.get("codiciAteco"):
                    ateco = str(bene["codiciAteco"])
                bdesc = bene.get("descrizione") or ""
                names = extract_company_names(bdesc)
                if names and not denominazione:
                    denominazione = names[0]
            for sog in detail.get("soggetti") or []:
                ruolo = (sog.get("ruolo") or "").upper()
                if ruolo in {"DEBITORE", "FALLITO", "ESECUTATO", "IMPRESA"}:
                    nome = " ".join(
                        x for x in [sog.get("nome"), sog.get("cognome")] if x
                    ).strip()
                    if nome:
                        denominazione = nome
                    if sog.get("cf"):
                        cf = sog["cf"]
            for allg in detail.get("allegati") or []:
                fname = allg.get("nomeFile") or ""
                names = extract_company_names(fname.replace("_", " ").replace("-", " "))
                if names and not denominazione:
                    denominazione = names[0]

        if not denominazione:
            names = extract_company_names(desc)
            denominazione = (
                names[0] if names else f"Procedura {procedura_num} — {tribunale}".strip(" —")
            )

        text_for_ids = desc + " " + " ".join(note_bits)
        p2, c2 = extract_piva_cf(text_for_ids)
        piva = piva or p2
        cf = cf or c2

        url = config.PVP_DETAIL_URL_TMPL.format(id=item.get("id"))
        note = "; ".join(x for x in note_bits if x)
        if match_tag:
            note = f"{note}; {match_tag}"
        note = f"{note}; {url}"

        return Company(
            denominazione=denominazione,
            piva=piva,
            cf=cf,
            ateco=ateco,
            provincia=provincia,
            stato=stato,
            fonte="pvp.giustizia.it",
            url=url,
            note=note[:500],
        )


def main() -> None:
    src = PvpGiustiziaSource()
    rows = src.run()
    for r in rows[:10]:
        print(f"{r.denominazione} | {r.stato} | {r.note[:120]}")


if __name__ == "__main__":
    main()
