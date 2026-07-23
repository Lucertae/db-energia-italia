"""Cross-source QA: gaps, staleness, duplicates on desk cache CSVs."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from bridge.spine_io import ROOT, load_json, read_fred_csv


def _parse_date(s: str) -> datetime | None:
    s = s.strip()[:10]
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _analyze_csv(path: Path, max_age_h: int) -> dict[str, Any]:
    rows = read_fred_csv(path)
    if not rows:
        return {"path": str(path.name), "status": "empty", "n": 0}

    dates: list[datetime] = []
    vals: list[float] = []
    for d, v in rows:
        dt = _parse_date(d)
        if dt:
            dates.append(dt)
            vals.append(v)

    if not dates:
        return {"path": str(path.name), "status": "unparseable", "n": len(rows)}

    dates_sorted = sorted(dates)
    gaps = 0
    max_gap_days = 0
    for i in range(1, len(dates_sorted)):
        delta = (dates_sorted[i] - dates_sorted[i - 1]).days
        if delta > 5:
            gaps += 1
            if delta > max_gap_days:
                max_gap_days = delta

    dupes = len(rows) - len(set(d.strftime("%Y-%m-%d") for d in dates))
    last_dt = dates_sorted[-1].replace(tzinfo=timezone.utc)
    age_h = int((datetime.now(timezone.utc) - last_dt).total_seconds() / 3600)
    stale_threshold = max_age_h
    if last_dt.weekday() == 4:
        stale_threshold += 48
    elif max_gap_days <= 35 and len(dates) >= 12:
        stale_threshold = max(stale_threshold, 960)
    stale = age_h > stale_threshold

    zeros = sum(1 for v in vals if v == 0.0)
    negatives = sum(1 for v in vals if v < 0.0)

    status = "ok"
    if stale:
        status = "stale"
    if gaps > 3 and max_gap_days > 35:
        status = "gappy"
    if dupes > 0:
        status = "dupes"

    return {
        "path": path.name,
        "status": status,
        "n": len(dates),
        "from": dates_sorted[0].strftime("%Y-%m-%d"),
        "to": dates_sorted[-1].strftime("%Y-%m-%d"),
        "age_h": age_h,
        "gaps_gt5d": gaps,
        "max_gap_days": max_gap_days,
        "dupes": dupes,
        "zeros": zeros,
        "negatives": negatives,
    }


def run(root: Path | None = None) -> dict[str, Any]:
    base = root or ROOT
    spine_path = base / "config" / "desk_spine.json"
    spine = load_json(spine_path) if spine_path.is_file() else {"series": []}

    reports: list[dict[str, Any]] = []
    issues = 0

    for entry in spine.get("series", []):
        sid = entry.get("id", "?")
        max_h = int(entry.get("max_age_h", 48))
        found = False
        for rel in entry.get("paths", [f"cache/{sid}.csv"]):
            p = base / str(rel).replace("/", "\\")
            if p.is_file():
                found = True
                rep = _analyze_csv(p, max_h)
                rep["id"] = sid
                rep["tier"] = entry.get("tier", "standard")
                if rep["status"] != "ok":
                    issues += 1
                reports.append(rep)
                break
        if not found:
            reports.append({"id": sid, "status": "missing", "tier": entry.get("tier")})
            issues += 1

    critical_bad = [
        r for r in reports
        if r.get("tier") == "critical" and r.get("status") not in ("ok", None)
    ]

    payload = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "series_checked": len(reports),
        "issues": issues,
        "critical_issues": len(critical_bad),
        "reports": reports,
        "note": "Gap >5d flags weekly/monthly series; validate cross-source before correlating.",
    }

    out_path = base / "cache" / "spine" / "modules" / "qa_series.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    return {
        "ok": len(critical_bad) == 0,
        "module": "qa_series",
        "message": f"{len(reports)} series {issues} issues ({len(critical_bad)} critical)",
        "outputs": [str(out_path.relative_to(base)).replace("\\", "/")],
    }
