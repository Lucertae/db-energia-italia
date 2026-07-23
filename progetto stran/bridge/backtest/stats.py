"""Minimal statistics (stdlib) for signal backtests."""
from __future__ import annotations

import math
import random
from datetime import datetime
from typing import Callable, Sequence


def bonferroni_t_threshold(n_tests: int, alpha: float = 0.05) -> float:
    """Two-sided critical t for Bonferroni-corrected family (normal approx)."""
    if n_tests < 1:
        n_tests = 1
    # inverse normal for alpha/(2*n) — table for common n
    table = {1: 1.96, 2: 2.24, 3: 2.39, 4: 2.50, 5: 2.58, 6: 2.64, 8: 2.73, 10: 2.81}
    if n_tests in table:
        return table[n_tests]
    if n_tests <= 12:
        return 2.85
    return 3.0


def pearson_ic_stats(x: Sequence[float], y: Sequence[float]) -> dict[str, float | int]:
    """Pearson IC with t-stat from correlation (t ≈ r·√(n−2)/√(1−r²))."""
    ic, t_ic, n = pearson(x, y)
    return {
        "ic": round(ic, 4),
        "t_ic": round(t_ic, 3),
        "t_ols": round(t_ic, 3),
        "t_nw": round(t_ic, 3),
        "slope": round(ols_slope(x, y)[0], 6),
        "n": n,
        "inference": "pearson_t",
    }


def pearson_with_nw(
    x: Sequence[float],
    y: Sequence[float],
    *,
    nw_lags: int = 7,
) -> dict[str, float | int]:
    """Pearson IC + OLS slope t-stat with Newey-West HAC SE (lag default 7)."""
    n = min(len(x), len(y))
    if n < 10:
        return {"ic": 0.0, "t_ic": 0.0, "t_ols": 0.0, "t_nw": 0.0, "slope": 0.0, "n": n, "inference": "ols_nw_slope"}

    ic, t_ic, _ = pearson(x, y)
    slope, intercept, _ = ols_slope(x, y)

    residuals = [y[i] - (intercept + slope * x[i]) for i in range(n)]
    x_c = [x[i] - sum(x) / n for i in range(n)]

    # OLS t on slope
    sxx = sum(v * v for v in x_c)
    if sxx <= 1e-18:
        return {"ic": ic, "t_ic": round(t_ic, 3), "t_ols": 0.0, "t_nw": 0.0, "slope": slope, "n": n, "inference": "ols_nw_slope"}
    sigma2 = sum(r * r for r in residuals) / max(1, n - 2)
    se_ols = math.sqrt(sigma2 / sxx) if sigma2 > 0 else 1e-12
    t_ols = slope / se_ols if se_ols > 1e-12 else 0.0

    # Newey-West on sum of x_c[i]*e[i]
    L = min(nw_lags, n - 1)
    gamma0 = sum(x_c[i] * x_c[i] * residuals[i] * residuals[i] for i in range(n)) / n
    var_nw = gamma0
    for lag in range(1, L + 1):
        w = 1.0 - lag / (L + 1)
        g = sum(
            x_c[i] * x_c[i - lag] * residuals[i] * residuals[i - lag]
            for i in range(lag, n)
        ) / n
        var_nw += 2 * w * g
    se_nw = math.sqrt(max(var_nw, 1e-18) / sxx) if sxx > 0 else 1e-12
    t_nw = slope / se_nw if se_nw > 1e-12 else 0.0

    return {
        "ic": round(ic, 4),
        "t_ic": round(t_ic, 3),
        "t_ols": round(t_ols, 3),
        "t_nw": round(t_nw, 3),
        "slope": round(slope, 6),
        "n": n,
        "inference": "ols_nw_slope",
    }


def hit_rate_signed(
    signal: Sequence[float],
    forward_ret: Sequence[float],
    expected_sign: int,
) -> float:
    """Monotone directional hit on all non-zero signals.

    expected_sign=-1: high signal should coincide with negative return (s·r·es > 0).
    """
    n = min(len(signal), len(forward_ret))
    if n == 0 or expected_sign == 0:
        return 0.0
    es = -1.0 if expected_sign < 0 else 1.0
    active = [(signal[i], forward_ret[i]) for i in range(n) if signal[i] != 0]
    if not active:
        return 0.0
    hits = sum(1 for s, r in active if (s * r * es) > 0)
    return hits / len(active)


def economic_edge(
    signal: Sequence[float],
    forward_ret: Sequence[float],
    expected_sign: int,
    *,
    cost_eur_mwh: float,
) -> dict[str, float | int | bool]:
    """E[|return|·1{correct}] − cost on traded (non-zero signal) hours."""
    es = -1.0 if expected_sign < 0 else 1.0
    edges: list[float] = []
    n_correct = 0
    for s, r in zip(signal, forward_ret):
        if s == 0:
            continue
        correct = (s * r * es) > 0
        if correct:
            n_correct += 1
        edges.append((abs(r) if correct else 0.0) - cost_eur_mwh)
    if not edges:
        return {
            "mean_edge": 0.0,
            "n_trades": 0,
            "n_correct": 0,
            "hit_signed": 0.0,
            "cost_eur_mwh": cost_eur_mwh,
            "pass": False,
        }
    return {
        "mean_edge": round(sum(edges) / len(edges), 4),
        "n_trades": len(edges),
        "n_correct": n_correct,
        "hit_signed": round(n_correct / len(edges), 4),
        "cost_eur_mwh": cost_eur_mwh,
        "pass": (sum(edges) / len(edges)) > 0,
    }


def block_bootstrap_conditional_ic(
    xs: Sequence[float],
    ys: Sequence[float],
    winds: Sequence[float],
    *,
    mask_fn: Callable[[list[float], list[float]], list[bool]],
    block_hours: int = 24,
    n_boot: int = 400,
    seed: int = 42,
) -> dict[str, float | int | str]:
    """Block bootstrap IC on conditional subsample (non-contiguous selection).

    Resamples contiguous blocks from the full hourly series, reapplies the
    conditional filter inside each replicate, then bootstraps the Pearson IC.
    """
    n = min(len(xs), len(ys), len(winds))
    if n < block_hours * 3:
        return {
            "ic": 0.0, "t_ic": 0.0, "t_boot": 0.0, "se_boot": 0.0,
            "n": 0, "n_cond": 0, "n_boot_ok": 0, "inference": "block_bootstrap",
        }

    x_list = list(xs[:n])
    y_list = list(ys[:n])
    w_list = list(winds[:n])

    def _ic_on_indices(indices: list[int]) -> float | None:
        bx = [x_list[i] for i in indices]
        by = [y_list[i] for i in indices]
        bw = [w_list[i] for i in indices]
        mask = mask_fn(bx, bw)
        sx = [x for x, m in zip(bx, mask) if m]
        sy = [y for y, m in zip(by, mask) if m]
        if len(sx) < 15:
            return None
        ic, _, _ = pearson(sx, sy)
        return ic

    point_mask = mask_fn(x_list, w_list)
    px = [x for x, m in zip(x_list, point_mask) if m]
    py = [y for y, m in zip(y_list, point_mask) if m]
    ic_point, t_ic, n_cond = pearson(px, py)

    n_blocks = max(1, (n + block_hours - 1) // block_hours)
    blocks = [
        list(range(i * block_hours, min((i + 1) * block_hours, n)))
        for i in range(n_blocks)
    ]
    rng = random.Random(seed)
    boot_ics: list[float] = []
    for _ in range(n_boot):
        chosen = [rng.choice(blocks) for _ in range(n_blocks)]
        indices = [i for block in chosen for i in block]
        ic_b = _ic_on_indices(indices)
        if ic_b is not None:
            boot_ics.append(ic_b)

    if len(boot_ics) < 30:
        return {
            "ic": round(ic_point, 4),
            "t_ic": round(t_ic, 3),
            "t_boot": 0.0,
            "se_boot": 0.0,
            "n": n,
            "n_cond": n_cond,
            "n_boot_ok": len(boot_ics),
            "block_hours": block_hours,
            "inference": "block_bootstrap_insufficient",
        }

    mean_b = sum(boot_ics) / len(boot_ics)
    var_b = sum((b - mean_b) ** 2 for b in boot_ics) / max(1, len(boot_ics) - 1)
    se_b = math.sqrt(max(var_b, 1e-18))
    t_boot = (ic_point - mean_b) / se_b if se_b > 1e-12 else 0.0
    if abs(mean_b) < 1e-9:
        t_boot = ic_point / se_b if se_b > 1e-12 else 0.0

    return {
        "ic": round(ic_point, 4),
        "t_ic": round(t_ic, 3),
        "t_boot": round(t_boot, 3),
        "se_boot": round(se_b, 4),
        "boot_mean_ic": round(mean_b, 4),
        "n": n,
        "n_cond": n_cond,
        "n_boot_ok": len(boot_ics),
        "block_hours": block_hours,
        "inference": "block_bootstrap",
    }


def ic_by_season(
    x: Sequence[float],
    y: Sequence[float],
    dates: Sequence[str],
) -> dict[str, float | int]:
    """Pearson IC within meteorological seasons (DJF/MAM/JJA/SON)."""
    buckets: dict[str, list[tuple[float, float]]] = {
        "DJF": [], "MAM": [], "JJA": [], "SON": [],
    }
    n = min(len(x), len(y), len(dates))
    for i in range(n):
        try:
            dt = datetime.fromisoformat(str(dates[i])[:10])
        except ValueError:
            continue
        m = dt.month
        if m in (12, 1, 2):
            key = "DJF"
        elif m in (3, 4, 5):
            key = "MAM"
        elif m in (6, 7, 8):
            key = "JJA"
        else:
            key = "SON"
        buckets[key].append((x[i], y[i]))

    out: dict[str, float | int] = {}
    for key, pairs in buckets.items():
        if len(pairs) < 30:
            out[key] = {"n": len(pairs), "ic": None}
            continue
        xs, ys = zip(*pairs)
        ic, _, nn = pearson(list(xs), list(ys))
        out[key] = {"n": nn, "ic": round(ic, 4)}
    return out


def pearson(x: Sequence[float], y: Sequence[float]) -> tuple[float, float, int]:
    """Return (r, t_stat, n). t_stat is approximate two-sided."""
    n = min(len(x), len(y))
    if n < 5:
        return 0.0, 0.0, n
    mx = sum(x[:n]) / n
    my = sum(y[:n]) / n
    num = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    den_x = math.sqrt(sum((x[i] - mx) ** 2 for i in range(n)))
    den_y = math.sqrt(sum((y[i] - my) ** 2 for i in range(n)))
    if den_x == 0 or den_y == 0:
        return 0.0, 0.0, n
    r = num / (den_x * den_y)
    if abs(r) >= 1.0:
        return r, 0.0, n
    t = r * math.sqrt((n - 2) / max(1e-12, 1.0 - r * r))
    return r, t, n


def spearman(x: Sequence[float], y: Sequence[float]) -> float:
    n = min(len(x), len(y))
    if n < 5:
        return 0.0

    def ranks(vals: Sequence[float]) -> list[float]:
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        out = [0.0] * len(vals)
        i = 0
        while i < len(order):
            j = i
            while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1.0
            for k in range(i, j + 1):
                out[order[k]] = avg
            i = j + 1
        return out

    rx, ry = ranks(list(x[:n])), ranks(list(y[:n]))
    r, _, _ = pearson(rx, ry)
    return r


def ols_slope(x: Sequence[float], y: Sequence[float]) -> tuple[float, float, int]:
    """Simple OLS y ~ a + b*x. Returns (slope, intercept, n)."""
    n = min(len(x), len(y))
    if n < 5:
        return 0.0, 0.0, n
    mx = sum(x[:n]) / n
    my = sum(y[:n]) / n
    var_x = sum((x[i] - mx) ** 2 for i in range(n))
    if var_x == 0:
        return 0.0, my, n
    cov = sum((x[i] - mx) * (y[i] - my) for i in range(n))
    b = cov / var_x
    a = my - b * mx
    return b, a, n


def hit_rate(signal: Sequence[float], forward_ret: Sequence[float]) -> float:
    """Directional hit rate for signed signal vs return sign."""
    n = min(len(signal), len(forward_ret))
    if n == 0:
        return 0.0
    hits = sum(
        1 for i in range(n)
        if signal[i] != 0 and (signal[i] > 0) == (forward_ret[i] > 0)
    )
    active = sum(1 for i in range(n) if signal[i] != 0)
    return hits / active if active else 0.0


def hit_rate_expected(
    signal: Sequence[float],
    forward_ret: Sequence[float],
    expected_sign: int,
) -> float:
    """Hit rate on high-signal days (top quartile): did return move as hypothesized?

    For expected_sign=+1: high signal → positive return.
    For expected_sign=-1: high signal → negative return.
    Avoids the level-only trap (e.g. wind always > 0).
    """
    return hit_rate_high_signal(signal, forward_ret, expected_sign, quantile=0.75)


def hit_rate_high_signal(
    signal: Sequence[float],
    forward_ret: Sequence[float],
    expected_sign: int,
    *,
    quantile: float = 0.75,
) -> float:
    n = min(len(signal), len(forward_ret))
    if n < 20 or expected_sign == 0:
        return 0.0
    xs = sorted(signal[:n])
    hi = xs[min(int(n * quantile), n - 1)]
    es = 1 if expected_sign > 0 else -1
    high_rets = [forward_ret[i] for i in range(n) if signal[i] >= hi]
    if not high_rets:
        return 0.0
    hits = sum(1 for r in high_rets if (r * es) > 0)
    return hits / len(high_rets)


def event_sign_ok(spread: float, expected_sign: int) -> bool:
    """High-quartile minus low-quartile return spread matches hypothesis direction."""
    if expected_sign == 0:
        return False
    return (spread * expected_sign) > 0


def event_mean(
    signal: Sequence[float],
    forward_ret: Sequence[float],
    *,
    upper_q: float = 0.75,
    lower_q: float = 0.25,
) -> dict[str, float | int]:
    n = min(len(signal), len(forward_ret))
    if n < 20:
        return {"n_high": 0, "n_low": 0, "mean_high": 0.0, "mean_low": 0.0, "spread": 0.0}
    xs = sorted(signal[:n])
    hi = xs[int(n * upper_q)]
    lo = xs[int(n * lower_q)]
    high = [forward_ret[i] for i in range(n) if signal[i] >= hi]
    low = [forward_ret[i] for i in range(n) if signal[i] <= lo]
    mean_hi = sum(high) / len(high) if high else 0.0
    mean_lo = sum(low) / len(low) if low else 0.0
    return {
        "n_high": len(high),
        "n_low": len(low),
        "mean_high": round(mean_hi, 5),
        "mean_low": round(mean_lo, 5),
        "spread": round(mean_hi - mean_lo, 5),
    }


def summarize(x: Sequence[float]) -> dict[str, float]:
    n = len(x)
    if n == 0:
        return {"n": 0, "mean": 0.0, "std": 0.0}
    m = sum(x) / n
    var = sum((v - m) ** 2 for v in x) / max(1, n - 1)
    return {"n": n, "mean": round(m, 5), "std": round(math.sqrt(var), 5)}
