"""Load desk cache CSV into normalized pandas Series."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd

from paths import CACHE, CATALOG


def load_catalog() -> dict:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def _resolve_path(meta: dict) -> Path | None:
    for rel in meta.get("cache_paths", []):
        p = CACHE / Path(rel).name if "/" not in rel and "\\" not in rel else Path(rel)
        if not p.is_absolute():
            p = CACHE.parent / rel if rel.startswith("cache") else CACHE / rel
        # normalize: paths in catalog are like cache/HUB.csv
        if not p.is_file():
            p = CACHE / Path(rel).name
        if p.is_file():
            return p
    return None


def _pick_value_column(df: pd.DataFrame, hint: str | None) -> str:
    cols = [c for c in df.columns if c.lower() not in ("date", "observation_date")]
    if not cols:
        raise ValueError("no value column")
    if hint and hint in cols:
        return hint
    for c in cols:
        if hint and hint.lower() in c.lower():
            return c
    return cols[0]


def load_series(desk_id: str) -> tuple[pd.Series, dict]:
    """Return (values indexed by Timestamp, metadata dict with path + vintage)."""
    cat = load_catalog()
    meta = dict(cat["series"][desk_id])
    path = _resolve_path(meta)
    if path is None:
        raise FileNotFoundError(f"{desk_id}: no cache file in {meta.get('cache_paths')}")

    df = pd.read_csv(path)
    date_col = "observation_date" if "observation_date" in df.columns else "DATE"
    if date_col not in df.columns:
        raise ValueError(f"{desk_id}: missing date column in {path}")

    val_col = _pick_value_column(df, meta.get("value_col_hint"))
    dates = pd.to_datetime(df[date_col], errors="coerce")
    vals = pd.to_numeric(df[val_col], errors="coerce")
    # FRED uses '.' for missing
    vals = vals.replace(".", pd.NA)

    s = pd.Series(vals.values, index=dates, name=desk_id, dtype="float64")
    s = s[~s.index.isna()].sort_index()
    s = s[~s.index.duplicated(keep="last")]

    meta["loaded_from"] = str(path)
    meta["vintage_mtime"] = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec="seconds")
    meta["n_obs"] = int(s.notna().sum())
    return s, meta


def load_domain(domain: str) -> dict[str, tuple[pd.Series, dict]]:
    cat = load_catalog()
    ids = cat["domains"][domain]["series"]
    out: dict[str, tuple[pd.Series, dict]] = {}
    for sid in ids:
        try:
            out[sid] = load_series(sid)
        except FileNotFoundError:
            continue
    return out
