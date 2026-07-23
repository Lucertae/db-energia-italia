"""PWR-01 v1 target artifact diagnostic — wrong target → spurious robust signal.

Demonstrates: wind_D depresses P(D) contemporaneously; Δ(D+1)=P(D+1)−P(D) inherits
positive IC as mechanical base/mean-reversion artifact, not economic forecast edge.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from bridge.backtest.pwr_signals import (
    NEWEY_WEST_LAGS,
    _align,
    _daily_wind_series,
    _desk_zone_map,
    _forward_returns,
    _load_or_fetch_archive,
    _rolling_zscore,
)
from bridge.backtest.stats import ols_slope, pearson, pearson_with_nw, summarize
from bridge.spine_io import ROOT, read_fred_csv
from bridge.weather.io import load_weather_manifest


def _same_day_level(prices: dict[str, float]) -> dict[str, float]:
    """P(D) aligned to date D."""
    return dict(prices)


def _next_day_level(prices: dict[str, float]) -> dict[str, float]:
    dates = sorted(prices.keys())
    out: dict[str, float] = {}
    for i, d in enumerate(dates):
        if i + 1 >= len(dates):
            break
        d_next = dates[i + 1]
        try:
            if (date.fromisoformat(d_next) - date.fromisoformat(d)).days != 1:
                continue
        except ValueError:
            continue
        out[d] = prices[d_next]
    return out


def _ols_controlled(y: list[float], x: list[float], control: list[float]) -> dict[str, float]:
    """OLS y ~ x + control; partial IC = corr(resid_y, resid_x) after removing control."""
    n = min(len(y), len(x), len(control))
    if n < 10:
        return {"coef_x_partial": 0.0, "ic_partial": 0.0, "t_partial": 0.0, "n": n}
    b_cy, a_cy, _ = ols_slope(control[:n], y[:n])
    b_cx, a_cx, _ = ols_slope(control[:n], x[:n])
    y_res = [y[i] - (a_cy + b_cy * control[i]) for i in range(n)]
    x_res = [x[i] - (a_cx + b_cx * control[i]) for i in range(n)]
    ic, t, _ = pearson(x_res, y_res)
    slope, _, _ = ols_slope(x_res, y_res)
    return {"coef_x_partial": round(slope, 4), "ic_partial": round(ic, 4), "t_partial": round(t, 3), "n": n}


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    manifest = load_weather_manifest(base)
    desk_zone = _desk_zone_map(manifest)
    desks = ["PDE", "PFR", "PIT"]
    results: list[dict[str, Any]] = []

    for desk in desks:
        rows = read_fred_csv(base / "cache" / f"{desk}.csv")
        if not rows:
            continue
        prices = {d: v for d, v in rows}
        zid = desk_zone.get(desk)
        if not zid:
            continue

        start = date.fromisoformat(rows[0][0])
        end = min(date.fromisoformat(rows[-1][0]), date.today())
        eu_zones = [z for z in manifest.get("zones", []) if z.get("region") == "EU"]
        zmeta = next((z for z in eu_zones if z["id"] == zid), None)
        if not zmeta:
            continue

        daily = _load_or_fetch_archive(
            base, zid, float(zmeta["lat"]), float(zmeta["lon"]), start, end
        )
        wind_raw = _daily_wind_series(daily)
        wind = _rolling_zscore(wind_raw)

        p_d = _same_day_level(prices)
        p_d1 = _next_day_level(prices)
        delta_d1 = _forward_returns(prices)

        # A) contemporaneous: wind_D vs P(D)
        xs_c, ys_c = _align(wind, p_d)
        ic_c, t_c, n_c = pearson(xs_c, ys_c)
        nw_c = pearson_with_nw(xs_c, ys_c, nw_lags=NEWEY_WEST_LAGS)

        # B) forward delta (v1 target): wind_D vs Δ(D+1)
        xs_d, ys_d = _align(wind, delta_d1)
        ic_d, t_d, n_d = pearson(xs_d, ys_d)
        nw_d = pearson_with_nw(xs_d, ys_d, nw_lags=NEWEY_WEST_LAGS)

        # C) level P(D+1) with control P(D)
        common = sorted(set(wind.keys()) & set(p_d1.keys()) & set(p_d.keys()))
        xs_l = [wind[d] for d in common]
        ys_l = [p_d1[d] for d in common]
        pc = [p_d[d] for d in common]
        partial = _ols_controlled(ys_l, xs_l, pc)

        artifact = (
            ic_c < -0.05
            and ic_d > 0.05
            and abs(partial.get("ic_partial", 0)) < abs(ic_d)
        )

        results.append({
            "desk": desk,
            "zone": zid,
            "A_contemporaneous_wind_vs_P_D": {
                "hypothesis": "wind ↑ → P(D) ↓ (same-day merit order)",
                "ic": round(ic_c, 4),
                "t_nw": nw_c.get("t_nw"),
                "n": n_c,
                "mean_P_D": summarize(ys_c),
            },
            "B_v1_target_wind_vs_delta_D1": {
                "hypothesis": "wind ↑ → Δ(D+1) ↑ (v1 — WRONG timing/target)",
                "ic": round(ic_d, 4),
                "t_nw": nw_d.get("t_nw"),
                "n": n_d,
                "mean_delta": summarize(ys_d),
            },
            "C_level_P_D1_controlling_P_D": {
                "hypothesis": "partial effect of wind on P(D+1) | P(D)",
                **partial,
            },
            "artifact_confirmed": artifact,
            "interpretation": (
                "Mechanical artifact: high wind lowers P(D), inflating Δ(D+1)=P(D+1)−P(D). "
                "Positive IC on delta is reflection of contemporaneous effect, not forecast edge."
                if artifact
                else "Pattern differs from canonical artifact — inspect manually."
            ),
        })

    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "signal_id": "PWR-01-v1-diagnostic",
        "doc": "docs/backtest-target-artifact.md",
        "test_case": "wrong_target_spurious_signal",
        "results": results,
        "all_desks_artifact": all(r.get("artifact_confirmed") for r in results) if results else False,
    }

    out_path = base / "cache" / "spine" / "modules" / "backtest_pwr_v1_diagnostic.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    pde = next((r for r in results if r["desk"] == "PDE"), {})
    ic_c = pde.get("A_contemporaneous_wind_vs_P_D", {}).get("ic")
    ic_d = pde.get("B_v1_target_wind_vs_delta_D1", {}).get("ic")
    ic_p = pde.get("C_level_P_D1_controlling_P_D", {}).get("ic_partial")
    pde_ok = pde.get("artifact_confirmed", False)
    msg = f"PDE artifact={'YES' if pde_ok else 'NO'}"
    if ic_c is not None and ic_d is not None:
        msg += f" | contemp={ic_c:+.3f} delta={ic_d:+.3f}"
    if ic_p is not None:
        msg += f" partial={ic_p:+.3f}"

    return {
        "ok": len(results) > 0,
        "module": "backtest_pwr_v1_diagnostic",
        "message": msg,
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
