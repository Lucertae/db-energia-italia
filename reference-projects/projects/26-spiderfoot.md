# SpiderFoot

- **Fonti dati:** [200+ OSINT modules](https://www.spiderfoot.net/documentation/) · [elenco completo](../data-sources/26-spiderfoot.md)
- **Sito:** https://www.spiderfoot.net
- **Stack:** Python 3, SQLite, web UI + CLI
- **Licenza:** MIT

## Screenshot UI

![SpiderFoot v4](https://www.spiderfoot.net/wp-content/uploads/2022/04/opensource-screenshot-v4.png)

## Dati free / open (ingestion)

**Elenco completo fonti dati (uno per uno):** [data-sources/26-spiderfoot.md](../data-sources/26-spiderfoot.md)

**200+ moduli OSINT** — automazione recon su dominio, IP, email, username.

| Categoria moduli | Esempi |
|------------------|--------|
| **DNS / WHOIS** | sfp_dnsresolve, sfp_whois |
| **CT / certs** | sfp_crt |
| **Code / social** | sfp_github, sfp_gravatar |
| **Threat feeds** | tiered API (Shodan, OTX, etc.) |
| **Web spider** | sfp_spider, sfp_pageinfo |

Correlation engine YAML con 37 regole predefinite. Export CSV/JSON/GEXF.

**Cosa rubare per STRAN:** pipeline OSINT su entità desk (company, vessel owner, port operator); alert su superficie attacco.
