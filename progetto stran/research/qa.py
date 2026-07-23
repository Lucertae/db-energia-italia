"""Data quality checks for desk series."""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd


@dataclass
class QAReport:
    desk_id: str
    freq: str
    n_total: int
    n_valid: int
    coverage_pct: float
    start: str | None
    end: str | None
    n_gaps: int
    max_gap_days: int
    n_outliers_mad: int
    vintage_mtime: str | None
    loaded_from: str | None
    warnings: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def _expected_calendar_days(freq: str, index: pd.DatetimeIndex) -> int:
    if len(index) == 0:
        return 0
    span = (index.max() - index.min()).days + 1
    if freq == "daily":
        return max(span, 1)
    if freq == "weekly":
        return max(span // 7 + 1, 1)
    if freq == "monthly":
        return max(len(pd.period_range(index.min(), index.max(), freq="M")), 1)
    return len(index)


def mad_outlier_mask(s: pd.Series, threshold: float = 6.0) -> pd.Series:
    x = s.dropna()
    if len(x) < 10:
        return pd.Series(False, index=s.index)
    med = x.median()
    mad = (x - med).abs().median()
    if mad == 0 or np.isnan(mad):
        return pd.Series(False, index=s.index)
    modified_z = 0.6745 * (s - med) / mad
    return modified_z.abs() > threshold


def qa_series(s: pd.Series, meta: dict) -> QAReport:
    freq = meta.get("freq", "daily")
    valid = s.dropna()
    warnings: list[str] = []

    if len(valid) == 0:
        warnings.append("empty series")
        return QAReport(
            desk_id=s.name or meta.get("desk_id", "?"),
            freq=freq,
            n_total=len(s),
            n_valid=0,
            coverage_pct=0.0,
            start=None,
            end=None,
            n_gaps=0,
            max_gap_days=0,
            n_outliers_mad=0,
            vintage_mtime=meta.get("vintage_mtime"),
            loaded_from=meta.get("loaded_from"),
            warnings=warnings,
        )

    if freq == "daily":
        full_idx = pd.date_range(valid.index.min(), valid.index.max(), freq="B")
        reindexed = s.reindex(full_idx)
        gaps = int(reindexed.isna().sum())
        gap_sizes = []
        na = reindexed.isna()
        if na.any():
            groups = (na != na.shift()).cumsum()
            for _, block in reindexed.groupby(groups):
                if block.isna().all():
                    gap_sizes.append(len(block))
        max_gap = max(gap_sizes) if gap_sizes else 0
        expected = len(full_idx)
    else:
        gaps = int(s.isna().sum())
        max_gap = 0
        expected = _expected_calendar_days(freq, valid.index)

    outliers = mad_outlier_mask(valid)
    n_out = int(outliers.sum())

    coverage = 100.0 * len(valid) / max(expected, 1)
    if coverage < 90:
        warnings.append(f"low coverage {coverage:.1f}%")
    if max_gap > 5 and freq == "daily":
        warnings.append(f"max business-day gap {max_gap}")
    if n_out > 0:
        warnings.append(f"{n_out} MAD outliers (|z|>6)")

    if meta.get("desk_id") == "TTF":
        warnings.append("monthly FRED proxy — not ICE TTF futures")

    return QAReport(
        desk_id=s.name or meta.get("desk_id", "?"),
        freq=freq,
        n_total=len(s),
        n_valid=len(valid),
        coverage_pct=round(coverage, 2),
        start=str(valid.index.min().date()),
        end=str(valid.index.max().date()),
        n_gaps=gaps,
        max_gap_days=max_gap,
        n_outliers_mad=n_out,
        vintage_mtime=meta.get("vintage_mtime"),
        loaded_from=meta.get("loaded_from"),
        warnings=warnings,
    )
