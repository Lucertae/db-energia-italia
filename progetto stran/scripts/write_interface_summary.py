#!/usr/bin/env python3
"""Riepilogo testuale stato dati/ingestion — no dump raw."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "interfacce" / "riepilogo.txt"


def count_files(glob: str) -> int:
    return sum(1 for _ in ROOT.glob(glob))


def read_json(path: Path) -> dict | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def module_lines() -> list[str]:
    lines = ["=== Moduli spine (cache/spine/modules/) ==="]
    mod_dir = ROOT / "cache" / "spine" / "modules"
    if not mod_dir.is_dir():
        lines.append("  (cartella assente)")
        return lines
    for p in sorted(mod_dir.glob("*.json")):
        data = read_json(p) or {}
        status = data.get("status") or data.get("ok")
        if status is None and "results" in data:
            status = "results"
        elif status is None and "error" in data:
            status = f"ERR: {data['error'][:80]}"
        elif status is None:
            status = "ok" if p.stat().st_size > 20 else "empty"
        built = data.get("built_at") or data.get("updated") or "-"
        sig = data.get("signal_id") or data.get("module") or p.stem
        extra = ""
        if p.stem == "backtest_pwr_v2":
            res = data.get("results") or []
            if res:
                extra = f" | any_pass={data.get('any_desk_passed')} desks={len(res)}"
        lines.append(f"  {p.name}: {sig} | {built} | {status}{extra}")
    return lines


def cache_lines() -> list[str]:
    lines = ["", "=== Cache dati (conteggi, no dump) ==="]
    buckets = [
        ("FRED CSV", "cache/*.csv"),
        ("Storico histdb", "cache/histdb/*.db"),
        ("Open-Meteo hourly PDE", "cache/weather/open_meteo_hourly/PDE/**/*.json"),
        ("Open-Meteo hourly PFR", "cache/weather/open_meteo_hourly/PFR/**/*.json"),
        ("Open-Meteo hourly PIT", "cache/weather/open_meteo_hourly/PIT/**/*.json"),
        ("ENTSO-E imbalance PIT", "cache/weather/entsoe_hourly/imbalance/PIT/*.json"),
        ("ENTSO-E wind published PDE", "cache/weather/entsoe_hourly/wind_published/PDE/*.json"),
        ("EPEX ID index", "cache/weather/epex/id_index/**/*.json"),
        ("Netztransparenz IdAep", "cache/weather/netztransparenz/IdAep/**/*"),
        ("Spine signals", "cache/spine/signals*.json"),
    ]
    for label, pattern in buckets:
        n = count_files(pattern)
        lines.append(f"  {label}: {n} file")
    man = read_json(ROOT / "cache" / "weather" / "entsoe_hourly" / "manifest.json")
    if man:
        lines.append(f"  ENTSO-E manifest updated: {man.get('updated', man.get('built_at', '-'))}")
    return lines


def pwr_summary() -> list[str]:
    lines = ["", "=== PWR-01 v2 backtest (sintesi) ==="]
    data = read_json(ROOT / "cache" / "spine" / "modules" / "backtest_pwr_v2.json")
    if not data:
        lines.append("  (backtest non eseguito)")
        return lines
    lines.append(f"  built_at: {data.get('built_at')}")
    lines.append(f"  any_desk_passed: {data.get('any_desk_passed')}")
    for r in data.get("results") or []:
        desk = r.get("desk", "?")
        full = r.get("full_sample") or {}
        cond = r.get("conditional_test_sample") or r.get("conditional_test") or {}
        fs = full.get("stats") or {}
        cs = cond.get("stats") or {}
        cv = cond.get("verdict") or {}
        ic_f = fs.get("ic")
        ic_c = cs.get("ic") if cs.get("ic") is not None else cv.get("ic_pearson")
        ic_fs = f"{ic_f:.4f}" if isinstance(ic_f, (int, float)) else str(ic_f)
        ic_cs = f"{ic_c:.4f}" if isinstance(ic_c, (int, float)) else str(ic_c)
        t_boot = cv.get("t_boot", cond.get("t_boot", "?"))
        passed = cv.get("passed", cond.get("passed", "?"))
        lines.append(
            f"  {desk}: target={r.get('target_effective', '-')} | "
            f"full IC={ic_fs} t_ic={fs.get('t_ic', '?')} | "
            f"cond IC={ic_cs} t_boot={t_boot} pass={passed}"
        )
    return lines


def ingestion_notes() -> list[str]:
    lines = ["", "=== Ingestion / sorgenti live (desk C) ==="]
    notes = [
        "FRED, ECB, STOOQ, EIA: refresh periodico via ingest_* (WinHTTP/cURL)",
        "ENTSO-E: XML desk + bridge entsoe_py_harvest (chiave in cache/eia.key o env)",
        "Crypto: Binance/Kraken ticker + funding",
        "AIS/Portwatch: cache locale + ingest_intel",
        "Libero: DB SQLite remoto (scripts/libero)",
        "Meteo: Open-Meteo forecast + grid hourly (bridge om_hourly_harvest)",
        "Spine Python: scripts/spine_build.py orchestra moduli config/modules.json",
    ]
    for n in notes:
        lines.append(f"  • {n}")
    lines.append("")
    lines.append("Per dettaglio serie: pagina CAT (screenshot 14-catalog.png)")
    lines.append("Per segnali research: cache/spine/modules/*.json (solo meta, non CSV)")
    return lines


def main() -> None:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    parts = [
        "OPS DESK — riepilogo stato dati",
        f"Generato: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')} UTC",
        f"Progetto: {ROOT}",
        "",
        "Screenshot: cartella interfacce/ (15 pagine, attesa ~40s pre-cattura)",
        "",
    ]
    parts.extend(module_lines())
    parts.extend(cache_lines())
    parts.extend(pwr_summary())
    parts.extend(ingestion_notes())
    OUT.write_text("\n".join(parts) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    main()
