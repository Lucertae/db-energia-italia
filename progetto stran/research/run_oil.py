#!/usr/bin/env python3
"""Oil domain pre-analysis — BRT, CRU (if available), VIX."""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from clean import clean_series, resample_series
from explore import analyze_pairs
from features import log_return
from series_io import load_domain, load_series
from paths import ensure_output
from qa import qa_series

import pandas as pd


def build_oil_features(brt: pd.Series, vix: pd.Series, cru: pd.Series | None = None) -> pd.DataFrame:
    brt_m = resample_series(brt, "monthly")
    vix_m = resample_series(vix, "monthly")
    m = pd.DataFrame(index=brt_m.index)
    m["brt_logret_1m"] = log_return(brt_m, 1)
    m["vix_lag1m"] = vix_m.shift(1)
    if cru is not None:
        cru_m = resample_series(cru, "monthly")
        m["cru_change_1m"] = cru_m.diff()
    return m.dropna(how="all")


def main() -> int:
    out_dir = ensure_output()
    loaded = load_domain("oil")
    if "BRT" not in loaded:
        print("ERROR: BRT missing", file=sys.stderr)
        return 1

    qa_reports = []
    clean_map = {}
    meta_map = {}
    for sid, (raw, meta) in loaded.items():
        meta_map[sid] = meta
        cleaned = clean_series(raw, meta)
        clean_map[sid] = cleaned
        qa_reports.append(qa_series(cleaned, meta).to_dict())

    cru = None
    if "CRU" not in clean_map:
        try:
            cru_s, cru_m = load_series("CRU")
            cru = clean_series(cru_s, cru_m)
            qa_reports.append(qa_series(cru, cru_m).to_dict())
        except FileNotFoundError:
            pass
    else:
        cru = clean_map["CRU"]

    features = build_oil_features(clean_map["BRT"], clean_map.get("VIX", clean_map["BRT"]), cru=cru)

    pairs = [("brt_logret_1m", "vix_lag1m")]
    if cru is not None:
        pairs.append(("brt_logret_1m", "cru_change_1m"))

    corrs, lags = analyze_pairs(features, pairs)

    features_path = out_dir / "oil_features_monthly.csv"
    features.to_csv(features_path, float_format="%.6f")
    (out_dir / "oil_qa.json").write_text(json.dumps(qa_reports, indent=2), encoding="utf-8")
    (out_dir / "oil_correlations.json").write_text(json.dumps(corrs, indent=2), encoding="utf-8")

    lines = [
        "# Oil domain — pre-analysis report",
        "",
        f"Rows: {len(features.dropna(how='all'))}",
        "",
        "## Correlations",
        "",
    ]
    for c in corrs:
        lines.append(f"- **{c['period']}** {c['x']} vs {c['y']}: r={c['pearson_r']}, p={c['p_value']}, n={c['n']}")
    if not cru:
        lines.append("")
        lines.append("_CRU missing — run scripts/desk_harvest/eia_public_inventories.py_")

    (out_dir / "oil_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Oil report -> {out_dir / 'oil_report.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
