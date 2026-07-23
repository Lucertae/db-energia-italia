"""PWR-01 v2 backtest: hourly delta (OM MW − published MW) → DA/imbalance spread.

Methodology:
- Signal at gate: normalized wind forecast delta via cubic power curve
- Target: imbalance_long − DA (EUR/MWh) per delivery hour — not Δ DA daily
- Newey-West t (lag 7), seasonal IC, Bonferroni across desks
- Train 2021–2024 / test 2025+ temporal split
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.backtest.stats import (
    block_bootstrap_conditional_ic,
    bonferroni_t_threshold,
    economic_edge,
    event_mean,
    event_sign_ok,
    hit_rate_expected,
    hit_rate_signed,
    ic_by_season,
    pearson_ic_stats,
    pearson_with_nw,
    spearman,
    summarize,
)
from bridge.energy.capacity import capacity_mw_for_hour
from bridge.energy.entsoe_util import load_power_wind_config
from bridge.energy.gate import gate_hour_key
from bridge.energy.power_curve import delta_norm, in_steep_curve_zone, wind_to_mw
from bridge.energy.wind_grid import load_grid_wind_hourly
from bridge.spine_io import ROOT


def _hour_key_utc(ts: str) -> str:
    """Normalize ISO timestamp to UTC hour bucket YYYY-MM-DDTHH."""
    try:
        import pandas as pd

        t = pd.Timestamp(ts)
        if t.tzinfo is None:
            t = t.tz_localize("UTC")
        else:
            t = t.tz_convert("UTC")
        return t.strftime("%Y-%m-%dT%H")
    except Exception:
        return str(ts)[:13]


def _load_hourly_series(cache_dir: Path, value_key: str) -> dict[str, float]:
    out: dict[str, float] = {}
    if not cache_dir.is_dir():
        return out
    for path in sorted(cache_dir.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        keys = value_key if isinstance(value_key, list) else [value_key]
        vals = None
        for k in keys:
            if k in data:
                vals = data[k]
                break
        if vals is None:
            continue
        for ts, v in zip(data.get("timestamps", data.get("time", [])), vals):
            if v is None:
                continue
            out[_hour_key_utc(str(ts))] = float(v)
    return out


def _load_om_wind_legacy(base: Path, zone_id: str) -> dict[str, float]:
    out: dict[str, float] = {}
    d = base / "cache" / "weather" / "open_meteo_hourly" / zone_id
    if not d.is_dir():
        return out
    for path in sorted(d.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue
        for ts, w in zip(data.get("time", []), data.get("windspeed_10m", [])):
            if w is None:
                continue
            out[_hour_key_utc(str(ts))] = float(w)
    return out


def _load_target_spread(
    base: Path,
    desk_id: str,
    desk_cfg: dict[str, Any],
    da: dict[str, float],
    imb: dict[str, float],
    id_idx: dict[str, float],
) -> tuple[dict[str, float], str]:
    """Build per-delivery-hour target spread and label."""
    target_mode = str(desk_cfg.get("target", "imb_minus_da"))
    if target_mode == "id_minus_da" and id_idx:
        spread = {hk: id_idx[hk] - da[hk] for hk in set(id_idx.keys()) & set(da.keys())}
        return spread, "id_minus_da"
    spread = {hk: imb[hk] - da[hk] for hk in set(imb.keys()) & set(da.keys())}
    label = "imb_minus_da" if target_mode == "id_minus_da" else target_mode
    if target_mode == "id_minus_da":
        label = "imb_minus_da (ID cache empty — fallback)"
    return spread, label


def _align_v2(
    om_wind: dict[str, float],
    pub_wind: dict[str, float],
    target_spread: dict[str, float],
    desk_cfg: dict[str, Any],
    base: Path,
    fleet_cfg: dict[str, Any],
    gate_cfg: dict[str, Any],
) -> tuple[list[float], list[float], list[str], list[float], list[str]]:
    country = str(desk_cfg.get("country", ""))
    cap_fallback = float(desk_cfg.get("capacity_mw_fallback", desk_cfg.get("capacity_mw", 1)))
    cut_in = float(fleet_cfg.get("cut_in_ms", 3))
    rated = float(fleet_cfg.get("rated_ms", 12))
    cut_out = float(fleet_cfg.get("cut_out_ms", 25))
    sigma = float(fleet_cfg.get("smooth_sigma_ms", 2.0))
    gate_hour = int(gate_cfg.get("hour_utc", 10))
    gate_minute = int(gate_cfg.get("minute_utc", 30))
    use_gate = bool(gate_cfg.get("enabled", True))

    xs: list[float] = []
    ys: list[float] = []
    dates: list[str] = []
    winds: list[float] = []

    hour_keys: list[str] = []

    delivery_hours = sorted(set(target_spread.keys()))
    for dhk in delivery_hours:
        gk = gate_hour_key(dhk, gate_hour_utc=gate_hour, gate_minute_utc=gate_minute) if use_gate else dhk
        if gk not in om_wind or gk not in pub_wind:
            continue
        cap = capacity_mw_for_hour(base, country, dhk, cap_fallback)
        w_ms = om_wind[gk]
        om_mw = wind_to_mw(
            w_ms, cap, cut_in_ms=cut_in, rated_ms=rated, cut_out_ms=cut_out,
            fleet=True, smooth_sigma_ms=sigma,
        )
        pub_mw = pub_wind[gk]
        signal = delta_norm(om_mw, pub_mw, cap)
        spread = target_spread[dhk]
        xs.append(signal)
        ys.append(spread)
        dates.append(dhk[:10] if len(dhk) >= 10 else dhk)
        hour_keys.append(dhk)
        winds.append(w_ms)
    return xs, ys, dates, winds, hour_keys


def _conditional_mask_fn(
    decile: float,
    steep_lo: float,
    steep_hi: float,
) -> Any:
    """Return mask function for block bootstrap (operates on list copies)."""

    def _mask(xs: list[float], winds: list[float]) -> list[bool]:
        if len(xs) != len(winds) or not xs:
            return []
        steep_idx = [
            i for i, w in enumerate(winds)
            if in_steep_curve_zone(w, lo_ms=steep_lo, hi_ms=steep_hi)
        ]
        if len(steep_idx) < 20:
            return [False] * len(xs)
        abs_steep = sorted(abs(xs[i]) for i in steep_idx)
        thr_i = min(int(len(abs_steep) * decile), len(abs_steep) - 1)
        thr = abs_steep[thr_i]
        return [
            in_steep_curve_zone(w, lo_ms=steep_lo, hi_ms=steep_hi) and abs(x) >= thr
            for x, w in zip(xs, winds)
        ]

    return _mask


def _conditional_mask(
    xs: list[float],
    winds: list[float],
    *,
    decile: float,
    steep_lo: float,
    steep_hi: float,
) -> list[bool]:
    """Top decile |delta| within steep fleet-curve wind band (4–11 m/s)."""
    if len(xs) != len(winds) or not xs:
        return []
    steep_idx = [
        i for i, w in enumerate(winds)
        if in_steep_curve_zone(w, lo_ms=steep_lo, hi_ms=steep_hi)
    ]
    if len(steep_idx) < 20:
        return [False] * len(xs)
    abs_steep = sorted(abs(xs[i]) for i in steep_idx)
    thr_i = min(int(len(abs_steep) * decile), len(abs_steep) - 1)
    thr = abs_steep[thr_i]
    return [
        in_steep_curve_zone(w, lo_ms=steep_lo, hi_ms=steep_hi) and abs(x) >= thr
        for x, w in zip(xs, winds)
    ]


def _filter_lists(
    xs: list[float], ys: list[float], dates: list[str], mask: list[bool]
) -> tuple[list[float], list[float], list[str]]:
    return (
        [x for x, m in zip(xs, mask) if m],
        [y for y, m in zip(ys, mask) if m],
        [d for d, m in zip(dates, mask) if m],
    )


def _split_sample(
    xs: list[float],
    ys: list[float],
    dates: list[str],
    *,
    train_end: str,
    test_start: str,
) -> tuple[tuple[list[float], list[float], list[str]], tuple[list[float], list[float], list[str]], dict[str, str]]:
    """Temporal split; falls back to 75/25 on unique dates if fixed cutoffs yield empty test."""
    train_x, train_y, train_d = [], [], []
    test_x, test_y, test_d = [], [], []
    for x, y, d in zip(xs, ys, dates):
        if d <= train_end:
            train_x.append(x)
            train_y.append(y)
            train_d.append(d)
        elif d >= test_start:
            test_x.append(x)
            test_y.append(y)
            test_d.append(d)

    if len(test_x) < 120:
        uniq = sorted(set(dates))
        if len(uniq) >= 8:
            cut_i = int(len(uniq) * 0.75)
            cut = uniq[cut_i - 1]
            train_x, train_y, train_d, test_x, test_y, test_d = [], [], [], [], [], []
            for x, y, d in zip(xs, ys, dates):
                if d <= cut:
                    train_x.append(x)
                    train_y.append(y)
                    train_d.append(d)
                else:
                    test_x.append(x)
                    test_y.append(y)
                    test_d.append(d)
            meta = {"mode": "adaptive_75_25", "cut_date": cut, "reason": "fixed test window empty (imbalance history)"}
            return (train_x, train_y, train_d), (test_x, test_y, test_d), meta

    return (train_x, train_y, train_d), (test_x, test_y, test_d), {"mode": "fixed", "train_end": train_end, "test_start": test_start}


def _indices_for_dates(dates: list[str], date_set: set[str]) -> list[int]:
    return [i for i, d in enumerate(dates) if d in date_set]


def _subset(xs: list[float], ys: list[float], winds: list[float], idx: list[int]) -> tuple[list[float], list[float], list[float]]:
    return (
        [xs[i] for i in idx],
        [ys[i] for i in idx],
        [winds[i] for i in idx],
    )


def _verdict_v2(
    stats: dict[str, Any],
    hr_signed: float,
    hr_high: float,
    ev_spread: float,
    ic_spear: float,
    econ: dict[str, Any],
    *,
    expected_sign: int,
    min_obs: int,
    min_ic: float,
    min_hit: float,
    min_t: float,
    min_t_bonf: float,
    min_mean_edge: float,
    split: str,
    inference: str,
) -> dict[str, Any]:
    ic = float(stats.get("ic", 0))
    if inference == "block_bootstrap":
        t_eff = abs(float(stats.get("t_boot", 0)))
        t_label = "t_boot"
    else:
        t_eff = abs(float(stats.get("t_ic", stats.get("t_nw", 0))))
        t_label = "t_ic"
    n = int(stats.get("n_cond", stats.get("n", 0)))
    sign_ok = (ic * expected_sign) > 0
    event_ok = event_sign_ok(ev_spread, expected_sign)
    tail_signal = abs(ic_spear) < abs(ic) * 0.5 and abs(ic) >= min_ic
    econ_ok = bool(econ.get("pass")) and float(econ.get("mean_edge", 0)) >= min_mean_edge
    passed = (
        n >= min_obs
        and sign_ok
        and event_ok
        and abs(ic) >= min_ic
        and hr_signed >= min_hit
        and t_eff >= min_t
        and t_eff >= min_t_bonf
        and econ_ok
        and not tail_signal
    )
    return {
        "split": split,
        "inference": inference,
        "n_obs": n,
        "ic_pearson": ic,
        "ic_spearman": round(ic_spear, 4),
        "tail_signal_warning": tail_signal,
        "t_primary": round(t_eff, 3),
        "t_ic": stats.get("t_ic"),
        "t_boot": stats.get("t_boot"),
        "hit_rate_signed": round(hr_signed, 4),
        "hit_rate_high_quartile": round(hr_high, 4),
        "economic": econ,
        "sign_ok": sign_ok,
        "event_sign_ok": event_ok,
        "economic_ok": econ_ok,
        "passed": passed,
        "gates": {
            "min_obs": min_obs,
            "min_ic": min_ic,
            "min_hit_signed": min_hit,
            "min_t": min_t,
            "min_t_bonferroni": min_t_bonf,
            "min_mean_edge_eur_mwh": min_mean_edge,
        },
    }


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    cfg = load_power_wind_config(base)
    bt = cfg.get("backtest", {})
    train_end = str(bt.get("train_end", "2024-12-31"))
    test_start = str(bt.get("test_start", "2025-01-01"))
    nw_lags = int(bt.get("newey_west_lags", 7))
    min_obs = int(bt.get("min_obs_hourly", 500))
    min_ic = float(bt.get("min_ic", 0.04))
    min_hit = float(bt.get("min_hit", 0.52))
    min_t_nw = float(bt.get("min_t_nw", 2.5))
    n_family = int(bt.get("family_tests", 6))
    min_t_bonf = float(bt.get("min_t_bonferroni", bonferroni_t_threshold(n_family)))
    min_obs_cond = int(bt.get("min_obs_conditional", 200))
    inf_cfg = bt.get("conditional_inference", {})
    block_hours = int(inf_cfg.get("block_hours", 24))
    n_boot = int(inf_cfg.get("n_boot", 400))
    min_t_boot = float(inf_cfg.get("min_t_boot", 2.0))
    econ_cfg = bt.get("economic_gate", {})
    cost_eur = float(econ_cfg.get("cost_eur_mwh", 1.5))
    min_mean_edge = float(econ_cfg.get("min_mean_edge_eur_mwh", 0.5))
    cond_cfg = bt.get("conditional", {})
    cond_decile = float(cond_cfg.get("delta_abs_decile", 0.9))
    steep_lo = float(cond_cfg.get("wind_steep_lo_ms", 4.0))
    steep_hi = float(cond_cfg.get("wind_steep_hi_ms", 11.0))
    primary_cond = bool(cond_cfg.get("primary_gate", True))
    fleet_cfg = bt.get("fleet_curve", {})
    gate_cfg = bt.get("gate", {"enabled": True, "hour_utc": 10, "minute_utc": 30})
    expected_sign = -1

    results: list[dict[str, Any]] = []
    promotions: list[dict[str, Any]] = []

    for desk_id, desk_cfg in cfg.get("desks", {}).items():
        pub = _load_hourly_series(
            base / "cache" / "weather" / "entsoe_hourly" / "wind_published" / desk_id,
            "wind_mw",
        )
        da = _load_hourly_series(
            base / "cache" / "weather" / "entsoe_hourly" / "da" / desk_id,
            "da_eur_mwh",
        )
        imb = _load_hourly_series(
            base / "cache" / "weather" / "entsoe_hourly" / "imbalance" / desk_id,
            "imb_long",
        )
        id_idx = _load_hourly_series(
            base / "cache" / "weather" / "entsoe_hourly" / "id_index" / desk_id,
            "id_eur_mwh",
        )
        target_spread, target_label = _load_target_spread(base, desk_id, desk_cfg, da, imb, id_idx)
        om = load_grid_wind_hourly(
            base, desk_id, desk_cfg.get("grid_points", []),
            legacy_zone=desk_cfg.get("om_legacy_zone"),
        )
        if not om:
            legacy = desk_cfg.get("om_legacy_zone") or desk_cfg.get("om_zone_id")
            if legacy:
                om = _load_om_wind_legacy(base, str(legacy))

        xs, ys, dates, winds, hour_keys = _align_v2(
            om, pub, target_spread, desk_cfg, base, fleet_cfg, gate_cfg,
        )
        if len(xs) < 50:
            results.append({
                "signal_id": "PWR-01-v2",
                "desk": desk_id,
                "n_hours": len(xs),
                "verdict": {"passed": False, "note": "insufficient hourly cache — run entsoe_hourly + om_hourly harvest"},
            })
            continue

        (tr_x, tr_y, tr_d), (te_x, te_y, te_d), split_meta = _split_sample(
            xs, ys, dates, train_end=train_end, test_start=test_start
        )
        desk_result: dict[str, Any] = {
            "signal_id": "PWR-01-v2",
            "desk": desk_id,
            "hypothesis": "delta_norm>0 (OM>published at gate) → imbalance−DA ↓",
            "expected_sign": expected_sign,
            "method": (
                f"multi-grid OM + fleet CF + gate D-1 {gate_cfg.get('hour_utc', 10)}:"
                f"{gate_cfg.get('minute_utc', 30):02d} UTC; target={target_label}"
            ),
            "target_effective": target_label,
            "gate": gate_cfg,
            "n_hours_total": len(xs),
            "grid_points": len(desk_cfg.get("grid_points", [])),
            "date_range": {"from": min(dates) if dates else None, "to": max(dates) if dates else None},
            "split_meta": split_meta,
            "coverage": {
                "om": len(om), "published": len(pub), "da": len(da),
                "imb": len(imb), "id_index": len(id_idx), "target_hours": len(target_spread),
            },
        }

        cond_mask_fn = _conditional_mask_fn(cond_decile, steep_lo, steep_hi)

        def _report_sample(
            split_name: str,
            sx: list[float],
            sy: list[float],
            sdates: list[str],
            sw: list[float] | None,
            *,
            conditional: bool,
            min_obs_gate: int,
        ) -> None:
            if len(sx) < 20:
                desk_result[f"{split_name}_sample"] = {"n": len(sx), "skipped": True}
                return
            ic_spear = spearman(sx, sy)
            hr_signed = hit_rate_signed(sx, sy, expected_sign)
            hr_high = hit_rate_expected(sx, sy, expected_sign)
            ev = event_mean(sx, sy)
            spread = float(ev.get("spread", 0))
            seasons = ic_by_season(sx, sy, sdates) if len(sdates) == len(sx) else {}
            econ = economic_edge(sx, sy, expected_sign, cost_eur_mwh=cost_eur)

            if conditional and sw is not None and len(sw) == len(sx):
                st = block_bootstrap_conditional_ic(
                    sx, sy, sw,
                    mask_fn=cond_mask_fn,
                    block_hours=block_hours,
                    n_boot=n_boot,
                )
                inference = "block_bootstrap"
                min_t = min_t_boot
            else:
                st = pearson_with_nw(sx, sy, nw_lags=nw_lags)
                inference = "pearson_t_contiguous"
                min_t = min_t_nw

            v = _verdict_v2(
                st, hr_signed, hr_high, spread, ic_spear, econ,
                expected_sign=expected_sign,
                min_obs=min_obs_gate,
                min_ic=min_ic,
                min_hit=min_hit,
                min_t=min_t,
                min_t_bonf=min_t_bonf,
                min_mean_edge=min_mean_edge,
                split=split_name,
                inference=inference,
            )
            desk_result[f"{split_name}_sample"] = {
                "stats": st,
                "ic_spearman": round(ic_spear, 4),
                "pearson_vs_spearman": {
                    "pearson": st.get("ic"),
                    "spearman": round(ic_spear, 4),
                    "tail_signal": abs(ic_spear) < abs(float(st.get("ic", 0))) * 0.5,
                },
                "hit_rate_signed": hr_signed,
                "hit_rate_high_quartile": hr_high,
                "event_study": ev,
                "target_spread": summarize(sy),
                "seasonal_ic": seasons,
                "economic": econ,
                "verdict": v,
            }

        for split_name, sx, sy, sdates in (
            ("full", xs, ys, dates),
            ("train", tr_x, tr_y, tr_d),
            ("test", te_x, te_y, te_d),
        ):
            min_g = min_obs if split_name != "test" else max(120, min_obs // 4)
            _report_sample(split_name, sx, sy, sdates, None, conditional=False, min_obs_gate=min_g)

        cmask = _conditional_mask(xs, winds, decile=cond_decile, steep_lo=steep_lo, steep_hi=steep_hi)
        cx, cy, cd = _filter_lists(xs, ys, dates, cmask)
        train_dates_set = set(tr_d)
        test_dates_set = set(te_d)
        ctr_idx = _indices_for_dates(dates, train_dates_set)
        cte_idx = _indices_for_dates(dates, test_dates_set)
        bx_tr, by_tr, bw_tr = _subset(xs, ys, winds, ctr_idx)
        bx_te, by_te, bw_te = _subset(xs, ys, winds, cte_idx)

        desk_result["conditional"] = {
            "filter": f"|delta|>p{int(cond_decile*100)} & wind∈[{steep_lo},{steep_hi}]m/s",
            "n_full": len(xs),
            "n_conditional": len(cx),
            "inference": "block_bootstrap",
            "block_hours": block_hours,
            "n_boot": n_boot,
        }
        for split_name, sx, sy, sdates, sw in (
            ("conditional_full", xs, ys, dates, winds),
            ("conditional_train", bx_tr, by_tr, tr_d, bw_tr),
            ("conditional_test", bx_te, by_te, te_d, bw_te),
        ):
            min_g = min_obs_cond if "test" not in split_name else max(80, min_obs_cond // 3)
            _report_sample(split_name, sx, sy, sdates, sw, conditional=True, min_obs_gate=min_g)

        test_v = desk_result.get("test_sample", {}).get("verdict", {})
        train_v = desk_result.get("train_sample", {}).get("verdict", {})
        cond_test_v = desk_result.get("conditional_test_sample", {}).get("verdict", {})
        cond_train_v = desk_result.get("conditional_train_sample", {}).get("verdict", {})
        if primary_cond and cond_test_v:
            promote = bool(cond_test_v.get("passed")) and bool(cond_train_v.get("sign_ok", cond_test_v.get("sign_ok")))
        else:
            promote = bool(test_v.get("passed")) and bool(train_v.get("sign_ok"))
        desk_result["promote"] = promote
        results.append(desk_result)
        promotions.append({
            "signal_id": "PWR-01-v2",
            "desk": desk_id,
            "status": "promote" if promote else "reject",
            "ic_test": (cond_test_v or test_v).get("ic_pearson"),
            "t_nw_test": (cond_test_v or test_v).get("t_boot") or (cond_test_v or test_v).get("t_ic"),
            "n_test": (cond_test_v or test_v).get("n_obs"),
            "gate": "conditional" if primary_cond else "full",
        })

    any_pass = any(r.get("promote") for r in results)
    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "signal_id": "PWR-01-v2",
        "target": "desk-specific: id_minus_da (PDE) or imb_minus_da; spread at delivery hour",
        "timing": "signal at D-1 gate (~10:30 UTC); OM/published wind from gate hour bucket",
        "gate": gate_cfg,
        "train_end": train_end,
        "test_start": test_start,
        "bonferroni": {"family_tests": n_family, "min_t": min_t_bonf},
        "conditional_inference": inf_cfg,
        "economic_gate": econ_cfg,
        "newey_west_lags": nw_lags,
        "note": "Full sample: t_ic (Pearson). Conditional: block bootstrap t_boot only.",
        "results": results,
        "promotions": promotions,
        "any_desk_passed": any_pass,
        "next": "Promote to config/signals.json only if test split passes all gates",
    }

    out_path = base / "cache" / "spine" / "modules" / "backtest_pwr_v2.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    cand_path = base / "cache" / "spine" / "signals_candidate.json"
    existing: list[dict] = []
    if cand_path.is_file():
        try:
            existing = json.loads(cand_path.read_text(encoding="utf-8")).get("candidates", [])
        except (json.JSONDecodeError, OSError):
            existing = []
    existing = [c for c in existing if c.get("id") != "PWR-01-v2"]
    existing.extend(
        {
            "id": "PWR-01-v2",
            "desk": p["desk"],
            "status": p["status"],
            "metric": "backtest_ic_test",
            "value": p.get("ic_test"),
            "t_nw": p.get("t_nw_test"),
            "n_obs": p.get("n_test"),
            "source": "bridge/backtest/pwr_v2.py",
        }
        for p in promotions
        if p["status"] == "promote"
    )
    cand_path.write_text(
        json.dumps({"built_at": payload["built_at"], "candidates": existing}, indent=2),
        encoding="utf-8",
    )

    best = max(
        results,
        key=lambda r: abs(
            (r.get("conditional_test_sample") or r.get("test_sample") or {}).get("stats", {}).get("ic", 0) or 0
        ),
        default={},
    )
    best_ic = (best.get("conditional_test_sample") or best.get("test_sample") or {}).get("stats", {}).get("ic")
    if best_ic is None and results:
        best = max(
            results,
            key=lambda r: abs((r.get("full_sample") or {}).get("stats", {}).get("ic", 0) or 0),
            default={},
        )
        best_ic = (best.get("full_sample") or {}).get("stats", {}).get("ic")
    msg = f"PWR-01-v2={'PASS' if any_pass else 'FAIL'}"
    if best_ic is not None:
        msg += f" | best {best.get('desk')} IC={best_ic:+.3f}"
    elif results:
        msg += f" | {results[0].get('n_hours_total', 0)}h aligned"
    else:
        msg += " | need hourly cache"

    return {
        "ok": len(results) > 0,
        "module": "backtest_pwr_v2",
        "message": msg,
        "outputs": [
            str(out_path.relative_to(base)).replace("\\", "/"),
            str(cand_path.relative_to(base)).replace("\\", "/"),
        ],
    }
