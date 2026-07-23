"""Load desk API keys from cache/*.key into os.environ (UI KEYS tab writes these)."""
from __future__ import annotations

import os
from pathlib import Path

# id → (env var, relative file under desk root / cache)
KEY_DEFS: list[tuple[str, str, str]] = [
    ("eia", "EIA_API_KEY", "eia.key"),
    ("entsoe", "ENTSOE_API_TOKEN", "entsoe.key"),
    ("gie", "HEDGE_GIE_API_KEY", "gie.key"),
    ("terna", "TERNA_API_KEY", "terna.key"),
    ("emaps", "ELECTRICITYMAPS_API_KEY", "emaps.key"),
    ("ocm", "OPENCHARGEMAP_API_KEY", "ocm.key"),
    ("ais", "AISSTREAM_API_KEY", "ais.key"),
    ("gfw", "GFW_API_TOKEN", "gfw.key"),
    ("firms", "NASA_FIRMS_MAP_KEY", "firms.key"),
    ("opensky", "OPENSKY_CLIENT_ID", "opensky.key"),
    ("aviationstack", "AVIATIONSTACK_API_KEY", "aviationstack.key"),
    ("acled", "ACLED_API_KEY", "acled.key"),
    ("ucdp", "UCDP_ACCESS_TOKEN", "ucdp.key"),
    ("abuseipdb", "ABUSEIPDB_API_KEY", "abuseipdb.key"),
    ("otx", "OTX_API_KEY", "otx.key"),
    ("fred", "FRED_API_KEY", "fred.key"),
    ("databento", "DATABENTO_API_KEY", "databento.key"),
    ("quandl", "QUANDL_API_KEY", "quandl.key"),
    ("cdsapi", "CDSAPI_KEY", "cdsapi.key"),
    ("finnhub", "FINNHUB_API_KEY", "finnhub.key"),
    ("icao", "ICAO_API_KEY", "icao.key"),
    ("openaq", "OPENAQ_API_KEY", "openaq.key"),
    ("waqi", "WAQI_API_KEY", "waqi.key"),
    ("windy", "WINDY_API_KEY", "windy.key"),
]

ENV_TO_FILE = {env: fname for _, env, fname in KEY_DEFS}


def _read_key_file(path: Path) -> str:
    if not path.is_file():
        return ""
    try:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return ""
    return text.splitlines()[0].strip() if text else ""


def apply_keys(cache_dir: Path | None = None) -> dict[str, bool]:
    """Load missing env vars from cache/*.key. Returns {env: present}."""
    if cache_dir is None:
        here = Path(__file__).resolve().parent
        root = Path(os.environ.get("DESK_ROOT", here.parents[1]))
        cache_dir = Path(os.environ.get("DESK_CACHE", root / "cache"))
    status: dict[str, bool] = {}
    for _, env, fname in KEY_DEFS:
        cur = os.environ.get(env, "").strip()
        if not cur:
            val = _read_key_file(cache_dir / fname)
            if val:
                os.environ[env] = val
                cur = val
                if env == "ENTSOE_API_TOKEN":
                    os.environ.setdefault("HEDGE_ENTSOE_TOKEN", val)
        status[env] = bool(cur)
    return status


def has_key(env_name: str, cache_dir: Path | None = None) -> bool:
    apply_keys(cache_dir)
    return bool(os.environ.get(env_name, "").strip())
