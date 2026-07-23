"""Backtest PWR-02 (HDD anomaly → DA return) and PWR-01 (wind → DA return).

Uses desk power CSVs (PDE/PFR/PIT…) + Open-Meteo archive (cached under cache/weather/backtest/).
Stdlib only — no vectorbt required.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from bridge.backtest.stats import (
    bonferroni_t_threshold,
    event_mean,
    event_sign_ok,
    hit_rate_expected,
    ic_by_season,
    ols_slope,
    pearson,
    pearson_with_nw,
    spearman,
    summarize,
)
from bridge.spine_io import ROOT, read_fred_csv
from bridge.weather.io import load_weather_manifest, open_meteo_archive


# Promotion gates — Bonferroni over 2 signals × 3 desks = 6 family tests
MIN_OBS = 120
MIN_IC = 0.04
MIN_HIT = 0.52
FAMILY_TESTS = 6
MIN_T = bonferroni_t_threshold(FAMILY_TESTS)
MIN_T_NW = 2.5
NEWEY_WEST_LAGS = 7


def _hdd(temp_c: float, base: float) -> float:
    return max(0.0, base - temp_c)


def _load_or_fetch_archive(
    base: Path,
    zone_id: str,
    lat: float,
    lon: float,
    start: date,
    end: date,
) -> dict[str, list[Any]]:
    cache_dir = base / "cache" / "weather" / "backtest"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path = cache_dir / f"archive_{zone_id}.json"

    if cache_path.is_file():
        cached = json.loads(cache_path.read_text(encoding="utf-8"))
        c_start = cached.get("start")
        c_end = cached.get("end")
        if c_start == start.isoformat() and c_end == end.isoformat():
            return cached.get("daily", {})

    raw = open_meteo_archive(lat, lon, start, end)
    daily = raw.get("daily", {})
    payload = {
        "zone_id": zone_id,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "fetched_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "daily": daily,
    }
    cache_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return daily


def _daily_hdd_series(
    daily: dict[str, list[Any]], hdd_base: float, window: int = 7, clim: int = 30
) -> dict[str, float]:
    times = daily.get("time") or []
    temps = daily.get("temperature_2m_mean") or []
    if len(times) < window + clim:
        return {}

    hdd_by_day: list[tuple[str, float]] = []
    for t, temp in zip(times, temps):
        if temp is None:
            continue
        hdd_by_day.append((t, _hdd(float(temp), hdd_base)))

    out: dict[str, float] = {}
    for i in range(window + clim - 1, len(hdd_by_day)):
        d, _ = hdd_by_day[i]
        roll = [hdd_by_day[j][1] for j in range(i - window + 1, i + 1)]
        climat = [hdd_by_day[j][1] for j in range(i - clim + 1, i + 1)]
        hdd_7 = sum(roll) / window
        hdd_clim = sum(climat) / clim
        out[d] = hdd_7 - hdd_clim
    return out


def _daily_wind_series(daily: dict[str, list[Any]]) -> dict[str, float]:
    times = daily.get("time") or []
    winds = daily.get("windspeed_10m_max") or daily.get("wind_speed_10m_max") or []
    out: dict[str, float] = {}
    for t, w in zip(times, winds):
        if w is not None:
            out[t] = float(w)
    return out


def _rolling_zscore(values: dict[str, float], window: int = 30) -> dict[str, float]:
    """Rolling z-score anomaly — removes level bias for wind-like features."""
    dates = sorted(values.keys())
    out: dict[str, float] = {}
    for i in range(window - 1, len(dates)):
        d = dates[i]
        chunk = [values[dates[j]] for j in range(i - window + 1, i + 1)]
        m = sum(chunk) / len(chunk)
        var = sum((v - m) ** 2 for v in chunk) / max(1, len(chunk) - 1)
        sd = var ** 0.5
        out[d] = (values[d] - m) / sd if sd > 1e-9 else 0.0
    return out


def _eu_weighted_series(
    zone_series: dict[str, dict[str, float]], zones: list[dict[str, Any]], key: str
) -> dict[str, float]:
    """Aggregate per-date weighted feature across EU zones."""
    weights: dict[str, float] = {}
    for z in zones:
        if z.get("region") != "EU":
            continue
        zid = z["id"]
        if zid not in zone_series:
            continue
        w = float(z.get(key, 0.0))
        if w <= 0:
            continue
        weights[zid] = w

    if not weights:
        return {}

    w_sum = sum(weights.values())
    dates: set[str] = set()
    for zid in weights:
        dates.update(zone_series[zid].keys())

    out: dict[str, float] = {}
    for d in sorted(dates):
        num = 0.0
        den = 0.0
        for zid, w in weights.items():
            v = zone_series[zid].get(d)
            if v is None:
                continue
            num += v * w
            den += w
        if den > 0:
            out[d] = num / den
    return out


def _desk_zone_map(manifest: dict[str, Any]) -> dict[str, str]:
    """power_desk → primary zone_id (first match)."""
    m: dict[str, str] = {}
    for z in manifest.get("zones", []):
        desk = z.get("power_desk")
        if desk and desk not in m:
            m[str(desk)] = z["id"]
    return m


def _forward_returns(prices: dict[str, float], horizon: int = 1) -> dict[str, float]:
    """DA price change (EUR/MWh) on consecutive calendar days — epftoolbox convention."""
    dates = sorted(prices.keys())
    out: dict[str, float] = {}
    for i, d in enumerate(dates):
        if i + horizon >= len(dates):
            break
        d_next = dates[i + horizon]
        try:
            gap = (date.fromisoformat(d_next) - date.fromisoformat(d)).days
        except ValueError:
            continue
        if gap != horizon:
            continue
        p0 = prices[d]
        p1 = prices[d_next]
        out[d] = p1 - p0
    return out


def _same_day_change(prices: dict[str, float]) -> dict[str, float]:
    """Contemporaneous DA change: price[d] - price[d-1] on consecutive days."""
    dates = sorted(prices.keys())
    out: dict[str, float] = {}
    for i in range(1, len(dates)):
        d_prev, d = dates[i - 1], dates[i]
        try:
            gap = (date.fromisoformat(d) - date.fromisoformat(d_prev)).days
        except ValueError:
            continue
        if gap != 1:
            continue
        out[d] = prices[d] - prices[d_prev]
    return out


def _align(signal: dict[str, float], rets: dict[str, float]) -> tuple[list[float], list[float]]:
    xs, ys = [], []
    for d in sorted(set(signal.keys()) & set(rets.keys())):
        xs.append(signal[d])
        ys.append(rets[d])
    return xs, ys


def _verdict(
    ic: float,
    t_stat: float,
    hr: float,
    n: int,
    expected_sign: int,
    *,
    event_spread: float | None = None,
    t_nw: float | None = None,
) -> dict[str, Any]:
    sign_ok = (ic * expected_sign) > 0
    event_ok = event_sign_ok(event_spread, expected_sign) if event_spread is not None else True
    t_eff = abs(t_nw) if t_nw is not None else abs(t_stat)
    passed = (
        n >= MIN_OBS
        and sign_ok
        and event_ok
        and abs(ic) >= MIN_IC
        and t_eff >= MIN_T
        and t_eff >= MIN_T_NW
        and hr >= MIN_HIT
    )
    return {
        "n_obs": n,
        "ic_pearson": round(ic, 4),
        "t_stat": round(t_stat, 3),
        "t_nw": round(t_nw, 3) if t_nw is not None else None,
        "hit_rate": round(hr, 4),
        "sign_ok": sign_ok,
        "event_sign_ok": event_ok,
        "passed": passed,
        "gates": {
            "min_obs": MIN_OBS,
            "min_ic": MIN_IC,
            "min_hit": MIN_HIT,
            "min_t_bonferroni": MIN_T,
            "min_t_nw": MIN_T_NW,
            "family_tests": FAMILY_TESTS,
        },
    }


def _backtest_pair(
    signal_id: str,
    feature: dict[str, float],
    desk: str,
    prices: dict[str, float],
    expected_sign: int,
    hypothesis: str,
    *,
    return_mode: str = "forward",
) -> dict[str, Any]:
    rets = (
        _same_day_change(prices)
        if return_mode == "same_day"
        else _forward_returns(prices, horizon=1)
    )
    xs, ys = _align(feature, rets)
    ic, t_stat, n = pearson(xs, ys)
    nw = pearson_with_nw(xs, ys, nw_lags=NEWEY_WEST_LAGS)
    ic_s = spearman(xs, ys)
    slope, intercept, _ = ols_slope(xs, ys)
    hr = hit_rate_expected(xs, ys, expected_sign)
    ev = event_mean(xs, ys)
    spread = float(ev.get("spread", 0.0))
    aligned_dates = sorted(set(feature.keys()) & set(rets.keys()))[:n]
    seasons = ic_by_season(xs, ys, aligned_dates) if len(aligned_dates) == n else {}
    return {
        "signal_id": signal_id,
        "desk": desk,
        "hypothesis": hypothesis,
        "expected_sign": expected_sign,
        "return_mode": return_mode,
        "regression": {"slope": round(slope, 6), "intercept": round(intercept, 6)},
        "ic_spearman": round(ic_s, 4),
        "newey_west": nw,
        "seasonal_ic": seasons,
        "event_study": ev,
        "forward_return": summarize(ys),
        "verdict": _verdict(
            ic, t_stat, hr, n, expected_sign,
            event_spread=spread,
            t_nw=float(nw.get("t_nw", 0)),
        ),
    }


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    manifest = load_weather_manifest(base)
    hdd_base = float(manifest.get("hdd_base_c", 18.0))
    wind_thr = float(manifest.get("wind_ramp_threshold_ms", 8.0))

    power_desks = ["PDE", "PFR", "PIT"]
    price_by_desk: dict[str, dict[str, float]] = {}
    min_date: date | None = None
    max_date: date | None = None

    for desk in power_desks:
        rows = read_fred_csv(base / "cache" / f"{desk}.csv")
        if not rows:
            continue
        prices = {d: v for d, v in rows}
        price_by_desk[desk] = prices
        d0 = date.fromisoformat(rows[0][0])
        d1 = date.fromisoformat(rows[-1][0])
        min_date = d0 if min_date is None else min(min_date, d0)
        max_date = d1 if max_date is None else max(max_date, d1)

    if not price_by_desk or min_date is None or max_date is None:
        return {
            "ok": False,
            "module": "backtest_pwr_signals",
            "message": "missing power CSV (PDE/PFR/PIT)",
            "outputs": [],
        }

    end = min(max_date, date.today() - timedelta(days=5))
    start = min_date

    eu_zones = [z for z in manifest.get("zones", []) if z.get("region") == "EU"]
    hdd_by_zone: dict[str, dict[str, float]] = {}
    wind_by_zone: dict[str, dict[str, float]] = {}
    fetch_errors: list[str] = []

    for z in eu_zones:
        zid = z["id"]
        try:
            daily = _load_or_fetch_archive(
                base, zid, float(z["lat"]), float(z["lon"]), start, end
            )
            hdd_by_zone[zid] = _daily_hdd_series(daily, hdd_base)
            wind_by_zone[zid] = _daily_wind_series(daily)
        except Exception as exc:
            fetch_errors.append(f"{zid}:{exc}")

    eu_hdd = _eu_weighted_series(hdd_by_zone, eu_zones, "weight_hdd")
    desk_zone = _desk_zone_map(manifest)

    pwr02_results: list[dict[str, Any]] = []
    pwr02_same_day: list[dict[str, Any]] = []
    for desk, prices in price_by_desk.items():
        pwr02_results.append(
            _backtest_pair(
                "PWR-02",
                eu_hdd,
                desk,
                prices,
                expected_sign=+1,
                hypothesis="EU HDD anomaly ↑ → DA price ↑ (demand)",
                return_mode="forward",
            )
        )
        pwr02_same_day.append(
            _backtest_pair(
                "PWR-02",
                eu_hdd,
                desk,
                prices,
                expected_sign=+1,
                hypothesis="EU HDD anomaly ↑ → same-day DA price ↑",
                return_mode="same_day",
            )
        )

    pwr01_results: list[dict[str, Any]] = []
    for desk, prices in price_by_desk.items():
        zid = desk_zone.get(desk)
        if not zid or zid not in wind_by_zone:
            continue
        wind_anom = _rolling_zscore(wind_by_zone[zid])
        pwr01_results.append(
            _backtest_pair(
                "PWR-01",
                wind_anom,
                desk,
                prices,
                expected_sign=-1,
                hypothesis=f"Zone {zid} wind anomaly ↑ → DA price ↓ (renewables)",
                return_mode="forward",
            )
        )

    # Threshold-based hit rate for live alert rule (wind > 8 m/s)
    wind_alerts: list[dict[str, Any]] = []
    for desk, prices in price_by_desk.items():
        zid = desk_zone.get(desk)
        if not zid or zid not in wind_by_zone:
            continue
        rets = _forward_returns(prices)
        xs, ys = _align(wind_by_zone[zid], rets)
        high = [(x, y) for x, y in zip(xs, ys) if x >= wind_thr]
        if len(high) >= 10:
            mean_ret = sum(y for _, y in high) / len(high)
            wind_alerts.append({
                "desk": desk,
                "zone": zid,
                "threshold_ms": wind_thr,
                "n_events": len(high),
                "mean_fwd_return": round(mean_ret, 5),
            })

    promotions: list[dict[str, Any]] = []
    for r in pwr02_results + pwr01_results:
        v = r["verdict"]
        promotions.append({
            "signal_id": r["signal_id"],
            "desk": r["desk"],
            "status": "promote" if v["passed"] else "reject",
            "ic": v["ic_pearson"],
            "hit_rate": v["hit_rate"],
            "n_obs": v["n_obs"],
        })

    any_pass = any(p["status"] == "promote" for p in promotions)
    pwr02_pass = any(
        p["status"] == "promote" for p in promotions if p["signal_id"] == "PWR-02"
    )
    pwr01_pass = any(
        p["status"] == "promote" for p in promotions if p["signal_id"] == "PWR-01"
    )

    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "sample": {"start": start.isoformat(), "end": end.isoformat(), "desks": power_desks},
        "PWR-02": {
            "feature": "eu_hdd_anom_7d_vs_30d",
            "return_alignment": "forward (d→d+1) primary; same_day diagnostic",
            "results": pwr02_results,
            "same_day_results": pwr02_same_day,
            "any_desk_passed": pwr02_pass,
        },
        "PWR-01": {
            "feature": "zone_wind_zscore_30d",
            "threshold_live_alert_ms": wind_thr,
            "results": pwr01_results,
            "threshold_events": wind_alerts,
            "any_desk_passed": pwr01_pass,
            "note": "Raw wind level rejected — use PWR-01b delta for live",
        },
        "promotions": promotions,
        "methodology_note": (
            "v1 daily target Δ DA is weak gate timing; see PWR-01-v2 hourly "
            "(delta→imb−DA). NW t + seasonal IC flag winter confounding."
        ),
        "fetch_errors": fetch_errors[:6],
        "next": (
            "Add passing signals to config/signals.json manually"
            if any_pass
            else "Do not promote — signals fail statistical gates"
        ),
    }

    out_path = base / "cache" / "spine" / "modules" / "backtest_pwr_signals.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    cand_path = base / "cache" / "spine" / "signals_candidate.json"
    candidates = [
        {
            "id": p["signal_id"],
            "desk": p["desk"],
            "status": p["status"],
            "metric": "backtest_ic",
            "value": p["ic"],
            "hit_rate": p["hit_rate"],
            "n_obs": p["n_obs"],
            "source": "bridge/backtest/pwr_signals.py",
        }
        for p in promotions
        if p["status"] == "promote"
    ]
    cand_path.write_text(
        json.dumps({"built_at": payload["built_at"], "candidates": candidates}, indent=2),
        encoding="utf-8",
    )

    msg = f"PWR-02={'PASS' if pwr02_pass else 'FAIL'} PWR-01={'PASS' if pwr01_pass else 'FAIL'}"
    if pwr02_results:
        best = max(pwr02_results, key=lambda r: abs(r["verdict"]["ic_pearson"]))
        msg += f" | best IC {best['desk']}={best['verdict']['ic_pearson']:+.3f}"

    return {
        "ok": len(pwr02_results) > 0,
        "module": "backtest_pwr_signals",
        "message": msg,
        "outputs": [
            str(out_path.relative_to(base)).replace("\\", "/"),
            str(cand_path.relative_to(base)).replace("\\", "/"),
        ],
    }
