"""Pre-analysis: correlations, lead-lag, sub-period stability."""
from __future__ import annotations

from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class CorrResult:
    x: str
    y: str
    pearson_r: float
    p_value: float
    n: int
    period: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["pearson_r"] = round(self.pearson_r, 4)
        d["p_value"] = round(self.p_value, 6)
        return d


@dataclass
class LeadLagResult:
    x: str
    y: str
    best_lag: int
    ccf_at_best: float
    period: str

    def to_dict(self) -> dict:
        d = asdict(self)
        d["ccf_at_best"] = round(self.ccf_at_best, 4)
        return d


def pearson_pair(x: pd.Series, y: pd.Series, period: str = "full") -> CorrResult | None:
    df = pd.concat([x, y], axis=1).dropna()
    if len(df) < 12:
        return None
    a, b = df.iloc[:, 0], df.iloc[:, 1]
    if a.std(ddof=1) == 0 or b.std(ddof=1) == 0:
        return None
    r, p = stats.pearsonr(a, b)
    return CorrResult(
        x=x.name or "x",
        y=y.name or "y",
        pearson_r=float(r),
        p_value=float(p),
        n=len(df),
        period=period,
    )


def cross_corr_best_lag(
    x: pd.Series,
    y: pd.Series,
    max_lag: int = 6,
    period: str = "full",
) -> LeadLagResult | None:
    """
    Positive lag: x leads y (x shifted forward vs y).
    Uses Pearson at each lag on aligned overlapping sample.
    """
    df = pd.concat([x, y], axis=1).dropna()
    if len(df) < 12:
        return None
    xs, ys = df.iloc[:, 0], df.iloc[:, 1]
    best_lag = 0
    best_r: float | None = None
    for lag in range(-max_lag, max_lag + 1):
        if lag > 0:
            a, b = xs.shift(lag), ys
        elif lag < 0:
            a, b = xs, ys.shift(-lag)
        else:
            a, b = xs, ys
        pair = pd.concat([a, b], axis=1).dropna()
        if len(pair) < 10:
            continue
        pa, pb = pair.iloc[:, 0], pair.iloc[:, 1]
        if pa.std(ddof=1) == 0 or pb.std(ddof=1) == 0:
            continue
        r, _ = stats.pearsonr(pa, pb)
        if best_r is None or abs(r) > abs(best_r):
            best_r = float(r)
            best_lag = lag
    if best_r is None:
        return None
    return LeadLagResult(
        x=x.name or "x",
        y=y.name or "y",
        best_lag=best_lag,
        ccf_at_best=best_r,
        period=period,
    )


def rolling_correlation(x: pd.Series, y: pd.Series, window: int = 24) -> pd.Series:
    return x.rolling(window).corr(y)


def sub_periods(index: pd.DatetimeIndex) -> dict[str, slice]:
    """Regime splits informed by JAE 2024 gas crisis literature."""
    return {
        "pre_covid": slice(None, "2020-03-01"),
        "covid_2020_21": slice("2020-03-01", "2022-01-01"),
        "crisis_2022_plus": slice("2022-01-01", None),
    }


def analyze_pairs(
    features: pd.DataFrame,
    pairs: list[tuple[str, str]],
) -> tuple[list[dict], list[dict]]:
    corrs: list[dict] = []
    lags: list[dict] = []

    for period_name, sl in sub_periods(features.index).items():
        sub = features.loc[sl]
        for a, b in pairs:
            if a not in sub.columns or b not in sub.columns:
                continue
            c = pearson_pair(sub[a], sub[b], period=period_name)
            if c:
                corrs.append(c.to_dict())
            ll = cross_corr_best_lag(sub[a], sub[b], max_lag=3, period=period_name)
            if ll:
                lags.append(ll.to_dict())

    # full sample
    for a, b in pairs:
        if a not in features.columns or b not in features.columns:
            continue
        c = pearson_pair(features[a], features[b], period="full")
        if c:
            corrs.append(c.to_dict())
        ll = cross_corr_best_lag(features[a], features[b], max_lag=3, period="full")
        if ll:
            lags.append(ll.to_dict())

    return corrs, lags
