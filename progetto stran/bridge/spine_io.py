"""Shared I/O for desk spine, FRED CSV, ECB XML, FX manifest."""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def read_fred_csv(path: Path) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    if not path.is_file():
        return rows
    lines = path.read_text(encoding="utf-8").splitlines()
    for line in lines[1:]:
        parts = line.split(",")
        if len(parts) < 2:
            continue
        try:
            val = float(parts[1])
        except ValueError:
            continue
        rows.append((parts[0].strip(), val))
    return rows


def fred_last(path: Path) -> float | None:
    rows = read_fred_csv(path)
    return rows[-1][1] if rows else None


def read_ecb_fx(path: Path) -> dict[str, float]:
    out: dict[str, float] = {}
    if not path.is_file():
        return out
    text = path.read_text(encoding="utf-8")
    for m in re.finditer(r"currency='([A-Z]{3})'\s+rate='([0-9.]+)'", text):
        out[m.group(1)] = float(m.group(2))
    if out:
        return out
    try:
        root = ET.fromstring(text)
        for cube in root.iter():
            cur = cube.attrib.get("currency")
            rate = cube.attrib.get("rate")
            if cur and rate and len(cur) == 3:
                out[cur] = float(rate)
    except ET.ParseError:
        pass
    return out


def load_fx_manifest(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    path = base / "config" / "fx_manifest.json"
    if not path.is_file():
        return {"pairs": [], "hub": "EUR", "fee_bps": 2}
    return load_json(path)


def desk_csv_path(root: Path, desk_id: str) -> Path:
    p = root / "cache" / f"{desk_id}.csv"
    if p.is_file():
        return p
    return root / "cache" / "fred" / f"{desk_id}.csv"


def pair_spot_eur_base(root: Path, pair: dict[str, Any], ecb: dict[str, float]) -> float | None:
    """Return quote-per-EUR (EUR/X convention) for one manifest pair."""
    ecb_cur = pair.get("ecb_currency")
    if ecb_cur and ecb_cur in ecb:
        return ecb[ecb_cur]

    fred_leg = pair.get("fred_leg_id")
    usd_per_quote = bool(pair.get("usd_per_quote"))
    if not fred_leg:
        return None

    eur_usd = ecb.get("USD")
    if eur_usd is None:
        eur_usd = fred_last(desk_csv_path(root, "EUF"))
    leg = fred_last(desk_csv_path(root, str(fred_leg)))
    if eur_usd is None or leg is None or leg <= 0:
        return None

    if str(pair.get("quote")) == "USD":
        return eur_usd
    if usd_per_quote:
        return eur_usd / leg
    return leg * eur_usd


def build_eur_cross_rates(root: Path) -> dict[str, float]:
    manifest = load_fx_manifest(root)
    ecb_path = root / "cache" / "ecb" / "eurofxref-daily.xml"
    ecb = read_ecb_fx(ecb_path)
    rates: dict[str, float] = {"EUR": 1.0}

    for pair in manifest.get("pairs", []):
        quote = pair.get("quote")
        if not quote:
            continue
        spot = pair_spot_eur_base(root, pair, ecb)
        if spot is not None and spot > 0:
            rates[str(quote)] = spot
    return rates
