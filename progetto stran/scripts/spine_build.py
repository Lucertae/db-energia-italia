#!/usr/bin/env python3
"""Build desk spine health: scan cache freshness → cache/spine/status.json."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
import sys

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CONFIG = ROOT / "config" / "desk_spine.json"
SIGNALS = ROOT / "config" / "signals.json"
OUT_DIR = ROOT / "cache" / "spine"
OUT_STATUS = OUT_DIR / "status.json"
OUT_LIVE = OUT_DIR / "signals_live.json"


def read_csv_series(path: Path) -> list[tuple[str, float]]:
    rows: list[tuple[str, float]] = []
    if not path.is_file():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split(",")
        if len(parts) < 2:
            continue
        try:
            val = float(parts[1])
        except ValueError:
            continue
        rows.append((parts[0].strip(), val))
    return rows


def chokepoint_deltas(root: Path) -> dict[str, int]:
    cp = root / "cache" / "portwatch" / "chokepoints.csv"
    out: dict[str, int] = {}
    if not cp.is_file():
        return out
    rows: dict[str, list[tuple[str, int]]] = {}
    for line in cp.read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split(",")
        if len(parts) < 6:
            continue
        desk, ntot = parts[1], int(parts[4] or 0)
        rows.setdefault(desk, []).append((parts[0], ntot))
    for desk, pts in rows.items():
        pts.sort(key=lambda x: x[0], reverse=True)
        latest = pts[0][1]
        hist = [v for _, v in pts[1:31]]
        base = sum(hist) / len(hist) if hist else latest
        out[desk] = int((latest - base) * 100 / base) if base else 0
    return out


def ngs_seasonal_z(root: Path) -> float | None:
    from datetime import datetime

    rows = read_csv_series(root / "cache" / "NGS.csv")
    if len(rows) < 52:
        return None
    parsed: list[tuple[datetime, float]] = []
    for d, v in rows:
        try:
            parsed.append((datetime.strptime(d[:10], "%Y-%m-%d"), v))
        except ValueError:
            continue
    if not parsed:
        return None
    parsed.sort(key=lambda x: x[0])
    latest_dt, latest_val = parsed[-1]
    wk = latest_dt.isocalendar().week
    yr = latest_dt.year
    hist = [v for dt, v in parsed if dt.isocalendar().week == wk and yr - 5 <= dt.year < yr]
    if len(hist) < 3:
        return None
    mu = sum(hist) / len(hist)
    var = sum((x - mu) ** 2 for x in hist) / max(1, len(hist) - 1)
    sd = var ** 0.5
    return (latest_val - mu) / sd if sd > 0 else None


def ttf_hub_spread_z(root: Path) -> float | None:
    hub = {d[:10]: v for d, v in read_csv_series(root / "cache" / "HUB.csv")}
    ttf = {d[:10]: v for d, v in read_csv_series(root / "cache" / "TTF.csv")}
    common = sorted(set(hub) & set(ttf))
    if len(common) < 24:
        return None
    spreads = [ttf[d] - hub[d] for d in common[-36:]]
    latest = spreads[-1]
    mu = sum(spreads) / len(spreads)
    var = sum((x - mu) ** 2 for x in spreads) / max(1, len(spreads) - 1)
    sd = var ** 0.5
    return (latest - mu) / sd if sd > 0 else None


def evaluate_signals(root: Path) -> list[dict]:
    live: list[dict] = []
    deltas = chokepoint_deltas(root)
    hormuz = deltas.get("HORMUZ")
    if hormuz is not None:
        alert = hormuz < -30
        live.append({
            "id": "MAR-02",
            "metric": "HORMUZ_delta_pct",
            "value": hormuz,
            "alert": alert,
            "msg": f"HORMUZ {hormuz:+d}% vs 30d" + (" ALERT" if alert else ""),
        })

    z_ngs = ngs_seasonal_z(root)
    if z_ngs is not None:
        alert = abs(z_ngs) > 1.5
        live.append({
            "id": "GAS-01",
            "metric": "ngs_z_vs_season",
            "value": round(z_ngs, 2),
            "alert": alert,
            "msg": f"NGS seasonal z={z_ngs:+.2f}" + (" ALERT" if alert else ""),
        })

    z_spread = ttf_hub_spread_z(root)
    if z_spread is not None:
        alert = abs(z_spread) > 2.0
        live.append({
            "id": "GAS-02",
            "metric": "ttf_hub_spread_z",
            "value": round(z_spread, 2),
            "alert": alert,
            "msg": f"TTF-HUB z={z_spread:+.2f}" + (" ALERT" if alert else ""),
        })
    return live


def age_hours(path: Path) -> int | None:
    if not path.is_file():
        return None
    mtime = path.stat().st_mtime
    return int((datetime.now().timestamp() - mtime) / 3600)


def check_entry(entry: dict, root: Path) -> dict:
    paths = entry.get("paths") or [entry.get("path", "")]
    max_h = int(entry.get("max_age_h", 48))
    best_age: int | None = None
    found = False
    used = ""

    for rel in paths:
        if not rel:
            continue
        p = root / rel.replace("/", os.sep)
        if p.is_file():
            found = True
            used = rel
            a = age_hours(p)
            if a is not None and (best_age is None or a < best_age):
                best_age = a

    if not found:
        status = "missing"
    elif best_age is not None and best_age > max_h:
        status = "stale"
    else:
        status = "ok"

    return {
        "id": entry.get("id", "?"),
        "status": status,
        "age_h": best_age,
        "max_age_h": max_h,
        "path": used,
        "tier": entry.get("tier", "standard"),
    }


def load_chokepoint_brief(root: Path) -> str:
    cp = root / "cache" / "portwatch" / "chokepoints.csv"
    if not cp.is_file():
        return ""
    rows: dict[str, list[tuple[str, int]]] = {}
    for line in cp.read_text(encoding="utf-8").splitlines()[1:]:
        parts = line.split(",")
        if len(parts) < 6:
            continue
        date, desk, _, _, ntot, _ = parts[0], parts[1], parts[2], parts[3], int(parts[4] or 0), parts[5]
        rows.setdefault(desk, []).append((date, ntot))
    parts_b = []
    for desk in ("HORMUZ", "MALACCA"):
        if desk not in rows:
            continue
        rows[desk].sort(key=lambda x: x[0], reverse=True)
        latest_date, latest = rows[desk][0]
        hist = [v for d, v in rows[desk][1:31]]
        base = sum(hist) / len(hist) if hist else latest
        delta = int((latest - base) * 100 / base) if base else 0
        parts_b.append(f"{desk} {latest} ({delta:+d}% vs 30d)")
    return " | ".join(parts_b)


def main() -> int:
    if not CONFIG.is_file():
        print(f"FAIL missing {CONFIG}", flush=True)
        return 1

    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    series_rows = [check_entry(s, ROOT) for s in cfg.get("series", [])]
    pipe_rows = [check_entry(p, ROOT) for p in cfg.get("pipelines", [])]

    ext_rows = []
    for ext in cfg.get("external", []):
        rel = ext.get("path", "")
        p = (ROOT / rel).resolve()
        max_h = int(ext.get("max_age_h", 24))
        optional = bool(ext.get("optional", True))
        if p.is_file():
            a = age_hours(p)
            st = "ok" if a is not None and a <= max_h else "stale"
            ext_rows.append({"id": ext["id"], "status": st, "age_h": a, "path": rel})
        elif optional:
            ext_rows.append({"id": ext["id"], "status": "optional_missing", "age_h": None, "path": rel})
        else:
            ext_rows.append({"id": ext["id"], "status": "missing", "age_h": None, "path": rel})

    counts = {"ok": 0, "stale": 0, "missing": 0}
    for r in series_rows + pipe_rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1

    modules_index: dict = {"ok": False, "brief": "skipped"}
    try:
        from bridge.module_runner import run_all

        modules_index = run_all(ROOT)
    except Exception as exc:
        modules_index = {"ok": False, "brief": f"FAIL:{exc}", "modules": [], "error": str(exc)}

    active_signals = []
    if SIGNALS.is_file():
        sig = json.loads(SIGNALS.read_text(encoding="utf-8"))
        active_signals = [s for s in sig.get("signals", []) if s.get("status") == "active"]

    cp_brief = load_chokepoint_brief(ROOT)
    signals_live = evaluate_signals(ROOT)

    wx_path = ROOT / "cache" / "spine" / "modules" / "weather_signals.json"
    if wx_path.is_file():
        try:
            wx = json.loads(wx_path.read_text(encoding="utf-8"))
            for s in wx.get("signals", []):
                if s.get("alert"):
                    signals_live.append({
                        "id": s.get("id", "WX"),
                        "metric": s.get("metric", "weather"),
                        "value": s.get("value", s.get("hdd_anom", 0)),
                        "alert": True,
                        "msg": s.get("msg", ""),
                    })
        except (json.JSONDecodeError, OSError):
            pass

    alerts = [s for s in signals_live if s.get("alert")]
    brief_parts = [
        f"SPINE ok={counts['ok']} stale={counts['stale']} miss={counts['missing']}",
    ]
    if cp_brief:
        brief_parts.append(cp_brief)
    if active_signals:
        brief_parts.append("SIG:" + ",".join(s["id"] for s in active_signals))
    if alerts:
        brief_parts.append("ALERT:" + ",".join(s["id"] for s in alerts))

    status = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "summary": counts,
        "series": series_rows,
        "pipelines": pipe_rows,
        "external": ext_rows,
        "signals_active": len(active_signals),
        "signals_live": signals_live,
        "signals_alert": len(alerts),
        "brief": " | ".join(brief_parts),
        "modules": modules_index.get("modules", []),
        "modules_ok": modules_index.get("ok", False),
    }
    if modules_index.get("brief"):
        brief_parts.append("MOD:" + str(modules_index["brief"]))
        status["brief"] = " | ".join(brief_parts)
    if modules_index.get("error"):
        status["modules_error"] = modules_index["error"]

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    OUT_STATUS.write_text(json.dumps(status, indent=2), encoding="utf-8")
    OUT_LIVE.write_text(json.dumps({"built_at": status["built_at"], "signals": signals_live}, indent=2), encoding="utf-8")
    print(f"OK spine status -> {OUT_STATUS}  {status['brief']}")
    try:
        import subprocess
        import sys
        man = HERE / "desk_harvest" / "build_ingest_manifest.py"
        if man.is_file():
            subprocess.run([sys.executable, str(man)], cwd=str(HERE / "desk_harvest"), check=False)
    except Exception:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
