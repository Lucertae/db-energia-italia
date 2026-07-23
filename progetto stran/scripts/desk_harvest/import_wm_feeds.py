#!/usr/bin/env python3
"""Build intel_feeds.json — World Monitor ingestion paro paro.

Primary source: local clone Desktop/str/worldmonitor-ingestion (feeds.ts,
variants, server digest _feeds.ts). Falls back to GitHub raw if clone missing.
Includes Google News topic feeds exactly as WM defines them.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import urllib.parse
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("DESK_ROOT", HERE.parents[1]))
OUT = HERE / "intel_feeds.json"
REGISTRY = HERE / "intel_feed_registry.json"
WM_MIRROR = HERE / "wm_upstream"  # copied configs for audit

UA = "ops-desk-wm-parity/3.0"
WM_LOCAL_CANDIDATES = [
    Path(os.environ.get("WM_ROOT", "")),
    Path(r"c:\Users\jecho\Desktop\str\worldmonitor-ingestion"),
    ROOT.parent / "str" / "worldmonitor-ingestion",
    ROOT / ".." / "str" / "worldmonitor-ingestion",
]
WM_BASE = "https://raw.githubusercontent.com/koala73/worldmonitor/main"

WM_REL_FILES = [
    ("feeds.ts", "src/config/feeds.ts", "wm"),
    ("full.ts", "src/config/variants/full.ts", "wm-full"),
    ("base.ts", "src/config/variants/base.ts", "wm-base"),
    ("finance.ts", "src/config/variants/finance.ts", "wm-finance"),
    ("tech.ts", "src/config/variants/tech.ts", "wm-tech"),
    ("commodity.ts", "src/config/variants/commodity.ts", "wm-commodity"),
    ("energy.ts", "src/config/variants/energy.ts", "wm-energy"),
    ("happy.ts", "src/config/variants/happy.ts", "wm-happy"),
    ("_feeds.ts", "server/worldmonitor/news/v1/_feeds.ts", "wm-digest"),
]

WM_EXTRA_COPY = [
    "data/telegram-channels.json",
    "src/config/map-layer-definitions.ts",
]


def find_wm_root() -> Path | None:
    for p in WM_LOCAL_CANDIDATES:
        if not p or str(p) in (".", ""):
            continue
        try:
            rp = p.resolve()
        except OSError:
            continue
        if (rp / "src" / "config" / "feeds.ts").is_file():
            return rp
    return None


def fetch_url(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=90) as resp:
        return resp.read().decode("utf-8", errors="replace")


def read_wm_file(wm_root: Path | None, rel: str) -> tuple[str, str]:
    """Return (text, source_label)."""
    if wm_root:
        path = wm_root / rel.replace("/", os.sep)
        if path.is_file():
            return path.read_text(encoding="utf-8", errors="replace"), f"local:{rel}"
    return fetch_url(f"{WM_BASE}/{rel}"), f"github:{rel}"


def gn(q: str) -> str:
    return (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote(q, safe="")
        + "&hl=en-US&gl=US&ceid=US:en"
    )


def gn_locale(q: str, hl: str, gl: str, ceid: str) -> str:
    return (
        "https://news.google.com/rss/search?q="
        + urllib.parse.quote(q, safe="")
        + f"&hl={hl}&gl={gl}&ceid={ceid}"
    )


def url_host(url: str) -> str:
    try:
        h = urllib.parse.urlparse(url).netloc.lower()
        return h[4:] if h.startswith("www.") else h
    except Exception:
        return ""


def slug_id(prefix: str, name: str, url: str) -> str:
    h = hashlib.sha1(f"{name}|{url}".encode()).hexdigest()[:8].upper()
    p = re.sub(r"[^A-Z]", "", prefix.upper())[:2] or "WM"
    return f"{p}{h}"[:11]


def resolve_url_expr(expr: str) -> str | None:
    expr = expr.strip().rstrip(",")
    m = re.match(r"rss\(\s*'((?:\\'|[^'])*)'\s*\)", expr)
    if m:
        u = m.group(1).replace("\\'", "'")
        return u if u.startswith("http") else None
    m = re.match(r'rss\(\s*"((?:\\"|[^"])*)"\s*\)', expr)
    if m:
        u = m.group(1).replace('\\"', '"')
        return u if u.startswith("http") else None
    m = re.match(r"railwayRss\(\s*'((?:\\'|[^'])*)'\s*\)", expr)
    if m:
        u = m.group(1).replace("\\'", "'")
        return u if u.startswith("http") else None
    m = re.match(r"gn\(\s*'((?:\\'|[^'])*)'\s*\)", expr)
    if m:
        return gn(m.group(1).replace("\\'", "'"))
    m = re.match(r'gn\(\s*"((?:\\"|[^"])*)"\s*\)', expr)
    if m:
        return gn(m.group(1).replace('\\"', '"'))
    m = re.match(
        r"gnLocale\(\s*'((?:\\'|[^'])*)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*,\s*'([^']+)'\s*\)",
        expr,
    )
    if m:
        return gn_locale(m.group(1).replace("\\'", "'"), m.group(2), m.group(3), m.group(4))
    if (expr.startswith("'") and expr.endswith("'")) or (expr.startswith('"') and expr.endswith('"')):
        u = expr[1:-1]
        return u if u.startswith("http") else None
    return None


def category_map(text: str) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    for m in re.finditer(r"^\s*(\w+)\s*:\s*\[", text, re.M):
        out.append((m.start(), m.group(1)))
    return out


def category_at(cats: list[tuple[int, str]], pos: int, default: str) -> str:
    c = default
    for p, name in cats:
        if p <= pos:
            c = name
        else:
            break
    return c


def parse_wm_text(text: str, cat_prefix: str) -> list[dict]:
    """Extract all named feeds including nested locale url maps (WM style)."""
    feeds: list[dict] = []
    cats = category_map(text)
    default = "general"

    # Objects with name + url (flat): { name: 'X', url: rss('...') | gn('...') }
    for m in re.finditer(
        r"\{\s*name:\s*'([^']+)'\s*,\s*url:\s*([^,{]+?)(?:,\s*lang:[^}]*)?\s*\}",
        text,
        re.S,
    ):
        name, expr = m.group(1), m.group(2)
        url = resolve_url_expr(expr)
        if not url:
            continue
        cat = category_at(cats, m.start(), default)
        feeds.append({
            "name": name,
            "url": url,
            "category": f"{cat_prefix}-{cat}" if cat_prefix else cat,
        })

    # Nested locale maps:
    # { name: 'France 24', url: { en: rss('...'), fr: rss('...') } }
    for m in re.finditer(
        r"\{\s*name:\s*'([^']+)'\s*,\s*url:\s*\{([^{}]+)\}\s*\}",
        text,
        re.S,
    ):
        name, body = m.group(1), m.group(2)
        cat = category_at(cats, m.start(), default)
        for lm in re.finditer(
            r"(\w+)\s*:\s*(rss\([^)]+\)|railwayRss\([^)]+\)|gn\([^)]+\)|gnLocale\([^)]+\)|'[^']+'|\"[^\"]+\")",
            body,
        ):
            lang, expr = lm.group(1), lm.group(2)
            url = resolve_url_expr(expr)
            if not url:
                continue
            feeds.append({
                "name": f"{name} [{lang}]",
                "url": url,
                "category": f"{cat_prefix}-{cat}" if cat_prefix else cat,
            })

    # digest-style double quotes names
    for m in re.finditer(
        r'\{\s*name:\s*"([^"]+)"\s*,\s*url:\s*([^,}]+)',
        text,
    ):
        name, expr = m.group(1), m.group(2)
        url = resolve_url_expr(expr)
        if not url:
            continue
        cat = category_at(cats, m.start(), default)
        feeds.append({
            "name": name,
            "url": url,
            "category": f"{cat_prefix}-{cat}" if cat_prefix else cat,
        })

    return feeds


def dedupe(feeds: list[dict]) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []
    for f in feeds:
        key = f["url"].rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(f)
    return out


def mirror_wm_files(wm_root: Path | None) -> None:
    """Keep a local mirror of WM ingest configs next to desk_harvest."""
    if not wm_root:
        return
    WM_MIRROR.mkdir(parents=True, exist_ok=True)
    for rel in [r for _, r, _ in WM_REL_FILES] + WM_EXTRA_COPY:
        src = wm_root / rel.replace("/", os.sep)
        if not src.is_file():
            continue
        dst = WM_MIRROR / rel.replace("/", os.sep)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        print(f"mirror {rel}")


def main() -> int:
    wm_root = find_wm_root()
    if wm_root:
        print(f"WM_ROOT={wm_root}")
    else:
        print("WM_ROOT missing — using GitHub raw koala73/worldmonitor")

    mirror_wm_files(wm_root)

    merged: list[dict] = []
    sources_ok: list[str] = []

    for label, rel, prefix in WM_REL_FILES:
        try:
            raw, src = read_wm_file(wm_root, rel)
            got = parse_wm_text(raw, prefix)
            merged.extend(got)
            sources_ok.append(src)
            print(f"WM {label}: +{len(got)}  ({src})")
        except Exception as e:
            print(f"WM {label}: FAIL ({e})")

    # Telegram channels → synthetic RSS via Google News site:t.me queries (WM OSINT surface)
    tg_path = None
    if wm_root and (wm_root / "data" / "telegram-channels.json").is_file():
        tg_path = wm_root / "data" / "telegram-channels.json"
    elif (WM_MIRROR / "data" / "telegram-channels.json").is_file():
        tg_path = WM_MIRROR / "data" / "telegram-channels.json"
    if tg_path:
        try:
            tg = json.loads(tg_path.read_text(encoding="utf-8"))
            n = 0
            channels_root = tg.get("channels", tg) if isinstance(tg, dict) else {}
            if isinstance(channels_root, dict):
                for variant, channels in channels_root.items():
                    if not isinstance(channels, list):
                        continue
                    for ch in channels:
                        if not isinstance(ch, dict):
                            continue
                        if ch.get("enabled") is False:
                            continue
                        handle = (ch.get("handle") or ch.get("username") or "").lstrip("@")
                        name = ch.get("label") or ch.get("name") or handle
                        if not handle:
                            continue
                        url = gn(f"site:t.me/{handle} OR @{handle}")
                        merged.append({
                            "name": f"TG {name}",
                            "url": url,
                            "category": f"wm-telegram-{variant}",
                        })
                        n += 1
            print(f"WM telegram-channels: +{n}")
            sources_ok.append("telegram-channels.json")
        except Exception as e:
            print(f"WM telegram skip: {e}")

    # Layer registry snapshot for MAP tab / parity docs
    layer_src = None
    if wm_root:
        p = wm_root / "src" / "config" / "map-layer-definitions.ts"
        if p.is_file():
            layer_src = p
    if layer_src:
        text = layer_src.read_text(encoding="utf-8", errors="replace")
        keys = re.findall(r"^\s{2}(\w+):\s+def\(", text, re.M)
        if not keys:
            keys = re.findall(r"^\s{2}(\w+):\s*\{\s*$", text, re.M)
            keys = [k for k in keys if k[0].islower()]
        if keys:
            out_layers = ROOT / "cache" / "ingest" / "wm_layer_sources.json"
            out_layers.parent.mkdir(parents=True, exist_ok=True)
            prev = {}
            if out_layers.is_file():
                try:
                    prev = json.loads(out_layers.read_text(encoding="utf-8"))
                except Exception:
                    prev = {}
            # labels from def('key', ..., 'Label')
            labels = {}
            for km in re.finditer(
                r"^\s{2}(\w+):\s+def\(\s*'[^']+'\s*,\s*'[^']*'\s*,\s*'[^']*'\s*,\s*'([^']+)'",
                text,
                re.M,
            ):
                labels[km.group(1)] = km.group(2)
            doc = {
                "keys": keys,
                "count": len(keys),
                "labels": labels,
                "source": str(layer_src),
                "sources": prev.get("sources", []),
            }
            out_layers.write_text(json.dumps(doc, indent=2), encoding="utf-8")
            print(f"WM layers: {len(keys)} keys -> {out_layers}")

    merged = dedupe(merged)
    gnews_n = sum(1 for f in merged if "news.google.com" in f["url"].lower())
    print(f"Merged unique RSS URLs: {len(merged)}  (google_news={gnews_n})")

    registry: dict[str, dict] = {}
    out_feeds: list[dict] = []
    for f in merged:
        prefix = "WM"
        if f["category"].startswith("wm-"):
            prefix = "WM"
        fid = slug_id(prefix, f["name"], f["url"])
        # avoid id collisions
        base = fid
        n = 0
        while fid in registry:
            n += 1
            fid = f"{base[:8]}{n}"[:11]
        entry = {
            "id": fid,
            "name": f["name"],
            "url": f["url"],
            "category": f["category"],
            "origin": url_host(f["url"]) or "worldmonitor",
            "ref": "worldmonitor",
        }
        out_feeds.append(entry)
        registry[fid] = {
            "name": f["name"],
            "url": f["url"],
            "category": f["category"],
            "ref": "worldmonitor",
        }

    cfg = {
        "version": 4,
        "policy": "worldmonitor_parity",
        "wm_root": str(wm_root) if wm_root else None,
        "generated_from": sources_ok,
        "feed_count": len(out_feeds),
        "google_news_count": gnews_n,
        "feeds": out_feeds,
        "max_per_feed": 5,
        "max_total": 20000,
        "concurrency": 24,
        "timeout_sec": 25,
        "fail_fast": False,
    }
    OUT.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"OK wrote {OUT} ({len(out_feeds)} feeds) — World Monitor paro paro")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
