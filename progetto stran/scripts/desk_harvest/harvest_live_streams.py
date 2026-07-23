#!/usr/bin/env python3
"""Poll live API streams (WM + GlobeOps parity) → cache/live/events.json."""
from __future__ import annotations

import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("DESK_ROOT", HERE.parents[1]))
CACHE = Path(os.environ.get("DESK_CACHE", ROOT / "cache"))
CONFIG = HERE / "live_streams.json"
OUT = CACHE / "live" / "events.json"

from api_keys import apply_keys, has_key  # noqa: E402

apply_keys(CACHE)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


def fetch(url: str, headers: dict | None = None, insecure_ssl: bool = False) -> tuple[int, str]:
    import ssl

    h = {"User-Agent": UA, "Accept": "application/json, application/geo+json, text/csv, application/rss+xml, */*"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, headers=h)
    ctx = ssl.create_default_context()
    if insecure_ssl:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    with urllib.request.urlopen(req, timeout=35, context=ctx) as resp:
        return resp.status, resp.read().decode("utf-8", errors="replace")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_usgs(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    out: list[dict] = []
    for f in data.get("features", [])[:30]:
        p = f.get("properties", {})
        g = f.get("geometry", {}).get("coordinates", [0, 0, 0])
        ts = p.get("time")
        if ts:
            ts = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        else:
            ts = now_iso()
        out.append({
            "type": "quake",
            "ts": ts,
            "title": (p.get("title") or "Earthquake")[:200],
            "severity": f"M{p.get('mag', 0):.1f}",
            "lat": g[1] if len(g) > 1 else 0,
            "lon": g[0] if len(g) > 0 else 0,
            "source": src["name"],
            "stream_id": src["id"],
        })
    return out


def parse_gdacs_rss(body: str, src: dict) -> list[dict]:
    out: list[dict] = []
    for m in re.finditer(r"<item>(.*?)</item>", body, re.S):
        block = m.group(1)
        title = re.search(r"<title>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.S)
        pub = re.search(r"<pubDate>(.*?)</pubDate>", block)
        link = re.search(r"<link>(.*?)</link>", block)
        if not title:
            continue
        t = re.sub(r"<[^>]+>", "", title.group(1)).strip()
        out.append({
            "type": "disaster",
            "ts": (pub.group(1)[:32] if pub else now_iso()),
            "title": t[:200],
            "severity": "GDACS",
            "url": link.group(1).strip() if link else "",
            "source": src["name"],
            "stream_id": src["id"],
        })
        if len(out) >= 20:
            break
    return out


def parse_noaa(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    out: list[dict] = []
    for f in data.get("features", [])[:20]:
        p = f.get("properties", {})
        out.append({
            "type": "weather",
            "ts": (p.get("sent") or now_iso())[:24],
            "title": ((p.get("event") or "") + " — " + (p.get("areaDesc") or ""))[:200],
            "severity": (p.get("severity") or "")[:16],
            "source": src["name"],
            "stream_id": src["id"],
        })
    return out


def parse_eonet(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    out: list[dict] = []
    for ev in data.get("events", [])[:20]:
        title = ev.get("title", "EONET event")
        out.append({
            "type": "natural",
            "ts": now_iso(),
            "title": title[:200],
            "severity": (ev.get("categories", [{}])[0].get("title") or "EONET")[:16],
            "source": src["name"],
            "stream_id": src["id"],
        })
    return out


def parse_opensky(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    n = len(data.get("states") or [])
    label = src.get("name", "OpenSky")
    return [{
        "type": "flight",
        "ts": now_iso(),
        "title": f"{label}: {n} aircraft",
        "severity": "OS",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def parse_gdelt_doc(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    arts = data.get("articles") or []
    out: list[dict] = []
    for a in arts[:20]:
        title = a.get("title") or a.get("url") or "GDELT article"
        out.append({
            "type": "conflict",
            "ts": (a.get("seendate") or now_iso())[:32],
            "title": str(title)[:200],
            "severity": "GDELT",
            "url": a.get("url") or "",
            "source": src["name"],
            "stream_id": src["id"],
        })
    return out or [{
        "type": "meta",
        "ts": now_iso(),
        "title": f"{src['name']}: no articles",
        "severity": "GDELT",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def parse_gdelt_geo(body: str, src: dict) -> list[dict]:
    # geo endpoint often 404 — fall back if DOC-shaped payload arrives
    if '"articles"' in body[:200]:
        return parse_gdelt_doc(body, src)
    data = json.loads(body)
    feats = data.get("features") or []
    out: list[dict] = []
    for f in feats[:25]:
        p = f.get("properties") or {}
        g = (f.get("geometry") or {}).get("coordinates") or [0, 0]
        name = p.get("name") or p.get("html") or p.get("title") or "GDELT geo"
        name = re.sub(r"<[^>]+>", "", str(name)).strip()
        out.append({
            "type": "conflict",
            "ts": now_iso(),
            "title": name[:200],
            "severity": "GDELT",
            "lat": g[1] if len(g) > 1 else 0,
            "lon": g[0] if len(g) > 0 else 0,
            "source": src["name"],
            "stream_id": src["id"],
        })
    if not out:
        out.append({
            "type": "meta",
            "ts": now_iso(),
            "title": f"{src['name']}: no geo points",
            "severity": "GDELT",
            "source": src["name"],
            "stream_id": src["id"],
        })
    return out


def parse_faa_xml(body: str, src: dict) -> list[dict]:
    out: list[dict] = []
    update = re.search(r"<Update_Time>(.*?)</Update_Time>", body)
    for m in re.finditer(r"<Delay_type>(.*?)</Delay_type>.*?<ARPT>(.*?)</ARPT>.*?<Reason>(.*?)</Reason>", body, re.S):
        dtype, arpt, reason = m.group(1), m.group(2), m.group(3)
        out.append({
            "type": "aviation",
            "ts": now_iso(),
            "title": f"FAA {arpt}: {dtype} — {re.sub(r'<[^>]+>', '', reason)[:120]}",
            "severity": "FAA",
            "source": src["name"],
            "stream_id": src["id"],
        })
        if len(out) >= 25:
            break
    if not out:
        # also catch Airport entries with Avg_Delay
        for m in re.finditer(r"<ARPT>(.*?)</ARPT>.*?<Avg_Delay>(.*?)</Avg_Delay>", body, re.S):
            out.append({
                "type": "aviation",
                "ts": now_iso(),
                "title": f"FAA {m.group(1)} avg delay {m.group(2)}",
                "severity": "FAA",
                "source": src["name"],
                "stream_id": src["id"],
            })
            if len(out) >= 20:
                break
    if not out:
        out.append({
            "type": "aviation",
            "ts": now_iso(),
            "title": f"FAA ASWS ok @ {update.group(1) if update else 'now'} — no active delays",
            "severity": "FAA",
            "source": src["name"],
            "stream_id": src["id"],
        })
    return out


def parse_urlhaus_csv(body: str, src: dict) -> list[dict]:
    out: list[dict] = []
    for line in body.splitlines():
        if not line or line.startswith("#"):
            continue
        parts = line.split(",")
        if len(parts) < 3:
            continue
        url = parts[2].strip().strip('"')
        threat = parts[4].strip().strip('"') if len(parts) > 4 else "malware"
        out.append({
            "type": "cyber",
            "ts": now_iso(),
            "title": f"URLhaus {threat}: {url[:140]}",
            "severity": "IOC",
            "source": src["name"],
            "stream_id": src["id"],
        })
        if len(out) >= 20:
            break
    return out or [{
        "type": "cyber",
        "ts": now_iso(),
        "title": "URLhaus: no recent rows",
        "severity": "IOC",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def parse_feodo_json(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    if isinstance(data, dict):
        data = data.get("data") or data.get("ips") or []
    out: list[dict] = []
    for row in (data or [])[:20]:
        if isinstance(row, dict):
            ip = row.get("ip_address") or row.get("ip") or "?"
            malware = row.get("malware") or row.get("status") or "c2"
            out.append({
                "type": "cyber",
                "ts": now_iso(),
                "title": f"Feodo {malware}: {ip}",
                "severity": "C2",
                "source": src["name"],
                "stream_id": src["id"],
            })
    return out or [{
        "type": "cyber",
        "ts": now_iso(),
        "title": "Feodo: empty",
        "severity": "C2",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def parse_yahoo_chart(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    res = (data.get("chart") or {}).get("result") or []
    if not res:
        return [{
            "type": "market",
            "ts": now_iso(),
            "title": f"{src['name']}: no chart data",
            "severity": "Y",
            "source": src["name"],
            "stream_id": src["id"],
        }]
    meta = res[0].get("meta") or {}
    sym = meta.get("symbol") or src["id"]
    price = meta.get("regularMarketPrice") or meta.get("previousClose") or 0
    prev = meta.get("chartPreviousClose") or meta.get("previousClose") or price
    chg = 0.0
    try:
        chg = 100.0 * (float(price) - float(prev)) / float(prev) if prev else 0.0
    except Exception:
        chg = 0.0
    return [{
        "type": "market",
        "ts": now_iso(),
        "title": f"{sym} {float(price):.2f} ({chg:+.2f}%)",
        "severity": "MKT",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def parse_bis_csv(body: str, src: dict) -> list[dict]:
    lines = [ln for ln in body.splitlines() if ln and not ln.startswith("FREQ")]
    # keep last few unique REF_AREA snapshot lines
    out: list[dict] = []
    seen: set[str] = set()
    for ln in reversed(lines):
        parts = ln.split(",")
        if len(parts) < 8:
            continue
        area = parts[1]
        if area in seen:
            continue
        seen.add(area)
        val = parts[-1]
        out.append({
            "type": "macro",
            "ts": now_iso(),
            "title": f"BIS policy rate {area}: {val}",
            "severity": "BIS",
            "source": src["name"],
            "stream_id": src["id"],
        })
        if len(out) >= 12:
            break
    return out or [{
        "type": "macro",
        "ts": now_iso(),
        "title": "BIS CB policy rates feed ok",
        "severity": "BIS",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def parse_celestrak(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    if not isinstance(data, list):
        data = []
    n = len(data)
    sample = data[:8]
    out = [{
        "type": "space",
        "ts": now_iso(),
        "title": f"{src['name']}: {n} objects",
        "severity": "TLE",
        "source": src["name"],
        "stream_id": src["id"],
    }]
    for obj in sample:
        name = obj.get("OBJECT_NAME") or obj.get("object_name") or "?"
        out.append({
            "type": "space",
            "ts": now_iso(),
            "title": f"TLE {name}",
            "severity": "ORB",
            "source": src["name"],
            "stream_id": src["id"],
        })
    return out


def parse_disease_sh(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    cases = data.get("cases") or 0
    deaths = data.get("deaths") or 0
    updated = data.get("updated")
    ts = now_iso()
    if updated:
        try:
            ts = datetime.fromtimestamp(updated / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        except Exception:
            pass
    return [{
        "type": "health",
        "ts": ts,
        "title": f"Global cases={cases:,} deaths={deaths:,}",
        "severity": "HEALTH",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def parse_atom(body: str, src: dict) -> list[dict]:
    out: list[dict] = []
    for m in re.finditer(r"<entry>(.*?)</entry>", body, re.S):
        block = m.group(1)
        title = re.search(r"<title[^>]*>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</title>", block, re.S)
        updated = re.search(r"<updated>(.*?)</updated>", block)
        if not title:
            continue
        t = re.sub(r"<[^>]+>", "", title.group(1)).strip()
        out.append({
            "type": "advisory",
            "ts": (updated.group(1)[:32] if updated else now_iso()),
            "title": t[:200],
            "severity": "ADV",
            "source": src["name"],
            "stream_id": src["id"],
        })
        if len(out) >= 15:
            break
    return out


def parse_gdelt_summary(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    timeline = data.get("timeline") or data.get("timelinevolinfo") or []
    if isinstance(timeline, dict):
        timeline = timeline.get("data") or []
    out: list[dict] = []
    for pt in timeline[-5:]:
        if isinstance(pt, dict):
            val = pt.get("value") or pt.get("count") or 0
            date = pt.get("date") or now_iso()
            out.append({
                "type": "intel",
                "ts": now_iso(),
                "title": f"GDELT conflict volume {val} @ {date}",
                "severity": "GDELT",
                "source": src["name"],
                "stream_id": src["id"],
            })
    if not out:
        out.append({
            "type": "intel",
            "ts": now_iso(),
            "title": "GDELT conflict timeline updated",
            "severity": "GDELT",
            "source": src["name"],
            "stream_id": src["id"],
        })
    return out


def parse_defillama_tvl(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    if not isinstance(data, list):
        return []
    total = sum(float(c.get("tvl") or 0) for c in data)
    top = sorted(data, key=lambda c: float(c.get("tvl") or 0), reverse=True)[:3]
    parts = ", ".join(f"{c.get('name', '?')} ${float(c.get('tvl') or 0)/1e9:.1f}B" for c in top)
    return [{
        "type": "market",
        "ts": now_iso(),
        "title": f"DeFi TVL ${total/1e9:.1f}B  top: {parts}",
        "severity": "DEFI",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def parse_defillama_fees(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    protocols = data.get("protocols") or []
    top = sorted(protocols, key=lambda p: float(p.get("total24h") or 0), reverse=True)[:5]
    out: list[dict] = []
    for p in top:
        fee = float(p.get("total24h") or 0)
        out.append({
            "type": "market",
            "ts": now_iso(),
            "title": f"{p.get('displayName') or p.get('name', '?')} fees 24h ${fee/1e6:.1f}M",
            "severity": "DEFI",
            "source": src["name"],
            "stream_id": src["id"],
        })
    return out or [{
        "type": "market",
        "ts": now_iso(),
        "title": "DeFiLlama fees overview updated",
        "severity": "DEFI",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def parse_crypto_fng(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    row = (data.get("data") or [{}])[0]
    val = row.get("value", "?")
    cls = row.get("value_classification", "")
    return [{
        "type": "market",
        "ts": now_iso(),
        "title": f"Crypto Fear & Greed {val} ({cls})",
        "severity": "FNG",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def parse_cnn_fng(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    score = data.get("fear_and_greed", {}).get("score")
    rating = data.get("fear_and_greed", {}).get("rating", "")
    if score is None:
        score = data.get("score")
    return [{
        "type": "market",
        "ts": now_iso(),
        "title": f"Equity Fear & Greed {score} ({rating})",
        "severity": "FNG",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def parse_binance_premium(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    sym = data.get("symbol", "?")
    rate = float(data.get("lastFundingRate") or 0) * 100
    mark = float(data.get("markPrice") or 0)
    return [{
        "type": "market",
        "ts": now_iso(),
        "title": f"{sym} mark ${mark:,.0f}  funding {rate:+.4f}%",
        "severity": "BIN",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def parse_binance_oi(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    sym = data.get("symbol", "?")
    oi = float(data.get("openInterest") or 0)
    return [{
        "type": "market",
        "ts": now_iso(),
        "title": f"{sym} open interest {oi:,.0f}",
        "severity": "BIN",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def parse_worldbank_cpi(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    rows = (data[1] if isinstance(data, list) and len(data) > 1 else []) or []
    if not rows:
        return []
    row = rows[0]
    val = row.get("value")
    yr = row.get("date", "")
    return [{
        "type": "macro",
        "ts": now_iso(),
        "title": f"US CPI inflation {val}% ({yr})",
        "severity": "WB",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def parse_imf_inflation(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    values = data.get("values") or data.get("USA") or {}
    if isinstance(values, dict):
        items = sorted((int(k), v) for k, v in values.items() if str(k).isdigit())
        if items:
            yr, val = items[-1]
            return [{
                "type": "macro",
                "ts": now_iso(),
                "title": f"IMF US inflation forecast {val}% ({yr})",
                "severity": "IMF",
                "source": src["name"],
                "stream_id": src["id"],
            }]
    return [{
        "type": "macro",
        "ts": now_iso(),
        "title": "IMF inflation data updated",
        "severity": "IMF",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def parse_openmeteo(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    cur = data.get("current") or {}
    t = cur.get("temperature_2m")
    w = cur.get("wind_speed_10m")
    p = cur.get("precipitation")
    label = src["name"].replace("Open-Meteo ", "")
    return [{
        "type": "weather",
        "ts": now_iso(),
        "title": f"{label}: {t}°C wind {w}m/s precip {p}mm",
        "severity": "WX",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def parse_mempool_fees(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    return [{
        "type": "market",
        "ts": now_iso(),
        "title": (
            f"BTC fees sat/vB fastest={data.get('fastestFee')} "
            f"hour={data.get('hourFee')} economy={data.get('economyFee')}"
        ),
        "severity": "BTC",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def parse_coingecko_global(body: str, src: dict) -> list[dict]:
    data = json.loads(body).get("data", {})
    mc = data.get("total_market_cap", {}).get("usd", 0)
    ch = data.get("market_cap_change_percentage_24h_usd", 0)
    return [{
        "type": "market",
        "ts": now_iso(),
        "title": f"Crypto mcap ${mc/1e12:.2f}T  24h {ch:+.1f}%",
        "severity": "CG",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def parse_coingecko_markets(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    out: list[dict] = []
    if isinstance(data, list):
        for c in data[:8]:
            sym = (c.get("symbol") or "").upper()
            ch = c.get("price_change_percentage_24h") or 0
            out.append({
                "type": "market",
                "ts": now_iso(),
                "title": f"{sym} ${c.get('current_price', 0):,.2f}  24h {ch:+.1f}%",
                "severity": "CG",
                "source": src["name"],
                "stream_id": src["id"],
            })
    return out


def parse_polymarket(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    out: list[dict] = []
    if isinstance(data, list):
        for m in data[:10]:
            q = (m.get("question") or "")[:160]
            vol = m.get("volume") or m.get("volumeNum") or 0
            try:
                vol = float(vol)
            except (TypeError, ValueError):
                vol = 0.0
            out.append({
                "type": "market",
                "ts": now_iso(),
                "title": f"{q}  vol ${vol/1e6:.1f}M" if vol else q,
                "severity": "POLY",
                "source": src["name"],
                "stream_id": src["id"],
            })
    return out


def parse_reliefweb(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    out: list[dict] = []
    for row in data.get("data", [])[:12]:
        f = row.get("fields", {})
        out.append({
            "type": "humanitarian",
            "ts": now_iso(),
            "title": (f.get("name") or "ReliefWeb disaster")[:200],
            "severity": (f.get("status") or "RW")[:16],
            "source": src["name"],
            "stream_id": src["id"],
        })
    return out


def parse_gdacs_api(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    out: list[dict] = []
    features = data if isinstance(data, list) else data.get("features") or data.get("events") or []
    for ev in features[:15]:
        if isinstance(ev, dict):
            title = ev.get("title") or ev.get("name") or ev.get("eventname") or "GDACS alert"
            out.append({
                "type": "disaster",
                "ts": now_iso(),
                "title": str(title)[:200],
                "severity": "GDACS",
                "source": src["name"],
                "stream_id": src["id"],
            })
    return out


def parse_cloudflare(body: str, src: dict) -> list[dict]:
    data = json.loads(body)
    out: list[dict] = []
    result = data.get("result") or {}
    for item in (result.get("traffic_anomalies") or result.get("items") or [])[:10]:
        title = item.get("title") or item.get("description") or item.get("name") or "Traffic anomaly"
        out.append({
            "type": "outage",
            "ts": now_iso(),
            "title": str(title)[:200],
            "severity": "CF",
            "source": src["name"],
            "stream_id": src["id"],
        })
    if not out and data.get("success"):
        out.append({
            "type": "meta",
            "ts": now_iso(),
            "title": "Cloudflare Radar: no active traffic anomalies",
            "severity": "CF",
            "source": src["name"],
            "stream_id": src["id"],
        })
    return out


PARSERS = {
    "usgs-quakes": parse_usgs,
    "usgs-quakes-25": parse_usgs,
    "usgs-significant": parse_usgs,
    "gdacs-rss": parse_gdacs_rss,
    "gdacs-api": parse_gdacs_api,
    "noaa-alerts": parse_noaa,
    "nasa-eonet": parse_eonet,
    "nasa-firms": parse_eonet,
    "gdelt-summary": parse_gdelt_doc,
    "gdelt-geo-conflict": parse_gdelt_doc,
    "gdelt-geo-protest": parse_gdelt_doc,
    "opensky-eu": parse_opensky,
    "opensky-us": parse_opensky,
    "opensky-mena": parse_opensky,
    "opensky-asia": parse_opensky,
    "faa-asws": parse_faa_xml,
    "coingecko-global": parse_coingecko_global,
    "coingecko-markets": parse_coingecko_markets,
    "polymarket": parse_polymarket,
    "reliefweb-rss": parse_gdacs_rss,
    "cloudflare-outages": parse_gdacs_rss,
    "cloudflare-status": parse_gdacs_rss,
    "aws-status": parse_gdacs_rss,
    "azure-status": parse_gdacs_rss,
    "ransomware-live": parse_gdacs_rss,
    "yahoo-fin-news": parse_gdacs_rss,
    "who-news": parse_gdacs_rss,
    "ecdc-news": parse_gdacs_rss,
    "cdc-travel": parse_gdacs_rss,
    "uk-fcdo-travel": parse_atom,
    "urlhaus-recent": parse_urlhaus_csv,
    "feodo-tracker": parse_feodo_json,
    "feodo-recommended": parse_feodo_json,
    "defillama-tvl": parse_defillama_tvl,
    "defillama-fees": parse_defillama_fees,
    "crypto-fng": parse_crypto_fng,
    "cnn-fear-greed": parse_cnn_fng,
    "binance-funding-btc": parse_binance_premium,
    "binance-funding-eth": parse_binance_premium,
    "binance-oi-btc": parse_binance_oi,
    "binance-oi-eth": parse_binance_oi,
    "worldbank-cpi-us": parse_worldbank_cpi,
    "imf-inflation-us": parse_imf_inflation,
    "openmeteo-london": parse_openmeteo,
    "openmeteo-houston": parse_openmeteo,
    "mempool-fees": parse_mempool_fees,
    "disease-sh-global": parse_disease_sh,
    "celestrak-stations": parse_celestrak,
    "celestrak-active": parse_celestrak,
    "bis-policy-rates": parse_bis_csv,
    "yahoo-vix": parse_yahoo_chart,
    "yahoo-sp500": parse_yahoo_chart,
    "yahoo-nasdaq": parse_yahoo_chart,
    "yahoo-dji": parse_yahoo_chart,
    "yahoo-ftse": parse_yahoo_chart,
    "yahoo-dax": parse_yahoo_chart,
    "yahoo-cac": parse_yahoo_chart,
    "yahoo-nikkei": parse_yahoo_chart,
    "yahoo-hsi": parse_yahoo_chart,
    "yahoo-sse": parse_yahoo_chart,
    "yahoo-kospi": parse_yahoo_chart,
    "yahoo-bse": parse_yahoo_chart,
    "yahoo-asx": parse_yahoo_chart,
    "yahoo-bvsp": parse_yahoo_chart,
    "yahoo-brent": parse_yahoo_chart,
    "yahoo-wti": parse_yahoo_chart,
}


def resolve_parser(src: dict):
    sid = src["id"]
    if sid in PARSERS:
        return PARSERS[sid]
    t = (src.get("type") or "").lower()
    if t in ("rss",):
        return parse_gdacs_rss
    if t in ("atom",):
        return parse_atom
    if t in ("geojson",):
        return parse_usgs
    if t in ("xml",):
        return parse_faa_xml
    if t in ("csv",) and "urlhaus" in sid:
        return parse_urlhaus_csv
    if t in ("csv",) and "bis" in sid:
        return parse_bis_csv
    if t in ("json",):
        return parse_json_heartbeat
    return None


def parse_json_heartbeat(body: str, src: dict) -> list[dict]:
    """Fallback for registry / opaque JSON streams (opensanctions, GIE, coinbase, …)."""
    try:
        data = json.loads(body)
    except Exception:
        return [{
            "type": "meta",
            "ts": now_iso(),
            "title": f"{src['name']}: non-json body",
            "severity": "OK",
            "source": src["name"],
            "stream_id": src["id"],
        }]
    n = 0
    if isinstance(data, list):
        n = len(data)
    elif isinstance(data, dict):
        for k in ("data", "datasets", "results", "features", "items"):
            if isinstance(data.get(k), list):
                n = len(data[k])
                break
        if not n:
            n = len(data)
    return [{
        "type": "meta",
        "ts": now_iso(),
        "title": f"{src['name']}: live ok (n={n})",
        "severity": "OK",
        "source": src["name"],
        "stream_id": src["id"],
    }]


def poll_stream(src: dict) -> tuple[str, list[dict], str]:
    sid = src["id"]
    env_key = src.get("env_key")
    if env_key and not has_key(env_key, CACHE):
        return sid, [], "skip:no_key"
    if (src.get("type") or "").lower() == "ws":
        return sid, [], "skip:websocket"

    url = src["url"]
    if sid == "acled-conflicts" and env_key:
        key = os.environ[env_key].strip()
        q = urllib.parse.urlencode({"key": key, "limit": 15, "event_type": "Battles"})
        url = f"{url}?{q}"
    if sid == "ucdp-ged-optional" and env_key:
        tok = os.environ[env_key].strip()
        q = urllib.parse.urlencode({"pagesize": 20, "page": 0})
        url = f"{url}?{q}"
        src = dict(src)
        hdrs = dict(src.get("headers") or {})
        hdrs["Authorization"] = f"Bearer {tok}"
        src["headers"] = hdrs

    try:
        status, body = fetch(
            url,
            headers=src.get("headers"),
            insecure_ssl=bool(src.get("insecure_ssl")),
        )
        parser = resolve_parser(src)
        if not parser:
            return sid, [], f"no_parser:{status}"
        events = parser(body, src)
        return sid, events, "ok"
    except Exception as e:
        return sid, [{"type": "meta", "ts": now_iso(), "title": f"{src['name']} error: {e}", "severity": "ERR", "source": src["name"], "stream_id": sid}], "fail"


def main() -> int:
    cfg = json.loads(CONFIG.read_text(encoding="utf-8"))
    streams = cfg.get("streams", [])
    all_events: list[dict] = []
    stats: dict[str, str] = {}

    for src in streams:
        sid, events, st = poll_stream(src)
        stats[sid] = st
        all_events.extend(events)

    out = {
        "built_at": now_iso(),
        "stream_count": len(streams),
        "event_count": len(all_events),
        "stats": stats,
        "events": all_events,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    ok = sum(1 for v in stats.values() if v == "ok")
    skip = sum(1 for v in stats.values() if v.startswith("skip"))
    fail = sum(1 for v in stats.values() if v == "fail" or v.startswith("no_parser"))
    print(f"OK live streams ok={ok} skip={skip} fail={fail} total={len(streams)} events={len(all_events)} -> {OUT}")
    for k, v in sorted(stats.items()):
        if v != "ok":
            print(f"  {k}: {v}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
