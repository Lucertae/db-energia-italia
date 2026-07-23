# Energy Monitor

- **Fonti dati:** [Energy Monitor](https://energy.worldmonitor.app/) · [elenco completo](../data-sources/03-energy-monitor.md)
- **Fork di:** World Monitor (focus energia)
- **Demo:** self-host `localhost:3000`
- **Stack:** TypeScript, Vite, deck.gl, MapLibre
- **Licenza:** MIT

## Screenshot UI

*Nessuno screenshot ufficiale nel README. UI identica a World Monitor con layer energia.*

Riferimento visivo: [World Monitor](01-world-monitor.md) e variant `energy.worldmonitor.app`.

## Dati free / open (ingestion)

**Elenco completo fonti dati (uno per uno):** [data-sources/03-energy-monitor.md](../data-sources/03-energy-monitor.md)


Dashboard **funziona senza API key** — i pannelli senza credenziali non compaiono.

### Senza chiave / pubblici

| Fonte | Dati |
|-------|------|
| **RSS** | 20+ feed energia, defense, MENA, finance |
| **Yahoo Finance** | Energy stocks (XOM, CVX, XLE, …) |
| **OpenSky** | Voli militari ADS-B |
| **GDELT** | Eventi geopolitici |
| **USGS** | Terremoti |
| **NASA FIRMS** | Incendi |
| **Dataset statici** | Pipeline, porti, chokepoint, basi militari |

### Free tier con registrazione

| Gruppo | Fonte | Dati |
|--------|-------|------|
| Mercati | **FRED**, **Finnhub**, **EIA** | Macro, energia US |
| Tracking | **AISStream**, **Wingbits** | Navi, ADS-B |
| Geo | **ACLED**, **NASA FIRMS** | Conflitti, incendi |
| AI | **Groq** | 14.400 req/giorno (brief energia) |
| Cache | **Upstash** | 10k cmd/giorno |

### Commercial / demo

| Fonte | Dati |
|-------|------|
| **OilPriceAPI** | WTI, Brent, gas, oro (integrazione promozionale) |
