"""Configurazione pipeline aziende energia in crisi."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
load_dotenv(ROOT / ".env")

CACHE_DIR = ROOT / "cache"
OUTPUT_DIR = ROOT / "output"
CACHE_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

USER_AGENT = (
    "AziendeCrisiEnergiaBot/1.0 (+local research; "
    "contact: operatori-energia-crisi@localhost; respectful crawler)"
)
MIN_DELAY_SECONDS = 2.0
MAX_RETRIES = 4
REQUEST_TIMEOUT = 45.0
LOOKBACK_MONTHS = 24
FUZZY_RATIO_THRESHOLD = 92
MAX_PARALLEL_SOURCES = 3

ATECO_CORE = [
    "35.11",
    "35.12",
    "35.13",
    "35.14",
    "35.21",
    "35.22",
    "35.23",
    "35.30",
]
ATECO_ADIACENTI = [
    "06.10",
    "06.20",
    "09.10",
    "19.10",
    "19.20",
    "27.11",
    "27.12",
    "27.20",
    "27.90",
    "43.21",
    "43.22",
    "42.22",
    "38.22",
    "71.12.2",
    "46.71",
]
ATECO_TARGET = ATECO_CORE + ATECO_ADIACENTI

KEYWORDS_ENERGIA = [
    "energia",
    "energy",
    "fotovoltaic",
    "fotovolt",
    "pannell fotovolta",
    "pannelli solari",
    "solar",
    "eolic",
    "eolico",
    "wind",
    "idroelettric",
    "biogas",
    "biometano",
    "biomasse",
    "geotermi",
    "power plant",
    "energia elettr",
    "impianto elettr",
    "societa elettr",
    "società elettr",
    "petrol",
    "oil & gas",
    "carburant",
    "rinnovabil",
    "hydrogen",
    "idrogeno",
    "energy storage",
    "teleriscaldament",
    "cogenerazion",
    "utility",
    "utilities",
    "gas ",
    " gas",
    "metano",
    "centrale elettr",
    "centrale eolic",
    "centrale idroe",
    "centrale termoelettr",
    "inverter fotovolta",
    "cabina primaria",
    "elettrodotto",
    "turbina eolic",
    "turbina a gas",
    "impianto fotovolta",
    "parco eolico",
    "raffiner",
]

# Nomi noti filiera energia nei tavoli MIMIT (match anche senza keyword generica)
MIMIT_ENERGY_NAME_HINTS = [
    "sofinter",
    "isab",
    "lukoil",
    "portovesme",
    "wartsila",
    "fimer",
    "eurallumina",
    "enel",
    "eni ",
    "snam",
    "italgas",
]

PROCEDURE_TERMS = [
    "liquidazione giudiziale",
    "fallimento",
    "concordato",
    "liquidazione coatta",
    "amministrazione straordinaria",
    "composizione negoziata",
    "misure protettive",
    "in liquidazione",
]

STATO_PRIORITY = {
    "liquidazione giudiziale": 0,
    "fallimento": 0,
    "fall.": 0,
    "l.g.": 0,
    "concordato preventivo": 1,
    "concordato": 1,
    "c.p.": 1,
    "amministrazione straordinaria": 2,
    "liquidazione coatta": 3,
    "composizione negoziata": 4,
    "misure protettive": 4,
    "tavolo di crisi mimit": 5,
    "tavolo di crisi mimit (monitoraggio)": 6,
    "scioglimento/liquidazione volontaria": 7,
    "in liquidazione": 7,
    "distress / news": 8,
}

OPENAPI_IT_KEY = os.getenv("OPENAPI_IT_KEY", "").strip()
CERVED_KEY = os.getenv("CERVED_KEY", "").strip()
TELEMACO_USER = os.getenv("TELEMACO_USER", "").strip()
TELEMACO_PASS = os.getenv("TELEMACO_PASS", "").strip()

# Anagrafica energia locale (opzionale): usato solo per enrichment P.IVA/provincia
ANAGRAFICA_LOCALE_PATH = Path(
    os.getenv(
        "ANAGRAFICA_LOCALE_PATH",
        str(ROOT.parent / "aziende-energetiche-it.txt"),
    )
)

PVP_SEARCH_URL = (
    "https://pvp.giustizia.it/ric-496b258c-986a1b71/ric-ms/"
    "ricerca/vendite?isPreview=true&language=it"
)
PVP_MAX_PAGES = 80  # ~20 risultati/pagina; copertura ampia con cache
PVP_DETAIL_URL_TMPL = "https://pvp.giustizia.it/pvp/#/dettaglio/{id}"

MIMIT_ATTIVI_URL = "https://www.mimit.gov.it/it/tavoli-crisi/attivi"
MIMIT_MONITORAGGIO_URL = "https://www.mimit.gov.it/it/tavoli-crisi/in-monitoraggio"

GAZZETTA_SEARCH_URL = "https://www.gazzettaufficiale.it/ricerca/java/spoolerResultRicerca"

ASTALEGALE_SEARCH_URL = "https://www.astalegale.net/Aste/Ricerca"
FALLCOASTE_SEARCH_URL = "https://www.fallcoaste.it/aste"

OPENAPI_BASE = "https://company.openapi.com"
OPENAPI_SEARCH = f"{OPENAPI_BASE}/IT-search"
OPENAPI_START = f"{OPENAPI_BASE}/IT-start"

OPENAPI_CRISIS_ACTIVITY_HINTS = [
    "liquidazione",
    "fallit",
    "concordato",
    "scioglimento",
    "cessat",
    "inattiva",
    "cancellat",
]

NEWS_MAX_QUERIES = 30
