"""Cleaning rules derived from academic preprocessing practice."""
from __future__ import annotations

import pandas as pd

from qa import mad_outlier_mask


def clean_series(s: pd.Series, meta: dict, *, winsorize_mad: float | None = 6.0) -> pd.Series:
    """
    Standard clean pipeline:
    - coerce numeric (done at load)
    - drop duplicate index
    - optional MAD winsorization (not deletion — preserves timing)
    """
    out = s.sort_index().astype("float64")
    out = out[~out.index.duplicated(keep="last")]

    if winsorize_mad is not None and out.notna().sum() >= 10:
        mask = mad_outlier_mask(out, winsorize_mad)
        if mask.any():
            med = out.median()
            out = out.where(~mask, med)

    return out


def to_business_daily(s: pd.Series, method: str = "ffill", limit: int = 5) -> pd.Series:
    if s.empty:
        return s
    idx = pd.date_range(s.index.min(), s.index.max(), freq="B")
    return s.reindex(idx).ffill(limit=limit) if method == "ffill" else s.reindex(idx)


def resample_series(s: pd.Series, freq: str, agg: str = "last") -> pd.Series:
    """Resample to target frequency for cross-series analysis."""
    if freq == "daily":
        return to_business_daily(s)
    rule = {"weekly": "W-FRI", "monthly": "ME"}.get(freq, freq)
    if agg == "mean":
        return s.resample(rule).mean()
    return s.resample(rule).last()


def align_to_frequency(
    series_map: dict[str, pd.Series],
    meta_map: dict[str, dict],
    target_freq: str = "monthly",
) -> pd.DataFrame:
    """Align heterogeneous series to common frequency (literature: no mixed-freq correlation)."""
    cols = {}
    for sid, s in series_map.items():
        # Always resample — monthly FRED may use month-start while resample uses month-end
        cols[sid] = resample_series(s, target_freq)
    df = pd.DataFrame(cols)
    return df.sort_index()
