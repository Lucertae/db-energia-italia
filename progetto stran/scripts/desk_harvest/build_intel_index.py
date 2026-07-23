#!/usr/bin/env python3
"""Build cache/intel/desk_index.json — headlines by desk category + live events."""
from __future__ import annotations

import csv
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CACHE = ROOT / "cache" / "intel"
LIVE = ROOT / "cache" / "live" / "events.json"
FEEDS = HERE / "intel_feeds.json"
REGISTRY = HERE / "intel_feed_registry.json"
HEADLINES = CACHE / "headlines.csv"
OUT = CACHE / "desk_index.json"

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)

DESK_CATS = [
    ("ALL", "ALL"),
    ("ENERGY", "ENERGY"),
    ("GEO", "GEO/POL"),
    ("DEFENSE", "DEFENSE"),
    ("FINANCE", "FINANCE"),
    ("TECH", "TECH/AI"),
    ("CLIMATE", "CLIMATE"),
    ("MARITIME", "MARITIME"),
]

# wm-*/go-*/stran-* prefix → desk category
CAT_MAP: list[tuple[str, str]] = [
    ("stran-maritime", "MARITIME"),
    ("stran-energy", "ENERGY"),
    ("stran-finance", "FINANCE"),
    ("stran-regulatory", "FINANCE"),
    ("stran-macro", "FINANCE"),
    ("stran-humanitarian", "DEFENSE"),
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


def desk_for_category(raw: str) -> str:
    raw = (raw or "").lower()
    for prefix, desk in CAT_MAP:
        if raw.startswith(prefix):
            return desk
    if raw.startswith("go-"):
        return "GEO"
    if raw.startswith("wm-"):
        return "GEO"
    return "GEO"


def fetch_json(url: str) -> dict | list:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", errors="replace"))


def harvest_events() -> list[dict]:
    """Load live events from harvest_live_streams cache; fallback to inline poll."""
    if LIVE.is_file():
        try:
            data = json.loads(LIVE.read_text(encoding="utf-8"))
            events = data.get("events", [])
            if events:
                return events
        except (json.JSONDecodeError, OSError):
            pass
    return _harvest_events_inline()


def _harvest_events_inline() -> list[dict]:
    events: list[dict] = []
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # USGS earthquakes (24h, M4.5+)
    try:
        data = fetch_json(
            "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson"
        )
        for f in data.get("features", [])[:40]:
            p = f.get("properties", {})
            g = f.get("geometry", {}).get("coordinates", [0, 0, 0])
            events.append({
                "type": "quake",
                "ts": p.get("time", "") and datetime.fromtimestamp(
                    p["time"] / 1000, tz=timezone.utc
                ).strftime("%Y-%m-%dT%H:%M:%SZ") or now,
                "title": p.get("title", "Earthquake")[:200],
                "severity": f"M{p.get('mag', 0):.1f}",
                "lat": g[1] if len(g) > 1 else 0,
                "lon": g[0] if len(g) > 0 else 0,
                "source": "USGS",
            })
    except Exception as e:
        events.append({"type": "meta", "ts": now, "title": f"USGS skip: {e}", "source": "SYS"})

    # GDACS disaster alerts (RSS via feedparser-less regex)
    try:
        req = urllib.request.Request("https://www.gdacs.org/xml/rss.xml", headers={"User-Agent": UA})
        raw = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", errors="replace")
        for m in re.finditer(r"<item>(.*?)</item>", raw, re.S):
            block = m.group(1)
            title = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.S)
            pub = re.search(r"<pubDate>(.*?)</pubDate>", block)
            link = re.search(r"<link>(.*?)</link>", block)
            if not title:
                continue
            t = re.sub(r"<[^>]+>", "", title.group(1)).strip()
            events.append({
                "type": "disaster",
                "ts": pub.group(1)[:32] if pub else now,
                "title": t[:200],
                "severity": "GDACS",
                "url": link.group(1).strip() if link else "",
                "source": "GDACS",
            })
            if len([e for e in events if e.get("type") == "disaster"]) >= 25:
                break
    except Exception as e:
        events.append({"type": "meta", "ts": now, "title": f"GDACS skip: {e}", "source": "SYS"})

    # NOAA active weather alerts (cap 20)
    try:
        data = fetch_json("https://api.weather.gov/alerts/active?status=actual&message_type=alert")
        for f in data.get("features", [])[:20]:
            p = f.get("properties", {})
            events.append({
                "type": "weather",
                "ts": (p.get("sent") or now)[:24],
                "title": (p.get("event", "") + " — " + (p.get("areaDesc") or ""))[:200],
                "severity": p.get("severity", "")[:16],
                "source": "NOAA",
            })
    except Exception as e:
        events.append({"type": "meta", "ts": now, "title": f"NOAA skip: {e}", "source": "SYS"})

    # CoinGecko global (market pulse)
    try:
        data = fetch_json("https://api.coingecko.com/api/v3/global")
        d = data.get("data", {})
        mc = d.get("total_market_cap", {}).get("usd", 0)
        ch = d.get("market_cap_change_percentage_24h_usd", 0)
        events.append({
            "type": "market",
            "ts": now,
            "title": f"Crypto mcap ${mc/1e12:.2f}T  24h {ch:+.1f}%",
            "severity": "CG",
            "source": "CoinGecko",
        })
    except Exception:
        pass

    # Polymarket — top active markets by volume
    try:
        data = fetch_json("https://gamma-api.polymarket.com/markets?active=true&closed=false&limit=8")
        if isinstance(data, list):
            for m in data[:8]:
                q = (m.get("question") or "")[:160]
                vol = m.get("volume") or m.get("volumeNum") or 0
                try:
                    vol = float(vol)
                except (TypeError, ValueError):
                    vol = 0.0
                events.append({
                    "type": "market",
                    "ts": now,
                    "title": f"{q}  vol ${vol/1e6:.1f}M" if vol else q,
                    "severity": "POLY",
                    "source": "Polymarket",
                })
    except Exception:
        pass

    # OpenSky — aircraft over Europe (bbox)
    try:
        data = fetch_json(
            "https://opensky-network.org/api/states/all"
            "?lamin=35&lomin=-12&lamax=62&lomax=28"
        )
        n = len(data.get("states") or [])
        events.append({
            "type": "ais",
            "ts": now,
            "title": f"OpenSky aircraft over EU waters bbox: {n}",
            "severity": "OS",
            "source": "OpenSky",
        })
    except Exception:
        pass

    return events


def main() -> int:
    registry: dict = {}
    if REGISTRY.is_file():
        registry = json.loads(REGISTRY.read_text(encoding="utf-8"))

    id_to_desk: dict[str, str] = {}
    for fid, meta in registry.items():
        id_to_desk[fid] = desk_for_category(meta.get("category", ""))

    rows: list[dict] = []
    if HEADLINES.is_file():
        with HEADLINES.open(encoding="utf-8", newline="") as f:
            for row in csv.DictReader(f):
                fid = row.get("source", "")
                desk = id_to_desk.get(fid, "GEO")
                rows.append({
                    "desk": desk,
                    "ts": row.get("ts", "")[:24],
                    "source": fid,
                    "name": (row.get("source_name") or fid)[:60],
                    "title": (row.get("title") or "")[:280],
                    "url": (row.get("url") or "")[:400],
                })

    rows.sort(key=lambda r: r["ts"], reverse=True)
    rows = rows[:2000]

    counts: dict[str, int] = {d: 0 for d, _ in DESK_CATS}
    counts["ALL"] = len(rows)
    for r in rows:
        counts[r["desk"]] = counts.get(r["desk"], 0) + 1

    categories = [{"id": cid, "label": lbl, "count": counts.get(cid, 0)} for cid, lbl in DESK_CATS]
    events = harvest_events()
    feed_n = 0
    if FEEDS.is_file():
        feed_n = len(json.loads(FEEDS.read_text(encoding="utf-8")).get("feeds", []))

    out = {
        "built_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stats": {
            "feeds": feed_n,
            "headlines": len(rows),
            "events": len(events),
        },
        "categories": categories,
        "headlines": rows,
        "events": events,
    }
    CACHE.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print(f"OK desk_index {len(rows)} headlines {len(events)} events -> {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
