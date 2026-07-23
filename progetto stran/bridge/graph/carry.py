"""Carry / CIP deviation and momentum factors from desk daily series."""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.spine_io import (
    ROOT,
    desk_csv_path,
    fred_last,
    load_fx_manifest,
    read_fred_csv,
)


def _momentum_63d(path: Path) -> float | None:
    rows = read_fred_csv(path)
    if len(rows) < 64:
        return None
    last = rows[-1][1]
    prev = rows[-64][1]
    if prev <= 0:
        return None
    return (last / prev - 1.0) * 100.0


def _cip_forward(spot: float, r_dom: float, r_for: float, years: float) -> float:
    return spot * math.exp((r_dom - r_for) * years)


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    manifest = load_fx_manifest(base)
    legs = manifest.get("rate_legs", {})
    sof_id = legs.get("usd", {}).get("desk_id", "SOF")
    edf_id = legs.get("eur", {}).get("desk_id", "EDF")

    sof = fred_last(desk_csv_path(base, sof_id))
    edf = fred_last(desk_csv_path(base, edf_id))

    signals: list[dict[str, Any]] = []
    for pair in manifest.get("pairs", []):
        pid = pair.get("id", "?")
        desk_id = pair.get("desk_id")
        if not desk_id:
            continue
        csv_path = desk_csv_path(base, str(desk_id))
        spot = fred_last(csv_path)
        mom = _momentum_63d(csv_path)

        row: dict[str, Any] = {
            "pair": pid,
            "desk_id": desk_id,
            "spot_eur_base": round(spot, 6) if spot else None,
            "mom_63d_pct": round(mom, 2) if mom is not None else None,
        }

        if spot and sof is not None and edf is not None and str(pair.get("quote")) == "USD":
            r_us = sof / 100.0
            r_eu = edf / 100.0
            fwd_3m = _cip_forward(spot, r_us, r_eu, 0.25)
            row["cip_fwd_3m"] = round(fwd_3m, 6)
            row["carry_spread_ann_pct"] = round((r_us - r_eu) * 100.0, 3)
            row["carry_signal"] = "long_usd" if r_us > r_eu else "long_eur"

        signals.append(row)

    # Rank by absolute momentum for dashboard
    ranked = sorted(
        [s for s in signals if s.get("mom_63d_pct") is not None],
        key=lambda s: abs(float(s["mom_63d_pct"])),
        reverse=True,
    )

    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rate_legs": {"SOFR": sof, "ECB_DFR": edf},
        "signals": signals,
        "top_momentum": ranked[:5],
        "note": "Daily FRED/ECB — carry from rate diff; not live forward points.",
    }

    out_path = base / "cache" / "spine" / "modules" / "fx_carry.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "ok": True,
        "module": "fx_carry",
        "message": f"{len(signals)} pairs SOFR={sof} DFR={edf}",
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
