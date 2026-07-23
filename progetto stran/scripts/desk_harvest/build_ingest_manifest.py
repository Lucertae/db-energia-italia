#!/usr/bin/env python3
"""Build unified ingest manifest for ING page — World Monitor parity (+ desk series).

RSS catalog from import_wm_feeds.py (WM feeds + variants + digest + telegram).
Google News topic feeds kept — same surface as World Monitor.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("DESK_ROOT", HERE.parents[1]))
CACHE = Path(os.environ.get("DESK_CACHE", ROOT / "cache"))
OUT = CACHE / "ingest" / "manifest.json"

from api_keys import apply_keys, has_key  # noqa: E402

apply_keys(CACHE)

# Paths under research / hypothesis docs are never concrete ingest sources
SPECULATIVE_PATH_MARKERS = (
    "docs/research/",
    "docs\\research\\",
    "research/output/",
    "research\\output\\",
    "SEGNALI_DA_STUDIARE",
    "CHOKEPOINTS_ROUTES",
    "chokepoints_catalog",
)

# wm-*/go-*/stran-* feed category → desk sector (same logic as build_intel_index.py)
CAT_MAP: list[tuple[str, str]] = [
    ("stran-maritime", "MARITIME"),
    ("stran-energy", "ENERGY"),
    ("stran-finance", "FINANCE"),
    ("stran-regulatory", "FINANCE"),
    ("stran-macro", "FINANCE"),
    ("stran-humanitarian", "DEFENSE"),
    ("stran-eu", "GEO"),
    ("stran-asia", "GEO"),
    ("stran-africa", "GEO"),
    ("stran-defense", "DEFENSE"),
    ("stran-wire", "GEO"),
    ("wm-energy", "ENERGY"),
    ("wm-commodities", "ENERGY"),
    ("wm-commodity", "ENERGY"),
    ("go-energy", "ENERGY"),
    ("go-commodities", "MARITIME"),
    ("wm-middleeast", "GEO"),
    ("wm-europe", "GEO"),
    ("wm-asia", "GEO"),
    ("wm-africa", "GEO"),
    ("wm-latam", "GEO"),
    ("wm-gccNews", "GEO"),
    ("wm-us", "GEO"),
    ("wm-politics", "GEO"),
    ("wm-gov", "DEFENSE"),
    ("wm-thinktanks", "DEFENSE"),
    ("wm-crisis", "DEFENSE"),
    ("wm-security", "DEFENSE"),
    ("go-defense", "DEFENSE"),
    ("go-government", "DEFENSE"),
    ("go-think-tanks", "DEFENSE"),
    ("go-humanitarian", "DEFENSE"),
    ("wm-finance", "FINANCE"),
    ("wm-markets", "FINANCE"),
    ("wm-bonds", "FINANCE"),
    ("wm-centralbanks", "FINANCE"),
    ("wm-forex", "FINANCE"),
    ("wm-crypto", "FINANCE"),
    ("wm-fintech", "FINANCE"),
    ("wm-economic", "FINANCE"),
    ("go-finance", "FINANCE"),
    ("wm-tech", "TECH"),
    ("wm-ai", "TECH"),
    ("wm-dev", "TECH"),
    ("wm-startups", "TECH"),
    ("go-tech", "TECH"),
    ("wm-climate", "CLIMATE"),
    ("wm-nature", "CLIMATE"),
    ("go-climate", "CLIMATE"),
    ("wm-science", "CLIMATE"),
]

SECTION_ORDER = {"PIPE": 0, "API": 1, "REF": 2, "RSS": 3, "SER": 4}

# Default poll cadence when a source has no explicit refresh_sec (no more null/on-demand).
DEFAULT_REFRESH_SEC = {
    "PIPE": 60,      # live pipelines
    "API": 300,      # adapter / API poll
    "RSS": 900,      # news feeds 15m
    "SER": 1800,     # series / desk metrics 30m
    "REF": 3600,     # reference matrix 1h
}
DEFAULT_REFRESH_FALLBACK = 600


def default_refresh_sec(section: str, explicit: object) -> int:
    if explicit is not None:
        try:
            v = int(explicit)  # type: ignore[arg-type]
            if v > 0:
                return v
        except (TypeError, ValueError):
            pass
    return DEFAULT_REFRESH_SEC.get((section or "").upper(), DEFAULT_REFRESH_FALLBACK)


def load_json(path: Path) -> dict | list | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def desk_for_category(raw: str) -> str:
    """World Monitor parity: sector = WM panel name (POLITICS, EUROPE, …)."""
    raw = (raw or "").lower().strip()
    if not raw:
        return "GEO"
    if raw.startswith("wm-digest-"):
        panel = raw[len("wm-digest-") :]
        return panel.replace("-", "")[:15].upper() or "DIGEST"
    if raw.startswith("wm-telegram"):
        return "TELEGRAM"
    if raw.startswith("wm-"):
        rest = raw[3:]
        for v in (
            "finance-",
            "tech-",
            "commodity-",
            "energy-",
            "happy-",
            "full-",
            "base-",
        ):
            if rest.startswith(v):
                rest = rest[len(v) :]
                break
        panel = rest.replace("-", "")[:15].upper()
        return panel or "WM"
    if raw.startswith("stran-"):
        for prefix, desk in CAT_MAP:
            if raw.startswith(prefix):
                return desk
        return "GEO"
    if raw.startswith("go-"):
        for prefix, desk in CAT_MAP:
            if raw.startswith(prefix):
                return desk
        return "GEO"
    for prefix, desk in CAT_MAP:
        if raw.startswith(prefix):
            return desk
    return "GEO"


def topic_from_category(raw: str) -> str:
    raw = (raw or "").lower()
    for prefix in ("stran-", "wm-digest-", "wm-", "go-"):
        if raw.startswith(prefix):
            return raw[len(prefix) :].replace("-", " ")[:20]
    return (raw or "general")[:20]


def url_host(url: str) -> str:
    try:
        host = urlparse(url).netloc.lower()
        if host.startswith("www."):
            host = host[4:]
        return host[:24]
    except Exception:
        return ""


def is_aggregator_url(url: str) -> bool:
    """Kept for callers; World Monitor parity keeps Google News topic feeds."""
    return False


def is_speculative_path(path: str) -> bool:
    if not path:
        return False
    p = path.replace("\\", "/")
    return any(m.replace("\\", "/") in p for m in SPECULATIVE_PATH_MARKERS)


def is_simulated_ref(project: dict) -> bool:
    ops = project.get("ops") or {}
    mode = str(ops.get("data_mode", "") or "").lower()
    role = str(project.get("desk_role", "") or "").lower()
    cat = str(project.get("category", "") or "").lower()
    if mode == "static":
        return True
    if cat == "web_clone":
        return True
    if "simul" in role or "demo only" in role or "no live" in role:
        return True
    return False


def simulated_ref_ids(ref_cfg: dict | None) -> set[str]:
    if not isinstance(ref_cfg, dict):
        return set()
    out: set[str] = set()
    for p in ref_cfg.get("projects", []) or []:
        if not isinstance(p, dict):
            continue
        if is_simulated_ref(p):
            pid = str(p.get("id", "") or "")
            if pid:
                out.add(pid)
                out.add(f"ref_{pid}")
    return out


def add(entries: list, **kw) -> None:
    origin = kw.get("origin", "")
    if origin in ("worldmonitor", "globeops", "wm", "go"):
        origin = url_host(kw.get("url", ""))
    e = {
        "id": kw.get("id", "")[:48],
        "section": kw.get("section", "API"),
        "status": kw.get("status", "planned"),
        "sector": kw.get("sector", "")[:12],
        "layer": kw.get("layer", "")[:20],
        "tier": kw.get("tier", "")[:12],
        "path": kw.get("path", "")[:96],
        "meta": kw.get("meta", "")[:200],
        "age_h": kw.get("age_h", -1),
        "max_age_h": kw.get("max_age_h", -1),
        "origin": origin[:24],
        "publisher": kw.get("publisher", "")[:48],
        "url": kw.get("url", "")[:256],
    }
    if kw.get("data_mode"):
        e["data_mode"] = str(kw["data_mode"])[:12]
    if "needs_map" in kw:
        e["needs_map"] = bool(kw["needs_map"])
    if kw.get("map_kind"):
        e["map_kind"] = str(kw["map_kind"])[:12]
    e["refresh_sec"] = default_refresh_sec(e["section"], kw.get("refresh_sec"))
    if kw.get("refresh_label"):
        e["refresh_label"] = str(kw["refresh_label"])[:120]
    entries.append(e)


def spine_lookup(status: dict | None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not status:
        return out
    for key in ("series", "pipelines", "external"):
        for row in status.get(key, []) or []:
            rid = row.get("id")
            if rid:
                out[rid] = row
    return out


def module_lookup(modules_index: dict | None) -> dict[str, dict]:
    out: dict[str, dict] = {}
    if not modules_index:
        return out
    for m in modules_index.get("modules", []) or []:
        mid = m.get("module")
        if mid:
            out[mid] = m
    return out


def load_feed_failures() -> dict[str, str]:
    """Map feed_id → last harvest error."""
    data = load_json(HERE / "feed_failures.json")
    out: dict[str, str] = {}
    if not data:
        return out
    rows: list = data if isinstance(data, list) else []
    if isinstance(data, dict):
        for k in ("failed", "failures", "feeds"):
            arr = data.get(k)
            if isinstance(arr, list):
                rows = arr
                break
    for x in rows:
        if isinstance(x, str):
            out[x] = "fail"
        elif isinstance(x, dict) and x.get("id"):
            out[str(x["id"])] = str(x.get("error", "fail"))
    return out


def rss_status_for_error(err: str) -> str:
    """Bot-blocked / unreachable publishers → blocked (amber), not hard fail."""
    e = (err or "").lower()
    if any(
        x in e
        for x in (
            "403",
            "forbidden",
            "certificate",
            "10061",
            "timed out",
            "timeout",
            "getaddrinfo",
            "connection reset",
            "unreachable",
            "404",
            "no parseable",
            "empty feed",
        )
    ):
        return "blocked"
    return "fail"


def export_reference_projects(cfg: Path, built: str) -> None:
    """Write compact spine module for 30 reference projects."""
    ref_path = cfg / "reference_projects.json"
    data = load_json(ref_path)
    if not isinstance(data, dict):
        return
    projects = data.get("projects") or []
    counts: dict[str, int] = {}
    for p in projects:
        tier = p.get("integration", "reference")
        counts[tier] = counts.get(tier, 0) + 1
    out = {
        "ok": True,
        "module": "reference_projects",
        "built_at": built,
        "message": f"{len(projects)} reference projects registered",
        "counts": counts,
        "projects": [
            {
                "num": p.get("num"),
                "id": p.get("id"),
                "name": p.get("name"),
                "integration": p.get("integration"),
                "desk_sector": p.get("desk_sector"),
                "data_portal": p.get("data_portal"),
                "data_portal_label": p.get("data_portal_label"),
                "data_sources": p.get("data_sources"),
                "ops": p.get("ops"),
            }
            for p in projects
        ],
    }
    spine_out = CACHE / "spine" / "modules" / "reference_projects.json"
    spine_out.parent.mkdir(parents=True, exist_ok=True)
    spine_out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {spine_out}  projects={len(projects)}")

    # Keep modules_index in sync — this module is built here (entry=null in modules.json)
    idx_path = CACHE / "spine" / "modules_index.json"
    idx = load_json(idx_path)
    if isinstance(idx, dict):
        mods = idx.get("modules") or []
        found = False
        for m in mods:
            if m.get("module") == "reference_projects":
                m["ok"] = True
                m["skipped"] = False
                m["message"] = out["message"]
                m.pop("trace", None)
                found = True
                break
        if not found:
            mods.append(
                {
                    "ok": True,
                    "module": "reference_projects",
                    "message": out["message"],
                }
            )
            idx["modules"] = mods
        brief = idx.get("brief", "") or ""
        brief = brief.replace("reference_projects:FAIL", "reference_projects:ok")
        if "reference_projects:ok" not in brief:
            brief = (brief + " | reference_projects:ok").strip(" |")
        idx["brief"] = brief
        idx_path.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")


def sort_entries(entries: list[dict]) -> None:
    def sort_key(e: dict) -> tuple:
        label = e.get("publisher") or e.get("meta") or e.get("id", "")
        if not isinstance(label, str):
            label = str(label)
        return (
            SECTION_ORDER.get(e.get("section", ""), 9),
            str(e.get("sector", "")),
            label.lower(),
        )

    entries.sort(key=sort_key)


def sync_wm_feeds() -> None:
    """Refresh intel_feeds.json from local World Monitor clone before building."""
    import subprocess
    import sys

    script = HERE / "import_wm_feeds.py"
    if not script.is_file():
        return
    try:
        subprocess.run([sys.executable, str(script)], cwd=str(ROOT), check=False, timeout=120)
    except Exception as e:
        print(f"WM feed sync skip: {e}")


def main() -> int:
    sync_wm_feeds()
    entries: list[dict] = []
    cfg = ROOT / "config"
    spine_status = load_json(CACHE / "spine" / "status.json")
    modules_index = load_json(CACHE / "spine" / "modules_index.json")
    spine_by_id = spine_lookup(spine_status if isinstance(spine_status, dict) else None)
    mod_by_id = module_lookup(modules_index if isinstance(modules_index, dict) else None)
    feed_failures = load_feed_failures()
    ref_cfg = load_json(cfg / "reference_projects.json")
    skip_ids = simulated_ref_ids(ref_cfg if isinstance(ref_cfg, dict) else None)

    # --- API: OSS registry adapters ---
    ds = load_json(cfg / "data_sources.json")
    if isinstance(ds, dict):
        for s in ds.get("sources", []) or []:
            sid = s.get("id", "")
            if sid in skip_ids:
                continue
            mod = mod_by_id.get(f"{sid}_harvest") or mod_by_id.get(sid)
            st = "disabled"
            meta = s.get("desk_role") or s.get("adapter") or ""
            if mod:
                if mod.get("skipped"):
                    st = "disabled"
                elif mod.get("ok"):
                    st = "ok"
                else:
                    st = "fail"
                meta = mod.get("message") or meta
            elif s.get("enabled_default"):
                st = "planned"
            elif s.get("optional"):
                st = "optional"
            add(
                entries,
                id=sid,
                section="API",
                status=st,
                sector=(s.get("sector", "") or "data").upper()[:12],
                layer=s.get("layer", "adapter"),
                tier="registry",
                publisher=sid,
                meta=meta,
                path=s.get("adapter") or s.get("repo", ""),
                url=s.get("repo", "") if str(s.get("repo", "")).startswith("http") else "",
            )

    mods = load_json(cfg / "modules.json")
    if isinstance(mods, dict):
        for m in mods.get("modules", []) or []:
            mid = m.get("id", "")
            if not mid or mid in skip_ids:
                continue
            rt = mod_by_id.get(mid, {})
            st = "disabled"
            if m.get("enabled"):
                st = "ok" if rt.get("ok", True) else "fail"
                if rt.get("skipped"):
                    st = "disabled"
            # built by build_ingest_manifest itself (entry=null in modules.json)
            if mid == "reference_projects":
                st = "ok"
            outs = m.get("outputs") or []
            add(
                entries,
                id=mid,
                section="API",
                status=st,
                sector=(m.get("sector", "") or "bridge").upper()[:12],
                layer=m.get("tier", "module"),
                tier=m.get("tier", ""),
                publisher=mid,
                meta=rt.get("message") or m.get("description", ""),
                path=outs[0] if outs else m.get("entry", ""),
            )
        for ea in mods.get("external_adapters", []) or []:
            eid = ea.get("id", "")
            if not eid or eid in skip_ids:
                continue
            # Pure UI reference clones without harvest/module → not concrete ingest sources
            integ = str(ea.get("integration", "") or "")
            if integ == "reference" and not ea.get("harvest") and not ea.get("module"):
                continue
            add(
                entries,
                id=eid,
                section="API",
                status="optional",
                sector=(ea.get("sector", "") or "bridge").upper()[:12],
                layer="adapter",
                publisher=eid,
                meta=ea.get("repo", "") or ea.get("companion", ""),
                url=ea.get("repo", "") if str(ea.get("repo", "")).startswith("http") else "",
            )

    # --- REF: reference projects (skip simulated / web_clone) ---
    if isinstance(ref_cfg, dict):
        for p in ref_cfg.get("projects", []) or []:
            pid = p.get("id", "")
            if is_simulated_ref(p):
                continue
            integration = p.get("integration", "reference")
            st = "ok" if integration == "integrated" else "partial" if integration == "partial" else "optional"
            if integration == "adapter_off":
                st = "optional"
            mod_id = p.get("module_id", "")
            if mod_id:
                rt = mod_by_id.get(mod_id, {})
                if rt.get("ok"):
                    st = "ok"
                elif rt.get("skipped") or integration == "adapter_off":
                    st = "optional"
                elif p.get("integration") == "integrated" and not rt:
                    st = "planned"
            ops = p.get("ops") or {}
            add(
                entries,
                id=f"ref_{pid}",
                section="REF",
                status=st,
                sector=(p.get("desk_sector", "") or "REF")[:12],
                layer=p.get("category", "reference")[:20],
                tier=integration,
                publisher=p.get("name", pid)[:48],
                url=p.get("data_portal", ""),
                path=p.get("data_sources", ""),
                meta=p.get("desk_role", "")[:200],
                origin=pid[:24],
                data_mode=ops.get("data_mode"),
                needs_map=ops.get("needs_map", False),
                map_kind=ops.get("map_kind"),
                refresh_sec=ops.get("refresh_sec"),
                refresh_label=ops.get("refresh_label"),
            )

    # --- API: spine live series + external endpoints ---
    spine_cfg = load_json(cfg / "desk_spine.json")
    if isinstance(spine_cfg, dict):
        for s in spine_cfg.get("series", []) or []:
            sid = s.get("id", "")
            rt = spine_by_id.get(sid, {})
            paths = s.get("paths") or []
            add(
                entries,
                id=sid,
                section="API",
                status=rt.get("status", "missing"),
                sector="MARKET",
                layer="series",
                tier=s.get("tier", ""),
                publisher=sid,
                path=rt.get("path") or (paths[0] if paths else ""),
                meta=s.get("backend", ""),
                age_h=rt.get("age_h", -1) if rt.get("age_h") is not None else -1,
                max_age_h=rt.get("max_age_h", s.get("max_age_h", -1)),
            )
        for e in spine_cfg.get("external", []) or []:
            eid = e.get("id", "")
            rt = spine_by_id.get(eid, {})
            add(
                entries,
                id=eid,
                section="API",
                status=rt.get("status", "optional_missing"),
                sector="EXTERNAL",
                layer="live",
                publisher=eid,
                path=rt.get("path") or e.get("path", ""),
                meta=e.get("backend", "") or eid,
                age_h=rt.get("age_h", -1) if rt.get("age_h") is not None else -1,
                max_age_h=e.get("max_age_h", -1),
            )

    # --- API: live streams (World Monitor + GlobeOps parity) ---
    live_cfg = load_json(HERE / "live_streams.json")
    if isinstance(live_cfg, dict):
        for s in live_cfg.get("streams", []) or []:
            sid = s.get("id", "")
            env_key = s.get("env_key", "")
            st = "optional" if s.get("optional") else "ok"
            if env_key and not has_key(env_key, CACHE):
                st = "optional"
            add(
                entries,
                id=sid,
                section="API",
                status=st,
                sector=(s.get("sector", "") or "LIVE")[:12],
                layer=s.get("type", "stream"),
                publisher=s.get("name", sid),
                url=s.get("url", ""),
                origin=url_host(s.get("url", "")),
                meta=(s.get("ref", "") + " " if s.get("ref") else "")
                + (s.get("note", "") or f"refresh={s.get('refresh_sec', 0)}s"),
            )

    # --- PIPE: harvest orchestration + spine pipelines ---
    if isinstance(spine_cfg, dict):
        for p in spine_cfg.get("pipelines", []) or []:
            pid = p.get("id", "")
            rt = spine_by_id.get(pid, {})
            paths = p.get("paths") or []
            add(
                entries,
                id=pid,
                section="PIPE",
                status=rt.get("status", "missing"),
                sector="HARVEST",
                layer="pipeline",
                tier=p.get("tier", ""),
                publisher=pid,
                path=rt.get("path") or (paths[0] if paths else ""),
                meta=p.get("script", "") or "",
                age_h=rt.get("age_h", -1) if rt.get("age_h") is not None else -1,
                max_age_h=rt.get("max_age_h", p.get("max_age_h", -1)),
            )

    harvest_steps = [
        ("rss_catalog_sync", "intel", "scripts/desk_harvest/import_wm_feeds.py", "RSS catalog sync (WM+GO)"),
        ("harvest_live_streams", "live", "scripts/desk_harvest/harvest_live_streams.py", "Live API streams WM+GO"),
        ("harvest_intel", "intel", "scripts/desk_harvest/harvest_intel.py", "RSS headline harvest"),
        ("harvest_fred", "macro", "scripts/desk_harvest/harvest_fred.py", "FRED macro series"),
        ("harvest_ecb", "fx", "scripts/desk_harvest/harvest_ecb.py", "ECB FX rates"),
        ("harvest_crypto", "crypto", "scripts/desk_harvest/harvest_crypto.py", "Binance klines"),
        ("harvest_equities", "equity", "scripts/desk_harvest/harvest_equities.py", "Equity history"),
        ("harvest_eia", "energy", "scripts/desk_harvest/harvest_eia.py", "EIA energy data"),
        ("harvest_entsoe", "energy", "scripts/desk_harvest/harvest_entsoe.py", "ENTSO-E power"),
        ("harvest_portwatch", "maritime", "scripts/desk_harvest/harvest_portwatch.py", "PortWatch AIS"),
        ("ingest_imf_weo", "macro", "scripts/desk_harvest/ingest_imf_weo.py", "IMF World Economic Outlook"),
        ("spine_build", "qa", "scripts/spine_build.py", "Spine status + manifest"),
        ("libero", "macro", "scripts/libero/fetch_all.py", "Libero macro fetch"),
    ]
    for hid, sec, script, label in harvest_steps:
        add(
            entries,
            id=hid,
            section="PIPE",
            status="ok",
            sector=sec.upper(),
            layer="step",
            publisher=label,
            path=script,
            meta=label,
        )

    # --- SER: IMF WEO key dump (if ingested) ---
    weo_sum = load_json(CACHE / "imf" / "weo_summary.json")
    weo_raw = CACHE / "imf" / "weo_raw.csv"
    weo_key = CACHE / "imf" / "weo_key.csv"
    if isinstance(weo_sum, dict) and weo_raw.is_file():
        st = weo_sum.get("status", "ok")
        age_h = -1
        try:
            mtime = weo_raw.stat().st_mtime
            age_h = int((datetime.now().timestamp() - mtime) / 3600)
        except OSError:
            pass
        add(
            entries,
            id="imf_weo",
            section="SER",
            status=st,
            sector="MACRO",
            layer="imf_weo",
            tier="reference",
            publisher="IMF WEO",
            origin="data.imf.org",
            url="https://data.imf.org/en/datasets/IMF.RES:WEO",
            path=str(weo_key.as_posix()) if weo_key.is_file() else str(weo_raw.as_posix()),
            meta=(
                f"countries={weo_sum.get('countries', '?')} "
                f"indicators={weo_sum.get('indicators', '?')} "
                f"years={weo_sum.get('year_min')}-{weo_sum.get('year_max')} "
                f"rows={weo_sum.get('rows_out', '?')}"
            ),
            age_h=age_h,
            max_age_h=24 * 45,
            refresh_sec=86400 * 30,
            refresh_label="WEO release ~30d",
            data_mode="batch",
        )
        for code, label in [
            ("NGDPD", "GDP current USD bn"),
            ("NGDP_RPCH", "Real GDP % change"),
            ("PCPI", "CPI period average"),
            ("LUR", "Unemployment rate"),
            ("BCA", "Current account USD"),
            ("GGXWDG", "Gov gross debt"),
            ("LP", "Population"),
            ("PPPGDP", "GDP PPP"),
        ]:
            add(
                entries,
                id=f"weo_{code}",
                section="SER",
                status=st,
                sector="MACRO",
                layer="imf_weo",
                publisher="IMF WEO",
                origin="data.imf.org",
                path=str(weo_key.as_posix()) if weo_key.is_file() else "",
                meta=label,
                url="https://data.imf.org/en/datasets/IMF.RES:WEO",
                refresh_sec=86400 * 30,
            )

    # --- RSS: World Monitor catalog (incl. Google News topic feeds) ---
    feeds_doc = load_json(HERE / "intel_feeds.json")
    if isinstance(feeds_doc, dict):
        for f in feeds_doc.get("feeds", []) or []:
            fid = f.get("id", "")
            name = f.get("name", "")
            url = f.get("url", "")
            cat = f.get("category", "")
            err = feed_failures.get(fid)
            st = rss_status_for_error(err) if err else "ok"
            add(
                entries,
                id=fid,
                section="RSS",
                status=st,
                sector=desk_for_category(cat),
                layer=topic_from_category(cat),
                publisher=name,
                origin=url_host(url) or "worldmonitor",
                url=url,
                meta=name,
            )

    # --- SER: desk catalog (series, pairs, zones) — real backends only ---
    # Desk hypothesis signals (MAR-02 Malacca/Hormuz, GAS-*, research md) are skipped.
    cat = load_json(cfg / "generated" / "catalog.json")
    if isinstance(cat, dict):
        for s in cat.get("series", []) or []:
            paths = s.get("paths") or []
            sid = s.get("id", "")
            add(
                entries,
                id=sid,
                section="SER",
                status="ok",
                sector="MACRO",
                layer=s.get("backend", "fred"),
                publisher=sid,
                path=paths[0] if paths else "",
                meta=f"fred={s.get('fred_id', '')}",
            )
        for p in cat.get("pairs", []) or []:
            pid = p.get("id", "")
            add(
                entries,
                id=pid,
                section="SER",
                status="ok",
                sector="FX",
                layer="pair",
                publisher=pid,
                meta=f"{p.get('base', '')}/{p.get('quote', '')} desk={p.get('desk_id', '')}",
            )

    fxm = load_json(cfg / "fx_manifest.json")
    if isinstance(fxm, dict):
        for p in fxm.get("pairs", []) or []:
            pid = p.get("id", "")
            if any(e["id"] == pid and e["section"] == "SER" for e in entries):
                continue
            add(
                entries,
                id=pid,
                section="SER",
                status="ok",
                sector="FX",
                layer="manifest",
                publisher=pid,
                meta=f"{p.get('base', '')}/{p.get('quote', '')} desk={p.get('desk_id', '')}",
            )

    wxm = load_json(cfg / "weather_manifest.json")
    if isinstance(wxm, dict):
        for z in wxm.get("zones", []) or []:
            zid = z.get("id", "")
            add(
                entries,
                id=zid,
                section="SER",
                status="ok",
                sector="WEATHER",
                layer="zone",
                publisher=z.get("name", zid),
                meta=f"{z.get('name', '')} pwr={z.get('power_desk', '')} gas={z.get('gas_proxy', '')}",
            )
        for step in wxm.get("pipeline", []) or []:
            add(
                entries,
                id=step,
                section="SER",
                status="ok",
                sector="WEATHER",
                layer="pipeline",
                publisher=step,
                meta="weather pipeline",
            )

    pw = load_json(cfg / "power_wind.json")
    if isinstance(pw, dict):
        for desk, info in (pw.get("desks") or {}).items():
            if not isinstance(info, dict):
                continue
            for gp in info.get("grid_points", []) or []:
                gid = gp.get("id", desk)
                eid = f"{desk}_{gid}"
                add(
                    entries,
                    id=eid,
                    section="SER",
                    status="ok",
                    sector="ENERGY",
                    layer="grid",
                    publisher=gid,
                    meta=f"{info.get('country', '')} lat={gp.get('lat', '')} lon={gp.get('lon', '')}",
                )

    # Hypothesis signals (MAR-02 Malacca/Hormuz, GAS-*, research notes) stay in
    # config/signals.json for research — deliberately omitted from INGEST.

    try:
        import series_config as sc  # noqa: PLC0415

        for row in getattr(sc, "DESK_FRED", []):
            did = row.desk_id if hasattr(row, "desk_id") else row[0]
            fid = row.fred_id if hasattr(row, "fred_id") else row[1]
            if any(e["id"] == did and e["section"] == "SER" for e in entries):
                continue
            add(
                entries,
                id=did,
                section="SER",
                status="ok",
                sector="MACRO",
                layer="desk_fred",
                publisher=did,
                meta=f"fred_id={fid}",
            )
        for sym in getattr(sc, "BINANCE_SYMBOLS", []):
            add(
                entries,
                id=sym,
                section="SER",
                status="ok",
                sector="CRYPTO",
                layer="binance",
                publisher=sym,
                meta="klines 1d",
            )
        for sym in getattr(sc, "YAHOO_EQUITIES", []):
            add(
                entries,
                id=sym,
                section="SER",
                status="ok",
                sector="EQUITY",
                layer="stooq",
                publisher=sym,
                meta="yahoo/stooq hist",
            )
    except Exception:
        pass

    # Final safety: drop any leftover research/hypothesis paths
    entries[:] = [
        e
        for e in entries
        if not is_speculative_path(str(e.get("path", "")))
        and not is_aggregator_url(str(e.get("url", "")))
    ]

    sort_entries(entries)

    by_sec: dict[str, int] = {}
    by_st: dict[str, int] = {}
    for e in entries:
        by_sec[e["section"]] = by_sec.get(e["section"], 0) + 1
        by_st[e["status"]] = by_st.get(e["status"], 0) + 1

    built = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # Prefer live build time for ING UI mtime/reload; keep spine as meta only
    spine_built = ""
    if isinstance(spine_status, dict) and spine_status.get("built_at"):
        spine_built = str(spine_status["built_at"])

    manifest = {
        "version": 3,
        "policy": "worldmonitor_parity",
        "built_at": built,
        "spine_built_at": spine_built,
        "summary": {
            "total": len(entries),
            "pipe": by_sec.get("PIPE", 0),
            "api": by_sec.get("API", 0),
            "ref": by_sec.get("REF", 0),
            "rss": by_sec.get("RSS", 0),
            "ser": by_sec.get("SER", 0),
            "ok": by_st.get("ok", 0),
            "fail": by_st.get("fail", 0),
            "disabled": by_st.get("disabled", 0),
            "optional": by_st.get("optional", 0),
            "missing": sum(v for k, v in by_st.items() if "missing" in k),
        },
        "entries": entries,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    export_reference_projects(cfg, built)
    print(
        f"Wrote {OUT}  total={len(entries)}  "
        f"PIPE={by_sec.get('PIPE', 0)} API={by_sec.get('API', 0)} "
        f"REF={by_sec.get('REF', 0)} RSS={by_sec.get('RSS', 0)} SER={by_sec.get('SER', 0)}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
