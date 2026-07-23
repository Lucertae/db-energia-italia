"""Wind speed → capacity factor → MW (turbine + fleet-smoothed curves)."""
from __future__ import annotations

import math


def capacity_factor(
    wind_ms: float,
    *,
    cut_in_ms: float = 3.0,
    rated_ms: float = 12.0,
    cut_out_ms: float = 25.0,
) -> float:
    """Single-turbine CF: cubic ramp cut-in→rated."""
    if wind_ms < cut_in_ms or wind_ms >= cut_out_ms:
        return 0.0
    if wind_ms >= rated_ms:
        return 1.0
    span = rated_ms - cut_in_ms
    if span <= 0:
        return 0.0
    x = (wind_ms - cut_in_ms) / span
    return x * x * x


def fleet_capacity_factor(
    wind_ms: float,
    *,
    cut_in_ms: float = 3.0,
    rated_ms: float = 12.0,
    cut_out_ms: float = 25.0,
    smooth_sigma_ms: float = 2.0,
    n_steps: int = 15,
) -> float:
    """Fleet aggregate CF: cubic turbine curve convolved with Gaussian σ≈2 m/s.

    Smooths the transition region where the signal lives (4–11 m/s).
    """
    if smooth_sigma_ms <= 0:
        return capacity_factor(
            wind_ms, cut_in_ms=cut_in_ms, rated_ms=rated_ms, cut_out_ms=cut_out_ms
        )
    lo = wind_ms - 3.0 * smooth_sigma_ms
    hi = wind_ms + 3.0 * smooth_sigma_ms
    if n_steps < 3:
        n_steps = 3
    total_w = 0.0
    total_cf = 0.0
    for i in range(n_steps):
        v = lo + (hi - lo) * i / (n_steps - 1)
        w = math.exp(-0.5 * ((v - wind_ms) / smooth_sigma_ms) ** 2)
        cf = capacity_factor(v, cut_in_ms=cut_in_ms, rated_ms=rated_ms, cut_out_ms=cut_out_ms)
        total_w += w
        total_cf += w * cf
    return total_cf / total_w if total_w > 0 else 0.0


def wind_to_mw(
    wind_ms: float,
    capacity_mw: float,
    *,
    cut_in_ms: float = 3.0,
    rated_ms: float = 12.0,
    cut_out_ms: float = 25.0,
    fleet: bool = True,
    smooth_sigma_ms: float = 2.0,
) -> float:
    cf_fn = fleet_capacity_factor if fleet else capacity_factor
    cf = cf_fn(
        wind_ms,
        cut_in_ms=cut_in_ms,
        rated_ms=rated_ms,
        cut_out_ms=cut_out_ms,
        smooth_sigma_ms=smooth_sigma_ms if fleet else 0.0,
    )
    return cf * capacity_mw


def in_steep_curve_zone(wind_ms: float, *, lo_ms: float = 4.0, hi_ms: float = 11.0) -> bool:
    """Hours where fleet CF is in rising (non-saturated) region."""
    return lo_ms <= wind_ms <= hi_ms


def delta_norm(om_mw: float, published_mw: float, capacity_mw: float) -> float:
    if capacity_mw <= 0:
        return 0.0
    return (om_mw - published_mw) / capacity_mw
