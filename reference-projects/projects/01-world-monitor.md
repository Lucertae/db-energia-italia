# World Monitor

- **Fonti dati:** [WM data catalog](https://www.worldmonitor.app/docs/data-sources) · [elenco completo](../data-sources/01-world-monitor.md)
- **Demo:** https://worldmonitor.app · varianti `energy.`, `commodity.`, `finance.`
- **Stack:** TypeScript, Vite, globe.gl, deck.gl, Tauri desktop
- **Licenza:** AGPL-3.0

## Screenshot UI

![Dashboard](../images/worldmonitor.jpg)

![Commodity variant live](../images/worldmonitor-commodity.png)

## Dati free / open (ingestion)

**Elenco completo fonti dati (uno per uno):** [data-sources/01-world-monitor.md](../data-sources/01-world-monitor.md)


Funziona **senza API key** per molte funzioni base. Catalogo API: https://www.worldmonitor.app/docs/data-sources

### Feed RSS — elenco completo uno per uno

**Non "500+ curati" generico:** nel codice ci sono **568 feed nominati** in `src/config/feeds.ts`, più varianti (`tech`, `finance`, `commodity`, `energy`, `happy`) e digest server-side.

→ Vedi anche **[worldmonitor-feeds-list.md](../worldmonitor-feeds-list.md)** (626 nomi unici, elencati uno per uno).
| **USGS** | Terremoti M4.5+ |
| **NASA EONET / GDACS** | Disastri naturali |
| **NASA FIRMS** | Incendi satellitari |
| **GDELT** | Eventi geopolitici geocodificati |
| **OpenSky / AISStream** | Voli ADS-B, navi AIS |
| **Yahoo Finance** | Indici, commodity, crypto sparkline |
| **CoinGecko** | Prezzi crypto |
| **Polymarket** | Prediction markets (tier pubblico) |
| **FRED / IMF / BIS / WTO** | Macro, tassi, trade (con key free dove richiesta) |
| **CelesTrak** | TLE satelliti |
| **Cloudflare Radar** | Internet outages |
| **Feodo / abuse.ch** | IOC cyber threat |
| **Ollama (locale)** | AI senza cloud |

### Free tier con registrazione

| Fonte | Dati | Note |
|-------|------|------|
| **ACLED** | Conflitti, proteste | Token ricercatori |
| **Wingbits** | ADS-B avanzato | Free tier |
| **Finnhub** | Mercati | Free tier |
| **Groq / OpenRouter** | Brief AI | Quote giornaliere free |
| **Upstash Redis** | Cache | 10k cmd/giorno |

### Layer mappa (56 tipi)

Conflitti, basi militari, cavi sottomarini, pipeline, porti, chokepoint, datacenter, minerali critici, rotte commerciali, GPS jamming, travel advisories, ritardi aeroportuali.
