# Open Infrastructure Map — DB vettoriale Italia

Percorso: `db/oim-italia/` · Volume tipico **~2.9 GB**.

Database PostGIS con le **10 categorie** e **75 voci** della legenda OIM, intera Italia (Geofabrik).  
Scheda: [`METADATI.txt`](METADATI.txt)

## Connessione

| Campo | Valore |
|-------|--------|
| Host | `localhost` |
| Porta | `5433` |
| Database | `oim_italia` |
| User / Password | `oim` / `oim` |

```
postgresql://oim:oim@127.0.0.1:5433/oim_italia
```

## Tabelle

- `legend_category` — 10 categorie  
- `legend_voce` — 75 voci  
- `oim_feature` — geometrie classificate (`category_id`, `voce_id`, `geom`, WKT/GeoJSON, quote, lunghezze)  
- `staging_*` — osm2pgsql intermedie  

## Build

Docker Desktop, ~8 GB liberi (PBF ~2.1 GB + DB):

```powershell
python db\oim-italia\scripts\build_italia.py
```

## Senza Docker

Export in `export/`: `oim_italia.gpkg`, `oim_italia.dump`, CSV feature/node/edge e stats.

Attribuire OpenStreetMap (ODbL).
