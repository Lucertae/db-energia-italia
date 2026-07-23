# IntelOwl

- **Fonti dati:** [500+ threat intel analyzers](https://intelowlproject.github.io/docs/) · [elenco completo](../data-sources/27-intelowl.md)
- **Demo:** https://intelowl.honeynet.org
- **Docs:** https://intelowlproject.github.io
- **Stack:** Django, React, Docker, PostgreSQL
- **Licenza:** AGPL-3.0

## Screenshot UI

![IntelOwl logo](https://raw.githubusercontent.com/intelowlproject/IntelOwl/master/static/intel_owl_positive.png)

## Dati free / open (ingestion)

**Elenco completo fonti dati (uno per uno):** [data-sources/27-intelowl.md](../data-sources/27-intelowl.md)

**500+ analyzer** — threat intel su file, URL, IP, dominio, hash, PCAP.

| Tipo | Analyzer esempio |
|------|------------------|
| **Reputation** | VirusTotal, AbuseIPDB, OTX, Shodan |
| **Malware feeds** | URLhaus, MalwareBazaar, ThreatFox (free) |
| **Local** | ClamAV, Yara, Suricata (PCAP) |
| **Mobile/APK** | Quark-Engine, Androguard, MobSF |

API unica per enrichment parallelo. GUI React con dashboard e form analisi.

**Cosa rubare per STRAN:** enrich IOC da feed cyber (complemento Feodo/abuse.ch in WM); health panel su analyzer availability.
