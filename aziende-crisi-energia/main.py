"""Orchestratore pipeline aziende energia in crisi."""
from __future__ import annotations

import argparse
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from loguru import logger

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config
from anagrafica import enrich_company_from_anagrafica, load_anagrafica
from dedup import dedup_companies, sort_companies
from export import write_outputs
from matching import is_energy_related
from models import Company, normalize_denominazione
from anagrafica import load_anagrafica
from sources.astalegale import AstaLegaleSource
from sources.fallimenti_news import FallimentiNewsSource
from sources.gazzetta_ufficiale import GazzettaUfficialeSource
from sources.mimit_tavoli import MimitTavoliSource, _extract_company_lines
from sources.openapi_it import OpenApiItSource, resolve_piva_by_name
from sources.pvp_giustizia import PvpGiustiziaSource
from sources.unioncamere_cnc import UnioncamereCncSource


SOURCE_MAP = {
    "pvp": PvpGiustiziaSource,
    "gu": GazzettaUfficialeSource,
    "mimit": MimitTavoliSource,
    "openapi": OpenApiItSource,
    "astalegale": AstaLegaleSource,
    "news": FallimentiNewsSource,
    "cnc": UnioncamereCncSource,
}


def setup_logging() -> None:
    logger.remove()
    logger.add(sys.stderr, level="INFO", format="{time:HH:mm:ss} | {level} | {message}")
    logger.add(
        config.OUTPUT_DIR / "run.log",
        level="DEBUG",
        encoding="utf-8",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {message}",
    )


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Pipeline aziende energia in crisi (IT)")
    p.add_argument(
        "--sources",
        default=",".join(SOURCE_MAP.keys()),
        help="Lista moduli separati da virgola (pvp,gu,mimit,openapi,astalegale,news,cnc)",
    )
    p.add_argument("--lookback-months", type=int, default=config.LOOKBACK_MONTHS)
    p.add_argument("--no-cache", action="store_true")
    p.add_argument(
        "--ateco-only",
        action="store_true",
        help="Esclude match solo-keyword (richiede ATECO o anagrafica)",
    )
    p.add_argument(
        "--skip-anagrafica",
        action="store_true",
        help="Non usare aziende-energetiche-it.txt per enrichment/MIMIT",
    )
    return p.parse_args()


def _mimit_with_anagrafica(use_cache: bool, skip_anagrafica: bool) -> list[Company]:
    """MIMIT: keyword energia OPPURE presente in anagrafica ARERA locale."""
    base = MimitTavoliSource(use_cache=use_cache)
    # prendi tutte le righe grezze e filtra
    results: list[Company] = []
    anag_ok = (not skip_anagrafica) and config.ANAGRAFICA_LOCALE_PATH.exists()
    for url, stato in [
        (config.MIMIT_ATTIVI_URL, "tavolo di crisi MIMIT"),
        (config.MIMIT_MONITORAGGIO_URL, "tavolo di crisi MIMIT (monitoraggio)"),
    ]:
        try:
            html = base.get_cached_text(url)
        except Exception as exc:  # noqa: BLE001
            logger.warning("MIMIT {}: {}", url, exc)
            continue
        lines = _extract_company_lines(html)
        anag_index: dict[str, object] = {}
        if anag_ok:
            for row in load_anagrafica(str(config.ANAGRAFICA_LOCALE_PATH)):
                anag_index[normalize_denominazione(row.denominazione)] = row
        for line in lines:
            low = line.lower()
            ok, tag = is_energy_related(text=line)
            hint_hit = any(h in low for h in config.MIMIT_ENERGY_NAME_HINTS)
            anag_hit = None
            if anag_ok:
                key = normalize_denominazione(line.split("(")[0].strip())
                anag_hit = anag_index.get(key)
            # Inclusione: keyword OR hint noto OR intersezione esatta anagrafica energia
            if not ok and not hint_hit and not anag_hit:
                continue
            note_parts = []
            if tag:
                note_parts.append(tag)
            if hint_hit and not tag:
                note_parts.append("match=mimit_energy_hint")
            if anag_hit:
                note_parts.append("anagrafica_energia=1")
            if not ok and not hint_hit and anag_hit:
                note_parts.append("match=anagrafica_energia")
            note_parts.append("elenco pubblico MIMIT")
            results.append(
                Company(
                    denominazione=line,
                    piva=anag_hit.piva if anag_hit else None,
                    provincia=anag_hit.provincia if anag_hit else None,
                    stato=stato,
                    fonte="mimit.gov.it",
                    url=url,
                    note="; ".join(note_parts),
                )
            )
    logger.info("Fonte mimit (con anagrafica): {} record", len(results))
    return results


def run_source(name: str, use_cache: bool, lookback: int, skip_anagrafica: bool) -> list[Company]:
    if name == "mimit":
        return _mimit_with_anagrafica(use_cache, skip_anagrafica)
    cls = SOURCE_MAP[name]
    src = cls(use_cache=use_cache)
    if name == "gu":
        src.lookback_months = lookback  # type: ignore[attr-defined]
    return src.run()


def filter_ateco_only(companies: list[Company], skip_anagrafica: bool) -> list[Company]:
    out: list[Company] = []
    for c in companies:
        ok, _ = is_energy_related(ateco=c.ateco, text=None, ateco_only=True)
        if ok:
            out.append(c)
            continue
        if not skip_anagrafica and "anagrafica_energia=1" in (c.note or ""):
            out.append(c)
            continue
        # scarta keyword-only
    return out


def main() -> int:
    args = parse_args()
    setup_logging()
    config.LOOKBACK_MONTHS = args.lookback_months
    use_cache = not args.no_cache

    selected = [s.strip() for s in args.sources.split(",") if s.strip()]
    unknown = [s for s in selected if s not in SOURCE_MAP]
    if unknown:
        logger.error("Sorgenti sconosciute: {}", unknown)
        return 2

    if not args.skip_anagrafica:
        load_anagrafica(str(config.ANAGRAFICA_LOCALE_PATH))

    logger.info("Avvio pipeline — sources={} cache={} lookback={}m", selected, use_cache, args.lookback_months)

    all_rows: list[Company] = []
    with ThreadPoolExecutor(max_workers=config.MAX_PARALLEL_SOURCES) as pool:
        futs = {
            pool.submit(run_source, name, use_cache, args.lookback_months, args.skip_anagrafica): name
            for name in selected
        }
        for fut in as_completed(futs):
            name = futs[fut]
            try:
                rows = fut.result()
                all_rows.extend(rows)
                logger.info("Completato {}: {} record", name, len(rows))
            except Exception as exc:  # noqa: BLE001
                logger.exception("Modulo {} eccezione non gestita: {}", name, exc)

    # enrichment anagrafica
    if not args.skip_anagrafica and config.ANAGRAFICA_LOCALE_PATH.exists():
        for c in all_rows:
            enrich_company_from_anagrafica(c, str(config.ANAGRAFICA_LOCALE_PATH))

    merged = dedup_companies(all_rows)

    # resolve P.IVA via openapi se possibile
    if config.OPENAPI_IT_KEY:
        resolver = OpenApiItSource(use_cache=use_cache)
        for c in merged:
            if not c.piva and c.denominazione:
                piva = resolve_piva_by_name(resolver, c.denominazione)
                if piva:
                    c.piva = piva
                    c.note = (
                        f"{c.note}; piva_da_openapi" if c.note else "piva_da_openapi"
                    )

    if args.ateco_only:
        merged = filter_ateco_only(merged, args.skip_anagrafica)

    merged = sort_companies(merged)
    paths = write_outputs(merged, config.OUTPUT_DIR)

    from collections import Counter

    by_stato = Counter(c.stato for c in merged)
    by_fonte = Counter()
    no_piva = sum(1 for c in merged if not c.piva)
    for c in merged:
        for f in (c.fonte or "").split("|"):
            if f:
                by_fonte[f.strip()] += 1

    logger.info("=== SUMMARY ===")
    logger.info("Totale: {}", len(merged))
    logger.info("Per stato: {}", dict(by_stato))
    logger.info("Per fonte: {}", dict(by_fonte))
    logger.info("Senza P.IVA: {}", no_piva)
    logger.info("Output: {}", paths)

    print(f"\nTotale aziende: {len(merged)}")
    print(f"Per stato: {dict(by_stato)}")
    print(f"Per fonte: {dict(by_fonte)}")
    print(f"Senza P.IVA: {no_piva}")
    print(f"TXT: {paths['txt']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
