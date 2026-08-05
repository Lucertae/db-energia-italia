# Database — infrastruttura & energia Italia

Cartella unica del progetto. Catalogo aggiornato: **2026-07-23** (~10+ GB utili).

| # | Cartella | Ruolo | Volume (catalogo) |
|---|----------|-------|-------------------|
| 1 | [`oim-italia/`](oim-italia/) | OpenInfraMap / OSM — geometrie infrastruttura | ~3.0 GB |
| 2 | [`entsoe-italia/`](entsoe-italia/) | ENTSO-E Transparency — serie operative | ~0.63 GB |
| 3 | [`owid-italia/`](owid-italia/) | Our World in Data — estratti Italia | ~21 MB |
| 4 | [`consumi-italia/`](consumi-italia/) | Consumi: ARERA + Terna + Eurostat + MASE | ~1.6 GB |
| 5 | [`mercati-italia/`](mercati-italia/) | Mercati: GME + gas + GSE + prezzi live | ~1.7 GB |
| 6 | [`meteo-italia/`](meteo-italia/) | Meteo: Open-Meteo + NASA POWER + Meteostat | ~1.1 GB |
| 7 | [`socio-italia/`](socio-italia/) | Popolazione, PIL/VA, suolo, mobilità, povertà | ~2.2 GB |
| 8 | [`impianti-italia/`](impianti-italia/) | Centrali: Wikidata, WRI, OSM, GEM | ~78 MB |
| 9 | [`terna-italia/`](terna-italia/) | Vista dedicata Terna (link a consumi) | ~75 MB |
| 10 | [`imprese-energia-italia/`](imprese-energia-italia/) | Operatori/venditori ARERA | ~23 MB |

Legacy: `owid-energy-italia/` → `owid-italia/sources/energy-data/`.

**Metadati:** ogni pacchetto ha `METADATI.txt` (cosa/quanto/copertura) e `catalog.csv`.  
Indice globale: [`catalog.csv`](catalog.csv) · [`CATALOG.md`](CATALOG.md).

Rigenera stats:

```powershell
python db/scripts/build_metadata_catalogs.py
```

Script trasversali: `db/scripts/`.

---

## Avvio rapido

```powershell
docker compose -f db/oim-italia/docker-compose.yml up -d postgis
python db/entsoe-italia/scripts/harvest_all_italia.py
python db/owid-italia/scripts/harvest_all.py
python db/consumi-italia/scripts/harvest_all.py
python db/mercati-italia/scripts/harvest_all.py
python db/meteo-italia/scripts/harvest_meteo_alt.py
python db/scripts/harvest_socio_italia.py
```

Dettaglio refresh e buchi noti: `db/<pacchetto>/METADATI.txt` sezione 2 e 6.

---


