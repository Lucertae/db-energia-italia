"""Backtest PWR-01 v2: normalized wind delta (OM vs ENTSO-E published) → DA price."""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bridge.backtest.pwr_signals import (
    MIN_HIT,
    MIN_IC,
    MIN_OBS,
    MIN_T,
    _align,
    _forward_returns,
    _load_or_fetch_archive,
    _verdict,
)
from bridge.backtest.stats import event_mean, hit_rate_expected, ols_slope, pearson, spearman, summarize
from bridge.spine_io import ROOT, read_fred_csv
from bridge.weather.io import load_weather_manifest


def _zscore_series(values: dict[str, float]) -> dict[str, float]:
    if len(values) < 10:
        return values
    xs = list(values.values())
    m = sum(xs) / len(xs)
    var = sum((v - m) ** 2 for v in xs) / max(1, len(xs) - 1)
    sd = var ** 0.5
    if sd < 1e-9:
        return {d: 0.0 for d in values}
    return {d: (v - m) / sd for d, v in values.items()}


MIN_OVERLAP = 10  # diagnostic backtest while entsoe_wind CSV accumulates history


def _wind_delta_series(
    base: Path,
    desk_id: str,
    zone_id: str,
    lat: float,
    lon: float,
    start: date,
    end: date,
) -> dict[str, float]:
    pub_rows = read_fred_csv(base / "cache" / "weather" / "entsoe_wind" / f"{desk_id}.csv")
    pub = {d[:10]: v for d, v in pub_rows}
    if not pub:
        return {}

    daily = _load_or_fetch_archive(base, zone_id, lat, lon, start, end)
    times = daily.get("time") or []
    winds = daily.get("windspeed_10m_max") or daily.get("wind_speed_10m_max") or []
    om: dict[str, float] = {}
    for t, w in zip(times, winds):
        if w is not None:
            om[str(t)[:10]] = float(w)

    common = sorted(set(om.keys()) & set(pub.keys()))
    if len(common) < MIN_OVERLAP:
        return {}

    om_z = _zscore_series({d: om[d] for d in common})
    pub_z = _zscore_series({d: pub[d] for d in common})
    return {d: om_z[d] - pub_z[d] for d in common}


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    manifest = load_weather_manifest(base)

    desks = ["PDE", "PFR", "PIT"]
    desk_zone: dict[str, dict[str, Any]] = {}
    for z in manifest.get("zones", []):
        desk = z.get("power_desk")
        if desk and str(desk) in desks and str(desk) not in desk_zone:
            desk_zone[str(desk)] = z

    min_date: date | None = None
    max_date: date | None = None
    prices_by_desk: dict[str, dict[str, float]] = {}
    for desk in desks:
        rows = read_fred_csv(base / "cache" / f"{desk}.csv")
        if not rows:
            continue
        prices_by_desk[desk] = {d: v for d, v in rows}
        d0 = date.fromisoformat(rows[0][0])
        d1 = date.fromisoformat(rows[-1][0])
        min_date = d0 if min_date is None else min(min_date, d0)
        max_date = d1 if max_date is None else max(max_date, d1)

    if not prices_by_desk or not min_date or not max_date:
        return {
            "ok": False,
            "module": "backtest_wind_delta",
            "message": "missing power or entsoe wind CSV",
            "outputs": [],
        }

    end = min(max_date, date.today() - timedelta(days=5))
    start = min_date

    results: list[dict[str, Any]] = []
    for desk in desks:
        if desk not in prices_by_desk or desk not in desk_zone:
            continue
        z = desk_zone[desk]
        delta = _wind_delta_series(
            base, desk, z["id"], float(z["lat"]), float(z["lon"]), start, end
        )
        if len(delta) < MIN_OVERLAP:
            results.append({
                "signal_id": "PWR-01b",
                "desk": desk,
                "n_overlap": len(delta),
                "verdict": {"passed": False, "note": "insufficient entsoe wind overlap"},
            })
            continue

        rets = _forward_returns(prices_by_desk[desk])
        xs, ys = _align(delta, rets)
        ic, t_stat, n = pearson(xs, ys)
        hr = hit_rate_expected(xs, ys, expected_sign=-1)
        slope, intercept, _ = ols_slope(xs, ys)
        ev = event_mean(xs, ys)
        spread = float(ev.get("spread", 0.0))
        v = _verdict(ic, t_stat, hr, n, expected_sign=-1, event_spread=spread)
        if n < MIN_OBS:
            v = {**v, "passed": False, "note": f"diagnostic n={n}<{MIN_OBS} — accumulate entsoe_wind history"}
        results.append({
            "signal_id": "PWR-01b",
            "desk": desk,
            "hypothesis": "delta_z>0 (more wind vs TSO) → DA price ↓",
            "expected_sign": -1,
            "method": "zscore(om_wind_ms) - zscore(entsoe_wind_mw)",
            "n_overlap": len(delta),
            "ic_pearson": round(ic, 4),
            "ic_spearman": round(spearman(xs, ys), 4),
            "t_stat": round(t_stat, 3),
            "hit_rate": round(hr, 4),
            "regression": {"slope": round(slope, 4), "intercept": round(intercept, 4)},
            "event_study": ev,
            "forward_return": summarize(ys),
            "verdict": v,
        })

    any_pass = any(r.get("verdict", {}).get("passed") for r in results)
    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "signal_id": "PWR-01b",
        "sample": {"start": start.isoformat(), "end": end.isoformat()},
        "results": results,
        "any_desk_passed": any_pass,
        "gates": {"min_obs": MIN_OBS, "min_overlap": MIN_OVERLAP, "min_ic": MIN_IC, "min_hit": MIN_HIT, "min_t": MIN_T},
        "note": "ENTSO-E wind CSV accumulates daily; full backtest needs ~120d overlap",
    }
    out_path = base / "cache" / "spine" / "modules" / "backtest_wind_delta.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    best = max(results, key=lambda r: abs(r.get("ic_pearson", 0) or 0), default={})
    msg = f"PWR-01b={'PASS' if any_pass else 'FAIL'}"
    if best.get("ic_pearson") is not None:
        msg += f" | best {best.get('desk')} IC={best.get('ic_pearson'):+.3f}"

    return {
        "ok": len(results) > 0,
        "module": "backtest_wind_delta",
        "message": msg,
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
