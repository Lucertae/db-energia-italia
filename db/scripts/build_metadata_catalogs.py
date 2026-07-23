#!/usr/bin/env python3
"""Build catalog.csv + METADATI.txt (AUTO-STATS) for every db/*-italia package.

One catalog row = one logical dataset (folder family), not every file.
Run: python db/scripts/build_metadata_catalogs.py
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import pandas as pd

DB = Path(__file__).resolve().parents[1]
TODAY = date.today().isoformat()
CATALOG_COLS = [
    "package",
    "dataset",
    "path",
    "description",
    "geo",
    "time_start",
    "time_end",
    "granularity",
    "rows_or_records",
    "n_files",
    "bytes",
    "unit_notes",
    "source",
    "license",
    "status",
]

SKIP_PARTS = {".git", "_tmp", "node_modules", "__pycache__", ".venv"}
YEAR_RE = re.compile(r"(?:19|20)\d{2}")


@dataclass
class DatasetDef:
    dataset: str
    path: str  # relative to package root
    description: str
    geo: str = "IT"
    granularity: str = ""
    unit_notes: str = ""
    source: str = ""
    license: str = ""
    status: str = "ok"
    # optional preferred merge/key files for row/year sampling (relative to package)
    sample_files: list[str] = field(default_factory=list)
    time_start: str = ""
    time_end: str = ""


@dataclass
class PackageDef:
    name: str
    title: str
    description: str
    refresh: str
    license_note: str
    gaps: str = ""
    datasets: list[DatasetDef] = field(default_factory=list)


def should_skip(p: Path) -> bool:
    return any(part in SKIP_PARTS for part in p.parts)


def measure_path(root: Path) -> tuple[int, int]:
    """Return (n_files, total_bytes) under root."""
    if not root.exists():
        return 0, 0
    if root.is_file():
        return 1, root.stat().st_size
    n, b = 0, 0
    for f in root.rglob("*"):
        if not f.is_file() or should_skip(f):
            continue
        n += 1
        try:
            b += f.stat().st_size
        except OSError:
            pass
    return n, b


def count_csv_rows(path: Path, max_bytes: int = 80_000_000) -> int | None:
    if not path.exists() or not path.is_file():
        return None
    if path.stat().st_size > max_bytes:
        # approximate via line count without full parse
        try:
            with open(path, "rb") as fh:
                return max(0, sum(1 for _ in fh) - 1)
        except OSError:
            return None
    try:
        return max(0, sum(1 for _ in open(path, encoding="utf-8", errors="replace")) - 1)
    except OSError:
        return None


def infer_years_from_csv(path: Path, max_bytes: int = 40_000_000) -> tuple[str, str]:
    if not path.exists():
        return "", ""
    years: list[int] = []
    years.extend(int(y) for y in YEAR_RE.findall(path.name) if 1990 <= int(y) <= 2030)

    def absorb(df: pd.DataFrame) -> None:
        for col in df.columns:
            cl = str(col).lower()
            if cl not in ("year", "anno", "time_period", "date", "datetime", "time", "valid_from", "valid_to"):
                # also TIME_PERIOD style
                if "time" not in cl and "date" not in cl and "year" not in cl and "anno" not in cl:
                    continue
            s = df[col].astype(str)
            for v in s:
                for y in YEAR_RE.findall(v):
                    yi = int(y)
                    if 1990 <= yi <= 2035:
                        years.append(yi)
            nums = pd.to_numeric(df[col], errors="coerce").dropna()
            for v in nums:
                yi = int(v)
                if 1990 <= yi <= 2035:
                    years.append(yi)

    try:
        if path.stat().st_size <= max_bytes:
            absorb(pd.read_csv(path, low_memory=False))
        else:
            absorb(pd.read_csv(path, nrows=3000, low_memory=False))
            # tail sample for end year
            with open(path, "rb") as fh:
                fh.seek(0, 2)
                size = fh.tell()
                fh.seek(max(0, size - 120_000))
                tail = fh.read().decode("utf-8", "replace")
            # skip partial first line
            lines = tail.splitlines()
            if len(lines) > 2:
                header = open(path, encoding="utf-8", errors="replace").readline()
                blob = header + "\n".join(lines[-80:])
                from io import StringIO

                absorb(pd.read_csv(StringIO(blob), low_memory=False))
    except Exception:
        pass
    if not years:
        return "", ""
    return str(min(years)), str(max(years))


def infer_years_from_names(files: list[Path]) -> tuple[str, str]:
    years = []
    for f in files[:500]:
        years.extend(int(y) for y in YEAR_RE.findall(f.name) if 1990 <= int(y) <= 2030)
    if not years:
        return "", ""
    return str(min(years)), str(max(years))


def collect_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    if root.is_file():
        return [root]
    out = []
    for f in root.rglob("*"):
        if f.is_file() and not should_skip(f):
            out.append(f)
    return out


def fmt_bytes(n: int) -> str:
    if n >= 1_000_000_000:
        return f"{n/1e9:.2f} GB"
    if n >= 1_000_000:
        return f"{n/1e6:.1f} MB"
    if n >= 1000:
        return f"{n/1e3:.1f} KB"
    return f"{n} B"


PACKAGES: list[PackageDef] = [
    PackageDef(
        name="consumi-italia",
        title="Consumi energetici Italia",
        description=(
            "Consumi e bilanci energetici aggregati: ARERA (clienti), Terna (API + bilanci), "
            "Eurostat (bilanci/prezzi/trade), MASE/SISEN, ISPRA, World Bank, CO₂. "
            "Nessun nominativo azienda/POD."
        ),
        refresh=(
            "python db/consumi-italia/scripts/harvest_all.py\n"
            "python db/consumi-italia/scripts/harvest_terna_api.py\n"
            "python db/scripts/fill_remaining_bulk.py"
        ),
        license_note="ARERA/Terna termini open data; Eurostat; ISPRA; WB; OWID.",
        gaps="Terna total-load 2021–22 può fallire per Developer Over Rate.",
        datasets=[
            DatasetDef("arera_domestici", "sources/arera/domestici", "Prelievi medi clienti domestici (regione/provincia)", "IT regioni/province", "annuale", "kWh / clienti", "ARERA", "open data ARERA"),
            DatasetDef("arera_non_domestici_ateco", "sources/arera/non_domestici_ateco", "Clienti non domestici BT per ATECO", "IT", "annuale", "clienti / kWh", "ARERA", "open data ARERA"),
            DatasetDef("terna_bilanci", "sources/terna/bilanci", "Consumi elettrici finali per settore 1990–2024", "IT", "annuale", "GWh", "ISPRA/Terna", "open"),
            DatasetDef("terna_total_load", "sources/terna/total_load", "Carico elettrico totale (API Terna)", "IT", "orario/sub-orario", "MW", "Terna API", "Terna Developer"),
            DatasetDef("terna_imcei", "sources/terna/imcei", "Indice mensile consumi energivori (IMCEI)", "IT", "mensile", "indice", "Terna API", "Terna Developer"),
            DatasetDef("terna_industry", "sources/terna/industry_sector", "Consumi industria provincia/ATECO", "IT province", "mensile", "GWh", "Terna API", "Terna Developer"),
            DatasetDef("terna_services", "sources/terna/services_sector", "Consumi servizi (incl. PA)", "IT", "mensile", "GWh", "Terna API", "Terna Developer"),
            DatasetDef("terna_by_sector", "sources/terna/electrical_energy_by_sector", "Energia elettrica per settore", "IT", "mensile", "GWh", "Terna API", "Terna Developer"),
            DatasetDef("terna_by_type", "sources/terna/electrical_energy_by_type", "Energia elettrica per tipologia", "IT", "mensile", "GWh", "Terna API", "Terna Developer"),
            DatasetDef("terna_capacity", "sources/terna/installed_capacity", "Capacità installata", "IT", "mensile", "MW", "Terna API", "Terna Developer"),
            DatasetDef("terna_res_capacity", "sources/terna/renewable_source_capacity", "Capacità rinnovabili per fonte", "IT", "mensile", "MW", "Terna API", "Terna Developer"),
            DatasetDef("eurostat_energy", "sources/eurostat", "Bilanci, prezzi, trade, stock, SDG energia (geo=IT)", "IT", "annuale/mensile", "mix Eurostat", "Eurostat", "Eurostat"),
            DatasetDef("mase_sisen", "sources/mase", "Relazione energetica, SISEN prezzi/carburanti/BEN/gas", "IT", "settimanale/mensile/annuale", "€/l, tep, Sm3", "MASE/SISEN", "open"),
            DatasetDef("ispra", "sources/ispra", "FE, indicatori energia, report GHG", "IT", "annuale", "tCO2eq / FE", "ISPRA", "open"),
            DatasetDef("worldbank_energy", "sources/worldbank", "Indicatori energetici WB Italia", "IT", "annuale", "mix", "World Bank", "CC-BY 4.0"),
            DatasetDef("edgar_co2", "sources/edgar", "Estratto CO₂ EDGAR/OWID", "IT", "annuale", "tCO2", "OWID/EDGAR", "CC-BY"),
            DatasetDef("ghg", "sources/ghg", "Materiali GHG EEA/correlati", "IT/EU", "annuale", "", "EEA", "open"),
            DatasetDef("istat_admin", "sources/istat", "Confini/elenco comuni (supporto geografico)", "IT", "statico", "", "ISTAT", "open"),
        ],
    ),
    PackageDef(
        name="terna-italia",
        title="Terna Italia (vista dedicata)",
        description=(
            "Pacchetto dedicato alle serie Terna: load, IMCEI, settori, capacità. "
            "I path sotto sources/ puntano (symlink) ai dati in consumi-italia/sources/terna.\n\n"
            "INCOMPLETO rispetto allo scope pieno Terna: mancano ancora i PDF e i dati "
            "semantici su incidenti di rete, stato della rete e avanzamento / sviluppo "
            "della rete (piani, cantieri, opere). Da aggiungere in cartelle dedicate "
            "(es. sources/pdf/, sources/incidenti/, sources/stato_rete/, sources/avanzamento_rete/)."
        ),
        refresh="python db/terna-italia/scripts/harvest_terna_api.py",
        license_note="Terna Developer Portal / open data collegati.",
        gaps=(
            "DA FARE — PDF e dati semantici Terna ancora assenti:\n"
            "  • incidenti di rete (report/eventi, cause, impatto)\n"
            "  • stato della rete (asset, congestioni, indisponibilità, manutenzioni)\n"
            "  • avanzamento / sviluppo rete (piani di sviluppo, cantieri, opere, milestone)\n"
            "Inoltre: total-load 2021–22 può fallire per Developer Over Rate (403)."
        ),
        datasets=[
            DatasetDef("bilanci", "sources/bilanci", "Bilanci consumi elettrici per settore", "IT", "annuale", "GWh", "ISPRA/Terna", "open"),
            DatasetDef("total_load", "sources/total_load", "Carico totale", "IT", "orario", "MW", "Terna API", "Terna Developer"),
            DatasetDef("imcei", "sources/imcei", "IMCEI", "IT", "mensile", "indice", "Terna API", "Terna Developer"),
            DatasetDef("industry_sector", "sources/industry_sector", "Industria provincia/ATECO", "IT", "mensile", "GWh", "Terna API", "Terna Developer"),
            DatasetDef("services_sector", "sources/services_sector", "Servizi", "IT", "mensile", "GWh", "Terna API", "Terna Developer"),
            DatasetDef("by_sector", "sources/electrical_energy_by_sector", "Per settore", "IT", "mensile", "GWh", "Terna API", "Terna Developer"),
            DatasetDef("by_type", "sources/electrical_energy_by_type", "Per tipologia", "IT", "mensile", "GWh", "Terna API", "Terna Developer"),
            DatasetDef("in_italy", "sources/electrical_energy_in_italy", "Serie nazionali", "IT", "mensile", "GWh", "Terna API", "Terna Developer"),
            DatasetDef("installed_capacity", "sources/installed_capacity", "Capacità installata", "IT", "mensile", "MW", "Terna API", "Terna Developer"),
            DatasetDef("res_capacity", "sources/renewable_source_capacity", "Capacità FER", "IT", "mensile", "MW", "Terna API", "Terna Developer"),
            DatasetDef(
                "pdf_documenti",
                "sources/pdf",
                "PDF Terna (report, piani, comunicati) — DA POPOLARE",
                "IT",
                "documentale",
                "PDF",
                "Terna",
                "termini Terna",
                status="planned",
            ),
            DatasetDef(
                "incidenti_rete",
                "sources/incidenti",
                "Incidenti / eventi di rete (dati semantici) — DA POPOLARE",
                "IT",
                "evento",
                "eventi, MW, durata",
                "Terna",
                "termini Terna",
                status="planned",
            ),
            DatasetDef(
                "stato_rete",
                "sources/stato_rete",
                "Stato della rete (asset, congestioni, indisponibilità) — DA POPOLARE",
                "IT",
                "snapshot/serie",
                "stato asset / MW",
                "Terna",
                "termini Terna",
                status="planned",
            ),
            DatasetDef(
                "avanzamento_rete",
                "sources/avanzamento_rete",
                "Avanzamento / sviluppo rete (piani, cantieri, opere) — DA POPOLARE",
                "IT",
                "progetto/milestone",
                "opere, stato avanzamento",
                "Terna",
                "termini Terna",
                status="planned",
            ),
        ],
    ),
    PackageDef(
        name="mercati-italia",
        title="Mercati energia Italia",
        description=(
            "Mercati elettrici e gas: GME MGP, ENTSOG/SNAM, GIE AGSI/ALSI, GSE incentivi, "
            "Ember, EUA EEX, snapshot prezzi live."
        ),
        refresh=(
            "python db/mercati-italia/scripts/harvest_all.py\n"
            "python db/scripts/harvest_prezzi_live.py\n"
            "python db/scripts/harvest_gie_agsi.py"
        ),
        license_note="GME, GIE, ENTSOG, GSE, Ember, EEX termini rispettivi.",
        gaps="GME MI/MSD/MB e Anno2007 spesso incompleti; Atlaimpianti solo UI.",
        datasets=[
            DatasetDef("gme_mgp", "sources/gme", "Esiti MGP e altri mercati GME (ZIP/CSV storici)", "IT zone", "orario/giornaliero", "€/MWh", "GME", "GME"),
            DatasetDef("prezzi_live", "sources/prezzi_live", "Snapshot prezzi live (DA zone, Ember, ARERA, SISEN, EUA)", "IT", "rolling ~90g / indici", "€/MWh, €/l", "multi", "open"),
            DatasetDef("agsi", "sources/agsi", "Stoccaggio gas Italia (GIE AGSI) paese + entities", "IT", "giornaliero", "TWh / %", "GIE AGSI", "GIE"),
            DatasetDef("alsi", "sources/alsi", "Terminali GNL Italia (GIE ALSI)", "IT", "giornaliero", "GWh", "GIE ALSI", "GIE"),
            DatasetDef("entsog_snam", "sources/entsog_snam", "Flussi gas fisici SNAM/ENTSOG", "IT punti", "giornaliero/mensile", "kWh/d", "ENTSOG", "ENTSOG"),
            DatasetDef("snam_opendata", "sources/snam_opendata", "Materiali open data SNAM", "IT", "misto", "", "SNAM", "open"),
            DatasetDef("gse", "sources/gse", "Incentivi/certificati GSE open data", "IT", "annuale/misto", "", "GSE", "open"),
            DatasetDef("ember", "sources/ember", "Serie mercato elettrico Ember", "IT", "giornaliero/orario", "€/MWh, MW", "Ember", "CC-BY"),
            DatasetDef("ets_eua", "sources/ets_eua", "Aste EUA EEX + contesto carbon OWID", "EU/IT", "asta/annuale", "€/t", "EEX/OWID", "open"),
        ],
    ),
    PackageDef(
        name="entsoe-italia",
        title="ENTSO-E Transparency Italia",
        description=(
            "Serie operative Transparency Platform: carico, generazione, prezzi DA, "
            "bilanciamento, scambi cross-border — paese IT e 7 zone di mercato."
        ),
        refresh="python db/entsoe-italia/scripts/harvest_all_italia.py",
        license_note="ENTSO-E Transparency (uso con API key).",
        gaps="Alcune serie balancing/intraday vuote per IT; prezzi DA sulle zone non sul codice paese.",
        datasets=[
            DatasetDef("IT_national", "data/IT", "Serie nazionali (load, gen, prices, balancing, …)", "IT", "orario/quarter", "MW, €/MWh", "ENTSO-E", "ENTSO-E"),
            DatasetDef("IT_North", "data/IT-North", "Zona Nord", "IT-North", "orario", "MW, €/MWh", "ENTSO-E", "ENTSO-E"),
            DatasetDef("IT_Centre_North", "data/IT-Centre-North", "Zona Centro-Nord", "IT-Centre-North", "orario", "MW, €/MWh", "ENTSO-E", "ENTSO-E"),
            DatasetDef("IT_Centre_South", "data/IT-Centre-South", "Zona Centro-Sud", "IT-Centre-South", "orario", "MW, €/MWh", "ENTSO-E", "ENTSO-E"),
            DatasetDef("IT_South", "data/IT-South", "Zona Sud", "IT-South", "orario", "MW, €/MWh", "ENTSO-E", "ENTSO-E"),
            DatasetDef("IT_Sicily", "data/IT-Sicily", "Zona Sicilia", "IT-Sicily", "orario", "MW, €/MWh", "ENTSO-E", "ENTSO-E"),
            DatasetDef("IT_Sardinia", "data/IT-Sardinia", "Zona Sardegna", "IT-Sardinia", "orario", "MW, €/MWh", "ENTSO-E", "ENTSO-E"),
            DatasetDef("IT_Calabria", "data/IT-Calabria", "Zona Calabria", "IT-Calabria", "orario", "MW, €/MWh", "ENTSO-E", "ENTSO-E"),
            DatasetDef("crossborder", "data/crossborder", "Scambi/NTC/outage frontiere IT", "IT borders", "orario", "MW", "ENTSO-E", "ENTSO-E"),
        ],
    ),
    PackageDef(
        name="meteo-italia",
        title="Meteo Italia",
        description=(
            "Driver meteo per domanda/FER: Open-Meteo (città/zone, orario+daily con pioggia/neve), "
            "alternativa NASA POWER (griglia nazionale + città + zone) e stazioni Meteostat."
        ),
        refresh=(
            "python db/meteo-italia/scripts/harvest_open_meteo.py\n"
            "python db/meteo-italia/scripts/harvest_meteo_alt.py"
        ),
        license_note="Open-Meteo/ERA5; NASA POWER; Meteostat.",
        gaps="Open-Meteo spesso 429: usare NASA POWER/Meteostat. Griglia Open-Meteo incompleta.",
        datasets=[
            DatasetDef(
                "open_meteo_cities_hourly",
                "sources/meteo",
                "12 città — orario ricco (precip/rain/snow/vento/solare)",
                "12 città IT",
                "orario",
                "°C, mm, cm, km/h, W/m2",
                "Open-Meteo",
                "Open-Meteo/ERA5",
                sample_files=["sources/meteo/italy_cities_hourly_2015_2026.csv"],
                time_start="2015",
                time_end="2026",
            ),
            DatasetDef(
                "open_meteo_cities_daily",
                "sources/meteo_daily",
                "12 città — giornaliero (sum precip/rain/snow)",
                "12 città IT",
                "giornaliero",
                "mm, cm, °C",
                "Open-Meteo",
                "Open-Meteo/ERA5",
                sample_files=["sources/meteo_daily/italy_cities_daily_2015_2026.csv"],
                time_start="2015",
                time_end="2026",
            ),
            DatasetDef("open_meteo_zones_hourly", "sources/open_meteo_zones", "7 zone ENTSO — orario", "7 zone", "orario", "come città", "Open-Meteo", "Open-Meteo/ERA5", time_start="2015", time_end="2026"),
            DatasetDef("open_meteo_zones_daily", "sources/open_meteo_zones_daily", "7 zone ENTSO — giornaliero", "7 zone", "giornaliero", "mm, °C", "Open-Meteo", "Open-Meteo/ERA5", time_start="2015", time_end="2026"),
            DatasetDef(
                "nasa_power_grid",
                "sources/nasa_power_grid",
                "Griglia nazionale ~1° daily (precip/temp/vento/solare)",
                "IT griglia ~81 punti",
                "giornaliero",
                "mm, °C, m/s, kWh/m2/d",
                "NASA POWER",
                "NASA POWER",
                sample_files=["sources/nasa_power_grid/italy_grid_daily_2015_present.csv"],
                time_start="2015",
                time_end="2026",
            ),
            DatasetDef("nasa_power_cities", "sources/nasa_power_cities", "12 città daily NASA POWER", "12 città", "giornaliero", "mm, °C, …", "NASA POWER", "NASA POWER", sample_files=["sources/nasa_power_cities/italy_cities_daily_2015_present.csv"], time_start="2015", time_end="2026"),
            DatasetDef("nasa_power_zones", "sources/nasa_power_zones", "7 zone ENTSO daily NASA POWER", "7 zone", "giornaliero", "mm, °C, …", "NASA POWER", "NASA POWER", sample_files=["sources/nasa_power_zones/italy_zones_daily_2015_present.csv"], time_start="2015", time_end="2026"),
            DatasetDef(
                "meteostat_stations",
                "sources/meteostat_stations",
                "Stazioni osservative IT daily (~120)",
                "IT stazioni",
                "giornaliero",
                "°C, mm precip, snow mm, km/h",
                "Meteostat",
                "Meteostat",
                sample_files=["sources/meteostat_stations/italy_stations_daily_2015_present.csv"],
                time_start="2015",
                time_end="2026",
            ),
            DatasetDef("open_meteo_grid", "sources/open_meteo_grid", "Tentativo griglia Open-Meteo (spesso vuoto/429)", "IT", "giornaliero", "", "Open-Meteo", "Open-Meteo", status="partial"),
        ],
    ),
    PackageDef(
        name="socio-italia",
        title="Socio-economico Italia",
        description=(
            "Driver di domanda: popolazione, PIL/VA settoriale e NUTS, uso suolo, "
            "mobilità/traffico, povertà/reddito (OWID/WB)."
        ),
        refresh=(
            "python db/scripts/harvest_socio_italia.py\n"
            "python db/scripts/harvest_territorio_mobilita.py\n"
            "python db/scripts/harvest_ispra_mit_mobility.py"
        ),
        license_note="Eurostat, World Bank, ISTAT, OWID, MIT open data, ISPRA.",
        gaps="ISTAT SDMX a volte SSL fail; Corine CLC raster richiede download CLMS manuale.",
        datasets=[
            DatasetDef("eurostat_demo", "sources/eurostat", "Demografia/occupazione Eurostat (IT)", "IT / NUTS", "annuale", "persone, %", "Eurostat", "Eurostat"),
            DatasetDef("eurostat_gva", "sources/eurostat_gva", "PIL/VA NACE a10/a64, GDP NUTS2–3, reddito famiglie", "IT NUTS", "annuale", "M€, €/ab", "Eurostat", "Eurostat"),
            DatasetDef("worldbank", "sources/worldbank", "Popolazione, GDP, lavoro, land area", "IT", "annuale", "mix", "World Bank", "CC-BY 4.0"),
            DatasetDef("istat", "sources/istat", "Comuni / estratti ISTAT", "IT", "misto", "", "ISTAT", "open"),
            DatasetDef("land_use", "sources/land_use", "Land cover Eurostat, WB land %, confini ISTAT, geojson", "IT", "annuale/statico", "km2, %", "Eurostat/ISTAT/WB", "open"),
            DatasetDef("mobility", "sources/mobility", "Veicoli/traffico Eurostat, ISPRA flotta, MIT porti/aereo/patenti, OSM", "IT", "annuale/misto", "veicoli, pax", "Eurostat/MIT/ISPRA", "open"),
            DatasetDef("poverty", "sources/poverty", "Povertà/Gini/GNI (PIP + WB)", "IT", "annuale", "%, indice", "OWID/WB", "CC-BY"),
            DatasetDef("owid", "sources/owid", "Estratti OWID demografici/sociali", "IT", "annuale", "", "OWID", "CC-BY"),
        ],
    ),
    PackageDef(
        name="impianti-italia",
        title="Impianti di generazione Italia",
        description="Inventari impianti/centrali da fonti aperte complementari (non Atlaimpianti GSE).",
        refresh="python db/scripts/harvest_impianti_complementari.py",
        license_note="Wikidata CC0; WRI GPPD CC-BY; OSM ODbL; GEM CC-BY 4.0; PowerAtlas termini propri.",
        gaps="GSE Atlaimpianti georiferito: solo download manuale UI.",
        datasets=[
            DatasetDef("wikidata", "sources/wikidata", "Centrali/asset da Wikidata", "IT", "snapshot", "n. impianti", "Wikidata", "CC0"),
            DatasetDef("wri_gppd", "sources/wri_gppd", "WRI Global Power Plant Database — IT", "IT", "snapshot", "MW, fuel", "WRI", "CC-BY"),
            DatasetDef("gem", "sources/gem", "Global Energy Monitor trackers IT", "IT", "snapshot", "MW", "GEM", "CC-BY 4.0"),
            DatasetDef("osm", "sources/osm", "OSM power plant/generator (Overpass)", "IT", "snapshot", "elementi OSM", "OpenStreetMap", "ODbL"),
            DatasetDef("poweratlas", "sources/poweratlas", "Power Atlas impianti IT", "IT", "snapshot", "", "PowerAtlas", "termini PowerAtlas"),
        ],
    ),
    PackageDef(
        name="imprese-energia-italia",
        title="Imprese / operatori energia Italia",
        description="Elenchi operatori e venditori energia da registri ARERA (open data).",
        refresh="Vedi script in imprese-energia-italia/ (harvest_arera.py, build_txt_massivo.py)",
        license_note="ARERA open data.",
        datasets=[
            DatasetDef("arera_operatori", "sources/arera_operatori", "Anagrafe operatori", "IT", "snapshot", "operatori", "ARERA", "open"),
            DatasetDef("arera_vend_ee", "sources/arera_vend_ee", "Venditori elettricità", "IT", "snapshot", "venditori", "ARERA", "open"),
            DatasetDef("arera_vend_gas", "sources/arera_vend_gas", "Venditori gas", "IT", "snapshot", "venditori", "ARERA", "open"),
            DatasetDef("derived", "derived", "Merge/derivati (es. arera_operatori_ALL)", "IT", "snapshot", "", "derivato", "open", sample_files=["derived/arera_operatori_ALL.csv"]),
        ],
    ),
    PackageDef(
        name="oim-italia",
        title="Open Infrastructure Map Italia",
        description=(
            "Geometrie infrastrutturali OSM classificate con legenda OpenInfraMap "
            "(elettrico, generazione, gas, …) in PostGIS + export offline."
        ),
        refresh=(
            "docker compose -f db/oim-italia/docker-compose.yml up -d postgis\n"
            "python db/oim-italia/scripts/build_italia.py"
        ),
        license_note="OSM ODbL — attribuire OpenStreetMap contributors.",
        datasets=[
            DatasetDef("export_gpkg", "export", "Export offline: GPKG, CSV feature/node/edge, stats", "IT", "snapshot", "geometrie", "OSM via OIM", "ODbL"),
            DatasetDef("pbf_data", "data", "Input/aree lavoro PBF (se presenti)", "IT", "snapshot", "", "Geofabrik OSM", "ODbL", status="optional"),
            DatasetDef("legend", "filtri-legenda-completa.json", "Legenda categorie/voci OIM", "—", "statico", "10 cat / 75 voci", "OpenInfraMap", "open"),
        ],
    ),
    PackageDef(
        name="owid-italia",
        title="Our World in Data — estratti Italia",
        description="Dataset OWID filtrati Italia: energia, CO₂, povertà, COVID, catalogo scansione.",
        refresh="python db/owid-italia/scripts/harvest_all.py",
        license_note="OWID CC-BY (verificare dataset singoli).",
        datasets=[
            DatasetDef("energy_data", "sources/energy-data", "Energy data Italy", "IT", "annuale", "mix energia", "OWID", "CC-BY"),
            DatasetDef("co2_data", "sources/co2-data", "CO₂ Italy", "IT", "annuale", "tCO2", "OWID", "CC-BY"),
            DatasetDef("poverty_data", "sources/poverty-data", "Poverty/PIP Italy", "IT", "annuale", "% / indici", "OWID/PIP", "CC-BY"),
            DatasetDef("covid", "sources/covid-19-data", "COVID-19 Italy", "IT", "giornaliero/annuale", "", "OWID", "CC-BY"),
            DatasetDef("energy_use_products", "sources/energy-use-products", "Energy use by product", "IT", "annuale", "", "OWID", "CC-BY"),
            DatasetDef("owid_datasets_scan", "sources/owid-datasets", "Scansione catalogo OWID + subset italy/", "IT/world", "snapshot", "dataset", "OWID", "CC-BY"),
        ],
    ),
    PackageDef(
        name="owid-energy-italia",
        title="OWID Energy Italia (legacy)",
        description="Alias legacy: i dati vivono in owid-italia/sources/energy-data/.",
        refresh="Usare owid-italia.",
        license_note="Vedi owid-italia.",
        datasets=[
            DatasetDef("redirect", ".", "Punta a owid-italia/sources/energy-data/", "IT", "—", "", "OWID", "CC-BY", status="legacy"),
        ],
    ),
]


def build_row(pkg: PackageDef, ds: DatasetDef) -> dict:
    root = DB / pkg.name
    target = root / ds.path
    files = collect_files(target)
    n_files, nbytes = measure_path(target)

    rows = None
    t0, t1 = ds.time_start, ds.time_end
    sample_candidates = [root / s for s in ds.sample_files]
    if not sample_candidates:
        # prefer *italy*.csv / *_all.csv / merges
        preferred = [
            f
            for f in files
            if f.suffix.lower() == ".csv"
            and any(k in f.name.lower() for k in ("italy", "_all", "present", "merge", "summary"))
        ]
        sample_candidates = preferred[:3] or [f for f in files if f.suffix.lower() == ".csv"][:2]

    for sp in sample_candidates:
        if not sp.exists() or not sp.is_file():
            continue
        if rows is None and sp.suffix.lower() == ".csv":
            rows = count_csv_rows(sp)
        if not t0 or not t1:
            a, b = infer_years_from_csv(sp)
            t0 = t0 or a
            t1 = t1 or b
        if rows is not None and t0 and t1:
            break

    if not t0 or not t1:
        a, b = infer_years_from_names(files)
        t0 = t0 or a
        t1 = t1 or b

    status = ds.status
    if n_files == 0 and status == "ok":
        status = "empty"
    # keep explicit planned/partial/legacy/optional even if path missing

    return {
        "package": pkg.name,
        "dataset": ds.dataset,
        "path": ds.path.replace("\\", "/"),
        "description": ds.description,
        "geo": ds.geo,
        "time_start": t0,
        "time_end": t1,
        "granularity": ds.granularity,
        "rows_or_records": rows if rows is not None else "",
        "n_files": n_files,
        "bytes": nbytes,
        "unit_notes": ds.unit_notes,
        "source": ds.source,
        "license": ds.license,
        "status": status,
    }


def write_catalog(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CATALOG_COLS)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def render_metadati(pkg: PackageDef, rows: list[dict]) -> str:
    total_bytes = sum(int(r["bytes"] or 0) for r in rows)
    total_files = sum(int(r["n_files"] or 0) for r in rows)
    lines = [
        "=" * 80,
        f"METADATI — {pkg.title}",
        "=" * 80,
        f"Aggiornato: {TODAY}",
        f"Path:       db/{pkg.name}/",
        f"Volume:     {fmt_bytes(total_bytes)}   |   file dati catalogati: {total_files}",
        "",
        "-" * 80,
        "1. DESCRIZIONE",
        "-" * 80,
        pkg.description,
        "",
        "-" * 80,
        "2. REFRESH",
        "-" * 80,
        pkg.refresh,
        "",
        "-" * 80,
        "3. DATASET (cosa / quanto / copertura)",
        "-" * 80,
    ]
    for r in rows:
        period = ""
        if r["time_start"] or r["time_end"]:
            period = f"{r['time_start'] or '?'}–{r['time_end'] or '?'}"
        qty = []
        if r["rows_or_records"] != "":
            qty.append(f"{r['rows_or_records']} righe (file campione)")
        qty.append(f"{r['n_files']} file")
        qty.append(fmt_bytes(int(r["bytes"] or 0)))
        lines += [
            f"[{r['dataset']}]  status={r['status']}",
            f"  path:    {r['path']}",
            f"  cosa:    {r['description']}",
            f"  geo:     {r['geo']}",
            f"  tempo:   {period or 'n/d'}   |  granularità: {r['granularity'] or 'n/d'}",
            f"  quanto:  {', '.join(qty)}",
            f"  unità:   {r['unit_notes'] or '—'}",
            f"  fonte:   {r['source']}  |  licenza: {r['license']}",
            "",
        ]
    lines += [
        "-" * 80,
        "4. CATALOGO MACHINE-READABLE",
        "-" * 80,
        "Vedi catalog.csv nello stesso folder (rigenerate con:",
        "  python db/scripts/build_metadata_catalogs.py",
        "",
        "-" * 80,
        "5. LICENZE",
        "-" * 80,
        pkg.license_note,
        "",
    ]
    if pkg.gaps:
        lines += [
            "-" * 80,
            "6. BUCHI NOTI",
            "-" * 80,
            pkg.gaps,
            "",
        ]
    lines += ["=" * 80, ""]
    return "\n".join(lines)


def main() -> None:
    all_rows: list[dict] = []
    print(f"Building catalogs under {DB}", flush=True)
    for pkg in PACKAGES:
        print(f"== {pkg.name}", flush=True)
        rows = [build_row(pkg, ds) for ds in pkg.datasets]
        all_rows.extend(rows)
        pkg_dir = DB / pkg.name
        pkg_dir.mkdir(parents=True, exist_ok=True)
        write_catalog(pkg_dir / "catalog.csv", rows)
        (pkg_dir / "METADATI.txt").write_text(render_metadati(pkg, rows), encoding="utf-8")
        print(f"  datasets={len(rows)} volume={fmt_bytes(sum(int(r['bytes'] or 0) for r in rows))}", flush=True)

    write_catalog(DB / "catalog.csv", all_rows)
    # short index
    idx = DB / "CATALOG.md"
    by_pkg: dict[str, list[dict]] = {}
    for r in all_rows:
        by_pkg.setdefault(r["package"], []).append(r)
    md = [
        "# Catalogo dataset — db/",
        "",
        f"Generato: {TODAY} — `python db/scripts/build_metadata_catalogs.py`",
        "",
        "| Pacchetto | Dataset | Volume | File | Periodo | Status |",
        "|-----------|---------|--------|------|---------|--------|",
    ]
    for pkg_name, rows in by_pkg.items():
        tb = sum(int(r["bytes"] or 0) for r in rows)
        tf = sum(int(r["n_files"] or 0) for r in rows)
        md.append(
            f"| `{pkg_name}` | {len(rows)} | {fmt_bytes(tb)} | {tf} | — | vedi METADATI |"
        )
    md += ["", "Dettaglio: `db/<pacchetto>/METADATI.txt` e `catalog.csv`.", ""]
    idx.write_text("\n".join(md), encoding="utf-8")
    print(f"Wrote global catalog.csv ({len(all_rows)} datasets) + CATALOG.md", flush=True)


if __name__ == "__main__":
    main()
