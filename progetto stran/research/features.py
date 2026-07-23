"""Feature engineering for energy signal research."""
from __future__ import annotations

import numpy as np
import pandas as pd


def log_return(s: pd.Series, periods: int = 1) -> pd.Series:
    return np.log(s / s.shift(periods))


def pct_change(s: pd.Series, periods: int = 1) -> pd.Series:
    return s.pct_change(periods)


def rolling_zscore(s: pd.Series, window: int = 252, min_periods: int = 60) -> pd.Series:
    mu = s.rolling(window, min_periods=min_periods).mean()
    sd = s.rolling(window, min_periods=min_periods).std()
    return (s - mu) / sd


def rolling_volatility(returns: pd.Series, window: int = 21) -> pd.Series:
    return returns.rolling(window, min_periods=max(5, window // 4)).std() * np.sqrt(252)


def spread(a: pd.Series, b: pd.Series) -> pd.Series:
    return a - b


def inventory_seasonal_deviation(
    inventory: pd.Series,
    window_years: int = 5,
) -> pd.DataFrame:
    """
    Weekly storage vs trailing same-week-of-year mean.
    Theory-of-storage: deviation from seasonal norm drives convenience yield.
    """
    df = pd.DataFrame({"level": inventory}).dropna()
    df["week"] = df.index.isocalendar().week.astype(int)
    df["year"] = df.index.year

    rows = []
    for dt, row in df.iterrows():
        wk = row["week"]
        yr = row["year"]
        hist = df[(df["week"] == wk) & (df["year"] < yr) & (df["year"] >= yr - window_years)]
        if len(hist) < 2:
            rows.append({"deviation_pct": np.nan, "z_vs_season": np.nan})
            continue
        mu = hist["level"].mean()
        sd = hist["level"].std(ddof=1)
        dev_pct = 100.0 * (row["level"] - mu) / mu if mu else np.nan
        z = (row["level"] - mu) / sd if sd and sd > 0 else np.nan
        rows.append({"deviation_pct": dev_pct, "z_vs_season": z})

    feat = pd.DataFrame(rows, index=df.index)
    feat["inventory_change"] = df["level"].diff()
    feat["inventory_change_pct"] = df["level"].pct_change()
    return feat


def build_gas_features(
    hub: pd.Series,
    ttf: pd.Series,
    vix: pd.Series | None = None,
    ngs: pd.Series | None = None,
    hub_meta: dict | None = None,
    ttf_meta: dict | None = None,
) -> pd.DataFrame:
    """Build gas-domain feature matrix at monthly frequency for cross-series work."""
    from clean import align_to_frequency, resample_series

    meta_map = {
        "HUB": hub_meta or {"freq": "daily"},
        "TTF": ttf_meta or {"freq": "monthly"},
    }
    series_map = {"HUB": hub, "TTF": ttf}
    if vix is not None:
        series_map["VIX"] = vix
        meta_map["VIX"] = {"freq": "daily"}

    monthly = align_to_frequency(series_map, meta_map, target_freq="monthly")

    out = pd.DataFrame(index=monthly.index)
    out["hub_level"] = monthly["HUB"]
    out["ttf_level"] = monthly["TTF"]
    out["ttf_hub_spread"] = monthly["TTF"] - monthly["HUB"]
    out["hub_logret_1m"] = log_return(monthly["HUB"], 1)
    out["ttf_logret_1m"] = log_return(monthly["TTF"], 1)
    out["spread_z_36m"] = rolling_zscore(out["ttf_hub_spread"], window=36, min_periods=12)

    if vix is not None:
        vix_m = resample_series(vix, "monthly")
        out["vix_level"] = vix_m
        out["vix_lag1m"] = out["vix_level"].shift(1)

    if ngs is not None:
        inv = inventory_seasonal_deviation(ngs)
        inv_m = inv.resample("ME").last()
        out["ngs_deviation_pct"] = inv_m["deviation_pct"].reindex(out.index)
        out["ngs_change_pct"] = inv_m["inventory_change_pct"].reindex(out.index)

    return out.dropna(how="all")
