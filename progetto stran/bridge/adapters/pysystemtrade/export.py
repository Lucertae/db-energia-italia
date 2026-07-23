"""Export desk FX daily series for pysystemtrade / CME futures research.

Convention (scrupulous):
- Never export raw desk_id CSV without normalization.
- 6E: FRED DEXUSEU = USD per EUR (CME 6E native).
- Other CME FX: FRED USD-leg directly (DEXJPUS, DEXUSUK, …) = exchange quote.
- EUR-base crosses kept in manifest for graph/carry, not blindly exported as CME price.
"""
from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.spine_io import ROOT, desk_csv_path, load_fx_manifest, read_fred_csv


def _align_fred_daily(
    eur_usd: list[tuple[str, float]],
    leg: list[tuple[str, float]],
    *,
    usd_per_quote: bool,
) -> list[tuple[str, float]]:
    leg_map = {d[:10]: v for d, v in leg}
    out: list[tuple[str, float]] = []
    for d, eu in eur_usd:
        lv = leg_map.get(d[:10])
        if lv is None or lv <= 0 or eu <= 0:
            continue
        if usd_per_quote:
            out.append((d[:10], eu / lv))
        else:
            out.append((d[:10], lv * eu))
    return out


def _eur_base_daily(root: Path, pair: dict[str, Any]) -> list[tuple[str, float]]:
    """Quote per 1 EUR from FRED legs (date-aligned)."""
    quote = pair.get("quote")
    fred_leg = pair.get("fred_leg_id")
    if not fred_leg:
        return []

    eur_usd = read_fred_csv(desk_csv_path(root, "EUF"))
    leg = read_fred_csv(desk_csv_path(root, str(fred_leg)))
    if not eur_usd or not leg:
        return []

    if quote == "USD":
        return [(d[:10], v) for d, v in eur_usd if v > 0]

    usd_per_quote = bool(pair.get("usd_per_quote"))
    return _align_fred_daily(eur_usd, leg, usd_per_quote=usd_per_quote)


def _cme_daily(root: Path, pair: dict[str, Any]) -> list[tuple[str, float]]:
    """CME-native daily price series for one manifest pair."""
    cme = pair.get("cme_future")
    fred_leg = pair.get("fred_leg_id")
    if not cme:
        return []

    # 6E settles on USD per EUR — FRED DEXUSEU directly
    if cme == "6E":
        rows = read_fred_csv(desk_csv_path(root, "EUF"))
        return [(d[:10], v) for d, v in rows if v > 0]

    # Other CME FX: use FRED USD leg (matches sources.c labels: USD/JPY, USD/GBP, …)
    if fred_leg:
        rows = read_fred_csv(desk_csv_path(root, str(fred_leg)))
        return [(d[:10], v) for d, v in rows if v > 0]

    return []


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    manifest = load_fx_manifest(base)
    export_dir = base / "cache" / "exports" / "pysystemtrade"
    export_dir.mkdir(parents=True, exist_ok=True)

    exported: list[dict[str, Any]] = []
    for pair in manifest.get("pairs", []):
        cme = pair.get("cme_future")
        if not cme:
            continue
        rows = _cme_daily(base, pair)
        eur_rows = _eur_base_daily(base, pair)
        if len(rows) < 30:
            continue

        fname = f"{cme}_daily_prices.csv"
        fpath = export_dir / fname
        with fpath.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["date", "price"])
            for d, v in rows:
                w.writerow([d, f"{v:.8f}"])

        exported.append({
            "cme": cme,
            "pair_id": pair.get("id"),
            "export_mode": "cme_fred_leg" if cme != "6E" else "cme_usd_per_eur",
            "eur_base_last": eur_rows[-1][1] if eur_rows else None,
            "file": fname,
            "rows": len(rows),
            "last": rows[-1][1],
        })

    pmanifest = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source": "ops_desk_bridge",
        "convention": {
            "6E": "FRED DEXUSEU = USD per EUR (CME native)",
            "6J/6B/6M/6C/6N": "FRED USD-leg (DEX*) = CME quote direction, NOT EUR-base cross",
        },
        "pysystemtrade_repo": "https://github.com/pst-group/pysystemtrade",
        "instruments": exported,
    }
    (export_dir / "manifest.json").write_text(
        json.dumps(pmanifest, indent=2), encoding="utf-8"
    )

    status = {
        "built_at": pmanifest["built_at"],
        "export_dir": "cache/exports/pysystemtrade",
        "count": len(exported),
        "instruments": [e["cme"] for e in exported],
    }
    status_path = base / "cache" / "spine" / "modules" / "pysystemtrade_export.json"
    status_path.parent.mkdir(parents=True, exist_ok=True)
    status_path.write_text(json.dumps(status, indent=2), encoding="utf-8")

    return {
        "ok": len(exported) > 0,
        "module": "pysystemtrade_export",
        "message": f"exported {len(exported)} CME (fred-native)",
        "outputs": [
            str(status_path.relative_to(base)).replace("\\", "/"),
            "cache/exports/pysystemtrade/manifest.json",
        ],
    }
