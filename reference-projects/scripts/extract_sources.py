#!/usr/bin/env python3
"""Extract named data sources from reference project GitHub repos."""
import json
import re
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data-sources"


def fetch(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "terminal-ref-extract"})
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.read().decode("utf-8", errors="replace")
    except Exception as e:
        return f"__ERROR__: {e}"


def write_md(path: Path, title: str, repo: str, demo: str | None, sections: list[tuple[str, list[str]]], note: str = ""):
    lines = [f"# {title}", "", f"- **Repo:** {repo}"]
    if demo:
        lines.append(f"- **Demo:** {demo}")
    if note:
        lines += ["", note]
    lines.append("")
    for sec_title, items in sections:
        lines.append(f"## {sec_title} ({len(items)})")
        lines.append("")
        for i, item in enumerate(items, 1):
            lines.append(f"{i}. {item}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def parse_name_lines(text: str, cat_pattern=r"^\s*(\w+):\s*\[") -> dict[str, list[str]]:
    cat = "general"
    out: dict[str, list[str]] = {}
    for line in text.splitlines():
        m = re.match(cat_pattern, line)
        if m:
            cat = m.group(1)
        for pat in [r"name:\s*'([^']+)'", r'name:\s*"([^"]+)"', r"title:\s*'([^']+)'"]:
            nm = re.search(pat, line)
            if nm:
                out.setdefault(cat, []).append(nm.group(1))
    return out


def flat_sections(d: dict[str, list[str]], prefix: str = "") -> list[tuple[str, list[str]]]:
    return [(f"{prefix}{k}" if prefix else k, sorted(set(v))) for k, v in sorted(d.items())]


# 02 GlobeOps
def globeops():
    tree = json.loads(fetch("https://api.github.com/repos/Kahooty/GlobeOps/git/trees/main?recursive=1"))
    paths = [n["path"] for n in tree["tree"] if n["path"].startswith("src/config/") and n["path"].endswith((".ts", ".js", ".json"))]
    all_feeds: dict[str, list[str]] = {}
    for p in paths:
        raw = fetch(f"https://raw.githubusercontent.com/Kahooty/GlobeOps/main/{p}")
        if raw.startswith("__ERROR__"):
            continue
        d = parse_name_lines(raw)
        for k, v in d.items():
            all_feeds.setdefault(f"{p} > {k}", []).extend(v)
    # static APIs from README
    apis = [
        "USGS — Earthquakes (5 min)",
        "NASA EONET — Natural events (15 min)",
        "NOAA — Weather alerts (15 min)",
        "GDELT — Geopolitical events (15 min)",
        "CoinGecko — Crypto markets (60 sec)",
        "Polymarket — Prediction markets (5 min)",
        "OpenSky — Aircraft tracking (30 sec)",
    ]
    static = [
        "Military installations (bundled)",
        "Nuclear facilities (bundled)",
        "Pipelines (bundled)",
        "Data centers (bundled)",
        "Maritime trade routes (bundled)",
        "Strategic waterways (bundled)",
    ]
    secs = flat_sections(all_feeds) + [("API live gratuite", apis), ("Dataset statici", static)]
    total = sum(len(s[1]) for s in secs)
    write_md(OUT / "02-globeops.md", "GlobeOps — fonti dati", "https://github.com/Kahooty/GlobeOps", "https://globeops.cloud/", secs,
             f"Totale voci: {total}. File config trovati: {len(paths)}")
    return total


# 03 Energy Monitor — energy variant feeds from WM
def energy_monitor():
    raw = fetch("https://raw.githubusercontent.com/koala73/worldmonitor/main/src/config/variants/energy.ts")
    d = parse_name_lines(raw)
    apis = [
        "OilPriceAPI — WTI, Brent, Natural Gas, Gold",
        "Yahoo Finance — XOM, CVX, COP, SLB, HAL, EOG, OXY, XLE, OIH",
        "EIA — US energy reports (EIA_API_KEY free)",
        "FRED — macro (FRED_API_KEY free)",
        "Finnhub — markets (free tier)",
        "OpenSky — military flights ADS-B",
        "AISStream — naval vessels (free)",
        "ACLED — conflicts (research token)",
        "NASA FIRMS — satellite fires",
        "GDELT — geopolitical events",
        "USGS — earthquakes",
        "Groq — AI briefs (14.400 req/day free)",
        "Upstash Redis — cache (10k/day free)",
        "Wingbits — ADS-B (free tier)",
    ]
    rss = flat_sections(d, "energy.ts > ")
    secs = rss + [("API / servizi (da README + fork WM)", apis)]
    write_md(OUT / "03-energy-monitor.md", "Energy Monitor — fonti dati", "https://github.com/karlwaldman/energymonitor", "https://energy.worldmonitor.app/",
             secs, "Fork di World Monitor. RSS = variant `energy`. API = stesso stack WM.")
    return sum(len(s[1]) for s in secs)


# 05 Fincept — search connectors in repo tree
def fincept():
    tree = json.loads(fetch("https://api.github.com/repos/Fincept-Corporation/FinceptTerminal/git/trees/main?recursive=1"))
    connector_files = [n["path"] for n in tree["tree"] if re.search(r"connector|data.?source|provider", n["path"], re.I) and n["path"].endswith((".py", ".json", ".md", ".ts"))]
    names: list[str] = []
    for p in connector_files[:40]:
        raw = fetch(f"https://raw.githubusercontent.com/Fincept-Corporation/FinceptTerminal/main/{p}")
        if raw.startswith("__ERROR__"):
            continue
        for pat in [r'"name"\s*:\s*"([^"]+)"', r"'name'\s*:\s*'([^']+)'", r"connector[_\s]*=\s*['\"]([^'\"]+)"]:
            names.extend(re.findall(pat, raw))
        names.extend(re.findall(r"class\s+(\w+Connector)", raw))
    # README explicit list
    readme_names = [
        "DBnomics", "Polygon", "Kraken", "Yahoo Finance", "FRED", "IMF", "World Bank", "AkShare",
        "Government APIs", "Alpaca", "IBKR", "Zerodha", "Angel One", "Upstox", "Fyers", "Dhan",
        "Groww", "Kotak", "IIFL", "5paisa", "AliceBlue", "Shoonya", "Motilal", "Tradier", "Saxo",
        "HyperLiquid", "Adanos Market Sentiment (optional)",
    ]
    all_n = sorted(set(readme_names + [n for n in names if len(n) > 2]))
    free = [n for n in all_n if n not in ("Polygon", "Adanos Market Sentiment (optional)")]
    write_md(OUT / "05-fincept-terminal.md", "Fincept Terminal — connettori dati", "https://github.com/Fincept-Corporation/FinceptTerminal", None,
             [("Connettori documentati README", readme_names), ("Tutti i nomi estratti dal codice", all_n)],
             "Tier free AGPL = bring your own data. Fincept Data API a crediti.")
    return len(all_n)


# 06 TyphooN from API_KEYS.md
def typhoon():
    raw = fetch("https://raw.githubusercontent.com/TyphooN-/TyphooN-Terminal/master/docs/API_KEYS.md")
    sections: list[tuple[str, list[str]]] = []
    cur = "general"
    items: list[str] = []
    for line in raw.splitlines():
        if line.startswith("## "):
            if items:
                sections.append((cur, items))
            cur = line[3:].strip()
            items = []
        elif line.startswith("**Used for:**"):
            items.append(line.replace("**Used for:**", "").strip())
    if items:
        sections.append((cur, items))
    # flatten to named sources
    names = [s[0] for s in sections]
    write_md(OUT / "06-typhoon-terminal.md", "TyphooN Terminal — fonti dati", "https://github.com/TyphooN-/TyphooN-Terminal", None,
             [("Fonti / servizi (da API_KEYS.md)", names)])
    return len(names)


# 07 OpenBook
def openbook():
    endpoints = [
        "Binance Futures WebSocket @depth@100ms",
        "Binance Futures WebSocket @aggTrade",
        "Binance Futures REST depth snapshot",
        "Binance Futures REST exchangeInfo",
        "Binance Futures REST mini-ticker",
    ]
    write_md(OUT / "07-openbook.md", "OpenBook — fonti dati", "https://github.com/sqwu/OpenBook", None,
             [("Binance Futures (pubblico, no key)", endpoints)])
    return len(endpoints)


# 09 Blackdesk
def blackdesk():
    tree = json.loads(fetch("https://api.github.com/repos/Blackdesk-ai/blackdesk/git/trees/main?recursive=1"))
    paths = [n["path"] for n in tree["tree"] if "provider" in n["path"].lower() or "adapter" in n["path"].lower() or "market" in n["path"].lower()]
    names = ["Yahoo Finance (primary market-data adapter)"]
    for p in paths[:20]:
        raw = fetch(f"https://raw.githubusercontent.com/Blackdesk-ai/blackdesk/main/{p}")
        names.extend(re.findall(r'"(?:name|provider|id)"\s*:\s*"([^"]+)"', raw))
    write_md(OUT / "09-blackdesk.md", "Blackdesk — fonti dati", "https://github.com/Blackdesk-ai/blackdesk", None,
             [("Market data", sorted(set(names)))])
    return len(set(names))


# 10 mkt — from README table
def mkt():
    sources = [
        "Coinbase Advanced Trade WebSocket — real-time crypto, L2 book (no auth)",
        "Coinbase Exchange REST — historical candles, order-book snapshot (no auth)",
        "Yahoo Finance REST — stocks, macro, options, earnings (no auth)",
        "FRED REST CSV — economic series via FRED: prefix (no auth)",
        "DeFiLlama REST — per-chain TVL (no auth)",
        "Binance Futures REST — funding rate + open interest BTC/ETH/SOL (no auth)",
        "Yahoo Finance RSS — news headlines (no auth)",
        "MarketWatch RSS — news headlines (no auth)",
        "CNBC RSS — news headlines (no auth)",
        "SEC EDGAR Atom RSS — per-ticker filings 8-K, 10-Q, 10-K (no auth)",
        "ntfy.sh — alert push (optional, no signup)",
        "Pushover — alert push (optional, free dev)",
    ]
    macro = ["10Y Treasury", "13W T-Bill", "VIX", "DXY", "Gold", "WTI Crude", "S&P 500", "Bitcoin", "2s10s spread"]
    write_md(OUT / "10-mkt.md", "mkt — fonti dati", "https://github.com/stxkxs/mkt", None,
             [("Provider (da README Data Sources)", sources), ("Macro dashboard (serie fisse)", macro)])
    return len(sources) + len(macro)


# 11 wickra
def wickra():
    items = [
        "Binance live — BTC/USDT, ETH/USDT, SOL/USDT, BNB/USDT, XRP/USDT (demo live.wickra.org)",
        "wickra-exchange — live feeds major crypto venues",
        "wickra-backtest Replay — recorded feeds (file)",
        "Synth — deterministic synthetic feed (offline)",
    ]
    write_md(OUT / "11-wickra-terminal.md", "wickra-terminal — fonti dati", "https://github.com/wickra-lib/wickra-terminal", "https://live.wickra.org/",
             [("Fonti", items)])
    return len(items)


# 12 stocksTUI
def stockstui():
    tree = json.loads(fetch("https://api.github.com/repos/andriy-git/stocksTUI/git/trees/main?recursive=1"))
    fred_series = []
    for n in tree["tree"]:
        if n["path"].endswith(".py"):
            raw = fetch(f"https://raw.githubusercontent.com/andriy-git/stocksTUI/main/{n['path']}")
            fred_series.extend(re.findall(r"FRED[_A-Z]*\s*=\s*['\"]([A-Z0-9_]+)['\"]", raw))
            fred_series.extend(re.findall(r"series_id\s*=\s*['\"]([A-Z0-9_]+)['\"]", raw))
    base = [
        "Yahoo Finance via yfinance — prices, crypto, options, news, history (no key)",
        "FRED API — economic indicators (free API key required)",
    ]
    secs = [("Provider", base)]
    if fred_series:
        secs.append(("Serie FRED nel codice", sorted(set(fred_series))))
    write_md(OUT / "12-stockstui.md", "stocksTUI — fonti dati", "https://github.com/andriy-git/stocksTUI", None, secs)
    return sum(len(s[1]) for s in secs)


# 13 pftui — from crates.io / known doc
def pftui():
    sources = [
        "Yahoo Finance — equities, ETFs, FX, commodities",
        "CoinGecko — crypto",
        "Polymarket — prediction markets",
        "CFTC/Socrata — COT positioning",
        "Alternative.me — Fear & Greed Index",
        "BLS — US economic series",
        "World Bank — global macro",
        "CME/COMEX — warehouse inventory",
        "RSS — market headlines (aggregated feeds)",
    ]
    write_md(OUT / "13-pftui.md", "pftui — fonti dati", "https://crates.io/crates/pftui", "https://pftui.com/",
             [("Provider (da DATA-AGGREGATION.md pubblicata)", sources)],
             "Repo GitHub non accessibile (404). Elenco da documentazione crate.")
    return len(sources)


# 14 OpenTerminalUI — providers from repo
def openterminal():
    tree = json.loads(fetch("https://api.github.com/repos/Hitheshkaranth/OpenTerminalUI/git/trees/main?recursive=1"))
    provider_paths = [n["path"] for n in tree["tree"] if re.search(r"provider|data.?source|router", n["path"], re.I) and n["path"].endswith((".py", ".ts", ".json"))]
    names = []
    for p in provider_paths[:50]:
        raw = fetch(f"https://raw.githubusercontent.com/Hitheshkaranth/OpenTerminalUI/main/{p}")
        names.extend(re.findall(r'(?:provider|name|id)\s*[=:]\s*["\']([^"\']+)["\']', raw, re.I))
    readme = [
        "Yahoo Finance (fallback)", "Google RSS (news fallback)", "NSEPython (India F&O)",
        "OpenRouter :free models", "LM Studio / local Gemma", "FinBERT / lexical sentiment fallback",
    ]
    all_n = sorted(set(readme + [n for n in names if 2 < len(n) < 60]))
    write_md(OUT / "14-openterminalui.md", "OpenTerminalUI — fonti dati", "https://github.com/Hitheshkaranth/OpenTerminalUI", "http://localhost:8000",
             [("Provider documentati", readme), ("Nomi estratti dal codice", all_n)])
    return len(all_n)


# 15 triphopp
def triphopp():
    tree = json.loads(fetch("https://api.github.com/repos/triphopp/bloomberg-terminal/git/trees/main?recursive=1"))
    routers = [n["path"] for n in tree["tree"] if n["path"].startswith("backend/routers/") and n["path"].endswith(".py")]
    modules = sorted({Path(p).stem for p in routers if not Path(p).stem.startswith("__")})
    all_urls: set[str] = set()
    by_router: dict[str, list[str]] = {}
    skip = ("localhost", "schemas.xmlsoap", "wikipedia.org/wiki/", "{", "facebook.com/{", "youtube.com/feeds")
    for p in routers:
        if Path(p).stem.startswith("__"):
            continue
        raw = fetch(f"https://raw.githubusercontent.com/triphopp/bloomberg-terminal/main/{p}")
        urls = []
        for u in re.findall(r"https?://[^\s\"']+", raw):
            u = u.rstrip(".,;)")
            if any(s in u for s in skip):
                continue
            if u not in all_urls:
                urls.append(u)
                all_urls.add(u)
        if urls:
            by_router[Path(p).stem] = sorted(urls)
    flat = sorted(all_urls)
    rss = [u for u in flat if "feed" in u.lower() or "rss" in u.lower() or "reuters" in u or "marketwatch" in u or "cnbc" in u or "investopedia" in u]
    apis = [u for u in flat if u not in rss]
    sections: list[tuple[str, list[str]]] = [
        ("Moduli backend/routers", modules),
        ("URL API / endpoint estratti dal codice", apis),
        ("Feed RSS / news estratti dal codice", rss),
    ]
    for mod, urls in sorted(by_router.items()):
        if len(urls) >= 2:
            sections.append((f"Router {mod}", urls))
    write_md(OUT / "15-triphopp-bloomberg.md", "triphopp Bloomberg — fonti dati", "https://github.com/triphopp/bloomberg-terminal", "http://localhost:3000", sections)
    return len(modules) + len(flat)


# 16 feremabraz
def feremabraz():
    write_md(OUT / "16-feremabraz-bloomberg.md", "feremabraz Bloomberg — fonti dati", "https://github.com/feremabraz/bloomberg-terminal", None,
             [("Dati simulati (unica fonte)", ["Simulated market data — refresh configurabile, no feed live"])])
    return 1


# 17 OpenBB providers
def openbb():
    tree = json.loads(fetch("https://api.github.com/repos/OpenBB-finance/OpenBB/git/trees/develop?recursive=1"))
    providers = sorted({n["path"].split("/")[2] for n in tree["tree"] if n["path"].startswith("openbb_platform/providers/") and n["type"] == "tree"})
    no_key = ["yfinance", "sec", "congress_gov", "government_us", "federal_reserve", "imf", "oecd", "us_eia", "bls", "cftc", "econdb", "tradingeconomics"]
    free_key = ["fred", "fmp", "intrinio", "tiingo", "benzinga", "alpha_vantage", "finra", "finviz", "nasdaq", "wsj"]
    write_md(OUT / "17-openbb.md", "OpenBB — provider dati", "https://github.com/OpenBB-finance/OpenBB", "https://pro.openbb.co",
             [("Tutti i provider (cartelle openbb_platform/providers/)", providers),
              ("Senza API key", [p for p in providers if p in no_key]),
              ("Free tier con API key", [p for p in providers if p in free_key]),
              ("Altri provider nel repo", [p for p in providers if p not in no_key and p not in free_key])])
    return len(providers)


# 18 egui-charts
def egui_charts():
    write_md(OUT / "18-egui-charts.md", "egui-charts — fonti dati", "https://github.com/userFRM/egui-charts", "https://userfrm.github.io/egui-charts/",
             [("Nessun feed bundled", ["DataSource trait — REST / WebSocket / CSV implementato dal host"])])
    return 1


# 04 Oriza
def oriza():
    rss, sites = [], []
    for path in ("backend/app/api/news.py", "backend/app/api/news_sources.py"):
        raw = fetch(f"https://raw.githubusercontent.com/Anknoit/Oriza/main/{path}")
        if raw.startswith("__ERROR__"):
            continue
        m = re.search(r"RSS_SOURCES\s*=\s*\[(.*?)\]", raw, re.S)
        if m:
            rss.extend(re.findall(r'"(https?://[^"]+)"', m.group(1)))
        m = re.search(r"DIRECT_SITES[^=]*=\s*\[(.*?)\]", raw, re.S)
        if m:
            block = re.sub(r"#.*", "", m.group(1))
            sites.extend(re.findall(r'"(https?://[^"]+)"', block))
    readme = [
        "EIA — press release RSS (in codice)",
        "OPEC events calendar (README)",
        "Weather forecasts — demo synthetic in weather.py (non live)",
        "Scrapy + Playwright pipelines (README)",
        "Satellite flaring (planned)",
        "Port congestion (planned)",
        "NDVI crop indices (planned)",
    ]
    secs = [("RSS hardcoded (news.py)", rss), ("Siti scrape diretti (news.py)", sites), ("Da README / stato implementazione", readme)]
    write_md(OUT / "04-oriza.md", "Oriza — fonti dati", "https://github.com/Anknoit/Oriza", "http://localhost:5173", secs)
    return sum(len(s[1]) for s in secs)


# 08 rs_trader
def rs_trader():
    tree = json.loads(fetch("https://api.github.com/repos/pcortellezzi/rs_trader/git/trees/main?recursive=1"))
    paths = [n["path"] for n in tree["tree"] if n["path"].endswith((".rs", ".toml", ".md"))]
    connectors, brokers = [], []
    for p in paths:
        raw = fetch(f"https://raw.githubusercontent.com/pcortellezzi/rs_trader/main/{p}")
        if raw.startswith("__ERROR__"):
            continue
        if re.search(r"connector|binance|csv|parquet", p, re.I):
            connectors.extend(re.findall(r'(?:struct|mod|pub mod)\s+(\w+)', raw))
        brokers.extend(re.findall(r"(?:Rithmic|Hyperliquid|DXFeed|Binance)", raw))
    base = [
        "CSV / Parquet — file locale",
        "Binance connector — live crypto",
        "Simulatori paper trading — offline",
    ]
    ext = sorted(set(brokers)) or ["Rithmic", "Hyperliquid", "DXFeed"]
    write_md(OUT / "08-rs-trader.md", "rs_trader — fonti dati", "https://github.com/pcortellezzi/rs_trader", None,
             [("Connettori implementati / menzionati", base), ("Broker estensibili (trait)", ext)])
    return len(base) + len(ext)


def fix_globeops_and_index():
    raw = fetch("https://raw.githubusercontent.com/Kahooty/GlobeOps/main/src/config/feed-sources.ts")
    items: list[tuple[str, str]] = []
    for line in raw.splitlines():
        m = re.search(r"name: '([^']+)'", line)
        c = re.search(r"category: '([^']+)'", line)
        if m and c:
            items.append((c.group(1), m.group(1)))
    by: dict[str, list[str]] = {}
    for cat, name in items:
        by.setdefault(cat, []).append(name)
    apis = [
        ("ACLED Conflicts", "api-json, key opzionale VITE_ACLED_API_KEY"),
        ("ACLED Protests", "api-json, key opzionale"),
        ("OpenSky Aircraft", "api-json, no key"),
        ("NOAA Weather Alerts", "api-geojson, no key"),
        ("GDELT Events", "api-json, no key"),
        ("CoinGecko Prices", "api-json, no key"),
        ("Polymarket", "api-json, no key"),
        ("ReliefWeb Disasters", "api-json, no key"),
        ("GDACS Alerts", "api-json, no key"),
    ]
    static = [
        "Military Installations", "Nuclear Facilities", "Major Pipelines",
        "Major Data Centers", "Maritime Trade Routes", "Strategic Waterways",
    ]
    sections = [(f"RSS — {cat}", names) for cat, names in sorted(by.items())]
    sections.append(("API live (data-sources.ts)", [f"{n} — {d}" for n, d in apis]))
    sections.append(("Dataset statici", static))
    write_md(
        OUT / "02-globeops.md", "GlobeOps — fonti dati",
        "https://github.com/Kahooty/GlobeOps", "https://globeops.cloud/",
        sections,
        f"Totale RSS: **{len(items)}** feed. Fonte: `src/config/feed-sources.ts`",
    )

    wm_src = OUT.parent / "worldmonitor-feeds-list.md"
    if wm_src.exists():
        text = wm_src.read_text(encoding="utf-8").replace(
            "# World Monitor — elenco completo feed RSS",
            "# World Monitor — fonti dati (feed RSS)",
        )
        (OUT / "01-world-monitor.md").write_text(text, encoding="utf-8")

    files = sorted(OUT.glob("*.md"))
    idx = ["# Indice fonti dati — tutti i progetti", "", "| # | File | Progetto |", "|---|------|----------|"]
    for f in files:
        if f.name == "README.md":
            continue
        title = f.read_text(encoding="utf-8").splitlines()[0].replace("# ", "")
        num = f.name.split("-")[0]
        idx.append(f"| {num} | [{f.name}]({f.name}) | {title} |")
    (OUT / "README.md").write_text("\n".join(idx) + "\n", encoding="utf-8")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    fns = [globeops, energy_monitor, oriza, fincept, typhoon, openbook, rs_trader, blackdesk, mkt, wickra, stockstui, pftui, openterminal, triphopp, feremabraz, openbb, egui_charts]
    for fn in fns:
        if fn is globeops:
            continue  # replaced by fix_globeops
        try:
            n = fn()
            print(f"OK {fn.__name__}: {n} items")
        except Exception as e:
            print(f"FAIL {fn.__name__}: {e}")
    fix_globeops_and_index()
    print("OK fix_globeops_and_index")
    new_script = Path(__file__).parent / "extract_new_sources.py"
    if new_script.exists():
        import subprocess
        import sys
        subprocess.run([sys.executable, str(new_script)], check=False)


if __name__ == "__main__":
    main()
