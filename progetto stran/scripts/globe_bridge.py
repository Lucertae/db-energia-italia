#!/usr/bin/env python3
"""Local bridge: USGS + desk live events → GeoJSON for OPS DESK globe."""
from __future__ import annotations

import json
import os
import re
import threading
import time
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get("DESK_ROOT", HERE.parents[1]))
CACHE = Path(os.environ.get("DESK_CACHE", ROOT / "cache"))
PORT = int(os.environ.get("GLOBE_BRIDGE_PORT", "8787"))
UA = "ops-desk-globe-bridge/1.0"

USGS = {
    "day": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_day.geojson",
    "week": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_week.geojson",
    "month": "https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/all_month.geojson",
}

# map stream_id / type → WM-style layer key
LAYER_RULES = [
    (re.compile(r"usgs|quake", re.I), "quakes"),
    (re.compile(r"firms|fire|wildfire|eonet", re.I), "fires"),
    (re.compile(r"opensky|flight|aviation|faa", re.I), "flights"),
    (re.compile(r"ais|ship|tanker|maritime|portwatch", re.I), "ais"),
    (re.compile(r"acled|ucdp|conflict|battle|gdelt|protest|unrest|oref", re.I), "conflicts"),
    (re.compile(r"cyber|urlhaus|feodo|ransomware", re.I), "cyber"),
    (re.compile(r"gdacs|flood|storm|volcano|natural", re.I), "natural"),
    (re.compile(r"climate|co2|seaice|carbon", re.I), "climate"),
]

_cache: dict[str, tuple[float, dict]] = {}
_lock = threading.Lock()


def fetch_json(url: str, timeout: int = 40) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def layer_of(ev: dict) -> str:
    blob = " ".join(
        str(ev.get(k, ""))
        for k in ("type", "stream_id", "source", "title", "severity")
    )
    for rx, name in LAYER_RULES:
        if rx.search(blob):
            return name
    return "other"


def feature_from_live(ev: dict, idx: int) -> dict | None:
    lat = ev.get("lat")
    lon = ev.get("lon") or ev.get("lng")
    if lat is None or lon is None:
        return None
    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        return None
    if not (-90 <= lat_f <= 90 and -180 <= lon_f <= 180):
        return None
    layer = layer_of(ev)
    # Fake magnitude for sizing by layer
    mag = 3.0
    if layer == "quakes":
        m = re.search(r"M\s*([0-9.]+)", str(ev.get("severity") or ev.get("title") or ""))
        mag = float(m.group(1)) if m else 4.0
    elif layer == "fires":
        mag = 3.5
    elif layer == "flights":
        mag = 2.2
    elif layer == "ais":
        mag = 2.5
    elif layer == "conflicts":
        mag = 4.5
    elif layer == "cyber":
        mag = 2.8
    ts = ev.get("ts") or ""
    # ms epoch if ISO
    t_ms = int(time.time() * 1000)
    if isinstance(ts, (int, float)):
        t_ms = int(ts if ts > 1e12 else ts * 1000)
    elif isinstance(ts, str) and len(ts) >= 10:
        try:
            from datetime import datetime
            t_ms = int(datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() * 1000)
        except Exception:
            pass
    return {
        "type": "Feature",
        "id": ev.get("stream_id", "live") + f"-{idx}",
        "geometry": {"type": "Point", "coordinates": [lon_f, lat_f, 0]},
        "properties": {
            "mag": mag,
            "place": ev.get("title") or ev.get("headline") or layer,
            "time": t_ms,
            "tsunami": 0,
            "felt": 0,
            "url": "",
            "type": layer,
            "layer": layer,
            "source": ev.get("source") or ev.get("stream_id") or "desk",
        },
    }


def usgs_features(time_range: str) -> list[dict]:
    url = USGS.get(time_range, USGS["day"])
    key = f"usgs:{time_range}"
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < 60:
            return hit[1]
    try:
        doc = fetch_json(url)
        feats = doc.get("features") or []
        for f in feats:
            props = f.setdefault("properties", {})
            props["layer"] = "quakes"
            props["type"] = props.get("type") or "earthquake"
        with _lock:
            _cache[key] = (now, feats)
        return feats
    except Exception as e:
        print(f"usgs fail: {e}")
        if hit:
            return hit[1]
        return []


def live_features() -> list[dict]:
    path = CACHE / "live" / "events.json"
    key = "live"
    now = time.time()
    with _lock:
        hit = _cache.get(key)
        if hit and now - hit[0] < 20:
            return hit[1]
    if not path.is_file():
        return []
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
        events = doc.get("events") or []
        out = []
        for i, ev in enumerate(events):
            if not isinstance(ev, dict):
                continue
            # skip plain quakes already covered by USGS enrich — keep all with coords
            f = feature_from_live(ev, i)
            if f:
                out.append(f)
        with _lock:
            _cache[key] = (now, out)
        return out
    except Exception as e:
        print(f"live fail: {e}")
        return hit[1] if hit else []


def build_geojson(time_range: str, layers: set[str] | None) -> dict:
    feats: list[dict] = []
    if not layers or "quakes" in layers:
        feats.extend(usgs_features(time_range))
    for f in live_features():
        layer = (f.get("properties") or {}).get("layer", "other")
        if layers and layer not in layers:
            continue
        feats.append(f)
    return {
        "type": "FeatureCollection",
        "metadata": {
            "generated": int(time.time()),
            "count": len(feats),
            "source": "ops-desk-globe-bridge",
            "timeRange": time_range,
        },
        "features": feats,
    }


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt: str, *args) -> None:
        print(f"[globe-bridge] {self.address_string()} {fmt % args}")

    def _cors(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")

    def do_OPTIONS(self) -> None:  # noqa: N802
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        u = urlparse(self.path)
        if u.path in ("/", "/health"):
            body = json.dumps({"ok": True, "service": "globe-bridge", "port": PORT}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if u.path in ("/api/points", "/api/geojson"):
            qs = parse_qs(u.query)
            tr = (qs.get("range") or qs.get("timeRange") or ["day"])[0]
            if tr not in USGS:
                tr = "day"
            layer_q = (qs.get("layers") or [""])[0]
            layers = {x.strip() for x in layer_q.split(",") if x.strip()} or None
            doc = build_geojson(tr, layers)
            body = json.dumps(doc).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if u.path == "/api/layers":
            body = json.dumps(
                {
                    "layers": [
                        {"id": "quakes", "label": "Earthquakes", "color": "#f97316"},
                        {"id": "fires", "label": "Fires", "color": "#ef4444"},
                        {"id": "flights", "label": "Aviation", "color": "#22d3ee"},
                        {"id": "ais", "label": "Ships AIS", "color": "#3b82f6"},
                        {"id": "conflicts", "label": "Conflicts", "color": "#dc2626"},
                        {"id": "natural", "label": "Natural", "color": "#a78bfa"},
                        {"id": "cyber", "label": "Cyber", "color": "#84cc16"},
                        {"id": "climate", "label": "Climate", "color": "#14b8a6"},
                        {"id": "other", "label": "Other", "color": "#94a3b8"},
                    ]
                }
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        self.send_response(404)
        self.end_headers()


def main() -> int:
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    print(f"globe-bridge on http://127.0.0.1:{PORT}")
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
