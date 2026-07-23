# Aziende energia in crisi — pipeline multi-sorgente (Italia)

Pipeline Python 3.11+ che aggrega fonti pubbliche (e API opzionali a pagamento) per produrre l’elenco di imprese italiane del settore energia / adiacenti in:

- **(A)** procedura concorsuale (liquidazione giudiziale, concordato, liquidazione coatta, amministrazione straordinaria, composizione negoziata / misure protettive)
- **(B)** distress pubblico (tavoli MIMIT, liquidazione volontaria segnalata, news)

Output principale: `output/aziende_energia_crisi.txt` (+ `.csv` / `.json`).

## Disclaimer

I dati raccolti da fonti pubbliche **non sostituiscono** la visura camerale ufficiale. Prima di qualsiasi uso commerciale (contatto, due diligence, offerte di acquisto asset) verificare lo stato su [registroimprese.it](https://www.registroimprese.it). Rispettare il GDPR: i dati trattati sono di imprese, ma i nominativi di persone fisiche (ditte individuali, curatori) vanno trattati con base giuridica adeguata.

## Setup

```powershell
cd aziende-crisi-energia
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Opzionale: valorizza in `.env`:

| Variabile | Uso |
|-----------|-----|
| `OPENAPI_IT_KEY` | Company API (`company.openapi.com`) — ricerca per ATECO + stato |
| `CERVED_KEY` | riservata / futura |
| `TELEMACO_USER` / `TELEMACO_PASS` | stub CNC (convenzione InfoCamere) |
| `ANAGRAFICA_LOCALE_PATH` | default `../aziende-energetiche-it.txt` per enrichment P.IVA |

### openapi.it — costo e registrazione

1. Registrati su [openapi.com](https://openapi.com) / prodotto Company Search  
2. Endpoint usati: `GET https://company.openapi.com/IT-search` (Bearer token)  
3. Costo orientativo: da ~€0.001/hit (name) a pochi centesimi con enrichment Start/Advanced  
4. Senza chiave il modulo viene **saltato** (warning in log)

## Uso

```powershell
# run completo
python main.py

# solo alcune fonti
python main.py --sources mimit,news,gu

# lookback GU/news, no cache, solo ATECO/anagrafica
python main.py --lookback-months 12 --no-cache --ateco-only
```

Ogni modulo è eseguibile da solo:

```powershell
python -m sources.mimit_tavoli
python -m sources.pvp_giustizia
python -m sources.fallimenti_news
```

## Architettura

| Modulo | Fonte | Note |
|--------|-------|------|
| `pvp` | pvp.giustizia.it JSON `ricerca/vendite` + dettaglio `ve-ms/vendite/{id}` | rate limit ≥2s, cache |
| `gu` | Gazzetta via Google News RSS `site:gazzettaufficiale.it` | ricerca HTML GU spesso WAF/login |
| `mimit` | mimit.gov.it tavoli attivi/monitoraggio | + match anagrafica energia |
| `openapi` | company.openapi.com | richiede chiave |
| `astalegale` | astalegale.net → fallback fallcoaste.it | |
| `news` | Google News RSS | qualità bassa, da verificare in visura |
| `cnc` | stub Telemaco + proxy news misure protettive | niente elenco aperto ufficiale |

Comportamento: moduli indipendenti, parallelo max 3, merge + dedup (P.IVA → fuzzy denominazione+provincia >92), enrichment anagrafica locale, export.

## Formato riga TXT

`RAGIONE SOCIALE | P.IVA/CF | ATECO | PROVINCIA | STATO | FONTE | NOTE`

## Limiti noti

- **Registro Imprese / Telemaco**: non esiste API pubblica gratuita “tutte le fallite per ATECO”.  
- **Composizione negoziata**: misure protettive pubblicate a Registro Imprese, non in elenco aperto.  
- **Gazzetta Ufficiale**: full-text pubblico spesso dietro WAF/login; il modulo degrada su RSS.  
- **PVP**: il debitore non sempre è nei `soggetti` dell’annuncio (specie esecuzioni immobiliari).  
- Rispettare robots.txt / ToS; User-Agent identificativo; caching in `cache/`.
