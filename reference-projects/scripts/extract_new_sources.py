#!/usr/bin/env python3
"""Extract data sources for projects 19-30."""
import json
import re
import urllib.request
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "data-sources"


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "terminal-ref-extract"})
    with urllib.request.urlopen(req, timeout=45) as r:
        return r.read().decode("utf-8", errors="replace")


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


def obsyd():
    tree = json.loads(fetch("https://api.github.com/repos/jo20ow/Obsyd/git/trees/main?recursive=1"))
    paths = [n["path"] for n in tree["tree"] if re.search(r"source|provider|feed|api|ingest", n["path"], re.I) and n["path"].endswith((".ts", ".py", ".md", ".json"))]
    urls: set[str] = set()
    names: list[str] = []
    for p in paths[:30]:
        raw = fetch(f"https://raw.githubusercontent.com/jo20ow/Obsyd/main/{p}")
        if raw.startswith("__ERROR__"):
            continue
        names.extend(re.findall(r'name:\s*["\']([^"\']+)["\']', raw))
        for u in re.findall(r"https?://[^\s\"']+", raw):
            u = u.rstrip(".,;)")
            if "github" not in u and "localhost" not in u:
                urls.add(u)
    readme = [
        "ENTSO-E Transparency Platform — day-ahead prices, load, generation mix, cross-border flows (API token free)",
        "Fraunhofer Energy-Charts — generation mix, residual load, forecasts DE/FR/NL",
        "GIE AGSI/ALSI — EU gas storage, LNG, flows (public)",
        "Anomaly radar — rule-based thresholds in open code (no ML black-box)",
    ]
    secs = [("Da README / documentazione", readme)]
    if names:
        secs.append(("Nomi estratti dal codice", sorted(set(names))[:80]))
    if urls:
        secs.append(("URL estratti dal codice", sorted(urls)[:40]))
    write_md(OUT / "19-obsyd.md", "OBSYD — fonti dati", "https://github.com/jo20ow/Obsyd", "https://obsyd.dev/", secs,
             "Desk energia EU open source (AGPL-3.0). Zone: DE-LU, FR, NL.")
    return sum(len(s[1]) for s in secs)


def gridstatus():
    raw = fetch("https://raw.githubusercontent.com/gridstatus/gridstatus/main/gridstatus/__init__.py")
    isos = re.findall(r"from gridstatus\.(\w+) import", raw)
    if not isos:
        isos = ["CAISO", "ERCOT", "PJM", "MISO", "SPP", "ISONE", "NYISO", "IESO", "AESO"]
    apis = [
        "CAISO — prices, load, renewables, outages",
        "ERCOT — SPP prices, load, wind/solar, congestion",
        "PJM — LMP, load, generation fuel mix",
        "MISO — day-ahead/real-time LMP, load",
        "SPP — prices, load, renewables",
        "ISONE — prices, load, fuel mix",
        "NYISO — prices, load, interface flows",
        "IESO — Ontario market data",
        "AESO — Alberta market data",
        "EIA — fuel mix, generation (US aggregate)",
    ]
    write_md(OUT / "20-gridstatus.md", "gridstatus — fonti dati", "https://github.com/gridstatus/gridstatus", "https://www.gridstatus.io/",
             [("ISO / operator supportati", apis), ("Moduli Python nel package", sorted(set(isos)) if isos else apis)],
             "Libreria Python. Molti endpoint pubblici senza key; alcuni richiedono credenziali (vedi .env.template).")
    return len(apis)


def electricitymaps():
    tree = json.loads(fetch("https://api.github.com/repos/electricitymaps/electricitymaps-contrib/git/trees/master?recursive=1"))
    parsers = sorted({n["path"].split("/")[1] for n in tree["tree"] if n["path"].startswith("parsers/") and n["type"] == "tree"})
    write_md(OUT / "21-electricitymaps.md", "Electricity Maps — fonti dati", "https://github.com/electricitymaps/electricitymaps-contrib", "https://app.electricitymaps.com/",
             [("Parser per paese/regione (cartelle parsers/)", parsers[:120]),
              ("Tipi dato standardizzati", ["production — mix generazione", "exchange — flussi cross-border", "price — day-ahead / spot dove disponibile", "carbon intensity — gCO2eq/kWh (flow-tracing su app)"])],
             f"Totale regioni parser: **{len(parsers)}**. Dati da TSO/governi ufficiali; API commerciale separata.")
    return len(parsers)


def herbie():
    models = [
        "HRRR — NOAA high-res US (sub-hourly)",
        "RAP — NOAA rapid refresh",
        "GFS — NOAA global forecast",
        "NAM — NOAA North America",
        "ECMWF IFS/HRES — open data tier",
        "ICON — DWD Germany",
        "GEM — Canada",
        "NBM — National Blend of Models",
        "RRFS — Rapid Refresh Forecast System",
    ]
    hosts = [
        "NOMADS — NOAA Operational Model Archive",
        "NODD AWS — Amazon Open Data",
        "NODD GCP — Google Cloud",
        "NODD Azure — Microsoft Azure",
        "ECMWF open data portal",
        "University of Utah Pando Archive",
    ]
    write_md(OUT / "22-herbie.md", "Herbie — fonti dati", "https://github.com/blaylockbk/Herbie", None,
             [("Modelli NWP supportati (subset)", models), ("Host / mirror download", hosts)],
             "Libreria Python per download GRIB/NetCDF. Nessuna API key per NOMADS/NODD pubblici.")
    return len(models) + len(hosts)


def gfw():
    apis = [
        "4Wings API — gridded AIS fishing effort, vessel presence, SAR detections 2017→~5d ago",
        "Vessels API — identity, registry, AIS metadata",
        "Events API — fishing, encounters, port visits, loitering, gaps",
        "Insights API — vessel history analytics",
    ]
    write_md(OUT / "23-global-fishing-watch.md", "Global Fishing Watch — fonti dati", "https://github.com/globalfishingwatch/gfw-api-python-client", "https://globalfishingwatch.org/map/",
             [("API GFW v3 (token gratuito con registrazione)", apis),
              ("Dataset sottostanti", ["AIS — vessel positions global", "Vessel registry — public registries merged", "SAR — satellite radar detections", "EEZ / MPA boundaries — marine governance"])],
             "Map UI su globalfishingwatch.org; client Python per ingest programmatico.")
    return len(apis) + 4


def tar1090():
    write_md(OUT / "24-tar1090.md", "tar1090 — fonti dati", "https://github.com/wiedehopf/tar1090", "https://adsb.lol/",
             [("Input (decoder locale)", ["readsb — ADS-B decoder (preferred)", "dump1090-fa — FlightAware fork", "dump1090-mutability — limited aircraft details"]),
              ("Feed aggregati pubblici (siti che usano tar1090+readsb)", ["adsb.lol", "globe.adsbexchange.com", "globe.airplanes.live", "globe.adsb.fi"]),
              ("Dati visualizzati", ["ICAO hex, callsign, altitude, speed, heading", "Track history (configurable interval)", "MLAT / TIS-B quando disponibile"])],
             "UI web per ADS-B locale o rete aggregata. Nessuna API key per decoder proprio.")
    return 10


def opensanctions():
    tree = json.loads(fetch("https://api.github.com/repos/opensanctions/opensanctions/git/trees/main?recursive=1"))
    datasets = sorted({n["path"].split("/")[1] for n in tree["tree"] if n["path"].startswith("datasets/") and n["type"] == "tree"})
    sources = [
        "OFAC SDN — US Treasury sanctions",
        "EU Consolidated List — European sanctions",
        "UN Security Council — consolidated sanctions",
        "UK HMT / OFSI — UK sanctions",
        "PEP databases — politically exposed persons (multi-country)",
        "OpenCorporates enrichment — via nomenklatura (optional)",
        "yente API — entity matching / fuzzy search",
    ]
    write_md(OUT / "25-opensanctions.md", "OpenSanctions — fonti dati", "https://github.com/opensanctions/opensanctions", "https://www.opensanctions.org/",
             [("Dataset crawler (cartelle datasets/)", datasets[:80]),
              ("Fonti aggregate principali", sources)],
             f"Totale dataset crawler: **{len(datasets)}**. Export: FollowTheMoney JSON, CSV, bulk download.")
    return len(datasets) + len(sources)


def spiderfoot():
    tree = json.loads(fetch("https://api.github.com/repos/smicallef/spiderfoot/git/trees/master?recursive=1"))
    modules = sorted({
        n["path"].split("/")[-1].replace(".py", "")
        for n in tree["tree"]
        if n["path"].startswith("modules/") and n["path"].endswith(".py") and not n["path"].endswith("__init__.py")
    })
    free_samples = [
        "sfp_dnsresolve — DNS resolution",
        "sfp_whois — WHOIS lookup",
        "sfp_shodan — Shodan (API key)",
        "sfp_crt — Certificate Transparency",
        "sfp_github — GitHub repos by email/domain",
        "sfp_gravatar — Gravatar profiles",
        "sfp_bingsearch — Bing search",
        "sfp_hackertarget — passive DNS / port scan",
        "sfp_intfiles — interesting file search",
        "sfp_spider — web spider",
    ]
    write_md(OUT / "26-spiderfoot.md", "SpiderFoot — fonti dati", "https://github.com/smicallef/spiderfoot", "http://localhost:5001/",
             [("Moduli OSINT (modules/*.py)", modules[:150]),
              ("Moduli esempio (free / mixed tier)", free_samples)],
             f"Totale moduli: **{len(modules)}**. Mix free API, tiered API, e scraper. SQLite backend.")
    return len(modules)


def intelowl():
    raw = fetch("https://raw.githubusercontent.com/intelowlproject/IntelOwl/master/configuration/analyzers_config.json")
    try:
        cfg = json.loads(raw)
        analyzers = sorted(cfg.keys()) if isinstance(cfg, dict) else []
    except json.JSONDecodeError:
        analyzers = []
    freeish = [
        "VirusTotal (API key)", "AbuseIPDB (API key)", "OTX AlienVault (API key)",
        "Shodan (API key)", "URLhaus (free)", "PhishStats (free tier)",
        "MalwareBazaar (free)", "ThreatFox (free)", "Yara (local rules)",
        "ClamAV (local)", "Suricata (PCAP, local)", "DNS resolver (free)",
    ]
    secs = [("Analyzer free / tier pubblico (subset documentato)", freeish)]
    if analyzers:
        secs.insert(0, ("Analyzer configurati (analyzers_config.json)", analyzers[:120]))
    write_md(OUT / "27-intelowl.md", "IntelOwl — fonti dati", "https://github.com/intelowlproject/IntelOwl", "https://intelowl.honeynet.org/",
             secs, f"Totale analyzer nel config: **{len(analyzers)}**.")
    return len(analyzers) + len(freeish)


def rotki():
    sources = [
        "Ethereum + L2 — on-chain balances via RPC / Etherscan-like APIs",
        "Bitcoin — UTXO tracking",
        "Exchange APIs — Binance, Kraken, Coinbase, etc. (user keys)",
        "DeFi protocols — Aave, Uniswap, Compound (on-chain decode)",
        "Traditional — manual entry / CSV import",
        "CoinGecko — price oracles (free tier)",
        "CryptoCompare — historical prices (optional key)",
    ]
    write_md(OUT / "28-rotki.md", "Rotki — fonti dati", "https://github.com/rotki/rotki", "https://rotki.com/",
             [("Provider integrati (da docs)", sources)],
             "Desktop self-hosted. Dati salvati localmente encrypted. Molti exchange richiedono API key utente.")
    return len(sources)


def pysystemtrade():
    sources = [
        "Interactive Brokers — live futures via ib_async (user account)",
        "Quandl / Nasdaq Data Link — historical futures (API key)",
        "CSV / Parquet — local price files",
        "arctic / legacy — optional tick store",
        "Carver futures instrument config — bundled metadata",
    ]
    write_md(OUT / "29-pysystemtrade.md", "pysystemtrade — fonti dati", "https://github.com/pst-group/pysystemtrade", None,
             [("Fonti dati futures", sources)],
             "Focus systematic FX/commodity/index futures. Backtest offline; live richiede IB account.")
    return len(sources)


def hummingbot():
    tree = json.loads(fetch("https://api.github.com/repos/hummingbot/hummingbot/git/trees/master?recursive=1"))
    connectors = sorted({n["path"].split("/")[2] for n in tree["tree"] if n["path"].startswith("hummingbot/connector/") and n["type"] == "tree"})
    public = [c for c in connectors if c not in ("gateway", "utilities", "test_support")]
    write_md(OUT / "30-hummingbot.md", "Hummingbot — fonti dati", "https://github.com/hummingbot/hummingbot", None,
             [("Exchange connector (cartelle hummingbot/connector/)", public[:80]),
              ("Protocollo dati per connector CEX", ["REST — order book snapshot, balances, order status", "WebSocket — trades, order book diffs, user stream (authenticated)"]),
              ("DEX via Gateway", ["Uniswap", "PancakeSwap", "Trader Joe", "SushiSwap", "Balancer", "Curve", "etc."])],
             f"Totale connector: **{len(public)}**. Dati pubblici order book senza auth; trading richiede API key exchange.")
    return len(public)


def rebuild_index():
    files = sorted(OUT.glob("*.md"))
    idx = ["# Indice fonti dati — tutti i progetti", "", "| # | File | Progetto |", "|---|------|----------|"]
    for f in files:
        if f.name == "README.md":
            continue
        title = f.read_text(encoding="utf-8").splitlines()[0].replace("# ", "")
        num = f.name.split("-")[0]
        idx.append(f"| {num} | [{f.name}]({f.name}) | {title} |")
    (OUT / "README.md").write_text("\n".join(idx) + "\n", encoding="utf-8")


if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    fns = [obsyd, gridstatus, electricitymaps, herbie, gfw, tar1090, opensanctions, spiderfoot, intelowl, rotki, pysystemtrade, hummingbot]
    for fn in fns:
        try:
            n = fn()
            print(f"OK {fn.__name__}: {n}")
        except Exception as e:
            print(f"FAIL {fn.__name__}: {e}")
    rebuild_index()
    print("OK index")
