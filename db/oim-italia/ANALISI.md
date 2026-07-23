# Analisi statistica e topologia

Stack consigliato: **PostGIS resta il motore** (stats SQL + topologia di rete).  
Il `.gpkg` è comodo per QGIS; per analisi pesanti usa Postgres o Parquet/DuckDB.

## 1. Statistica (SQL, già nel DB)

```sql
-- per categoria
SELECT * FROM v_stats_categoria ORDER BY n DESC;

-- per voce legenda
SELECT * FROM v_stats_voce WHERE category_id = 'linee_elettriche' ORDER BY lunghezza_tot_m DESC;

-- distribuzione quote
SELECT width_bucket(sslm_start_m, 0, 3000, 15) AS fascia,
       count(*), round(avg(sslm_start_m)::numeric,1)
FROM oim_feature GROUP BY 1 ORDER BY 1;
```

Connessione: `postgresql://oim:oim@127.0.0.1:5433/oim_italia`

## 2. Topologia di rete (nodi / archi)

Tabelle:

| Tabella / vista | Contenuto |
|-----------------|-----------|
| `oim_node` | nodi = estremi unici delle LineString |
| `oim_edge` | archi = linee con `node_start` / `node_end` |
| `v_node_degree` | grado del nodo (n. linee incidenti) |

```sql
-- nodi giunzione (grado >= 3)
SELECT * FROM v_node_degree WHERE grado >= 3 ORDER BY grado DESC LIMIT 50;

-- linee collegate allo stesso nodo
SELECT e.*
FROM oim_edge e
WHERE e.node_start = 123 OR e.node_end = 123;

-- percorso grezzo: archi uscenti da un nodo
SELECT e.edge_id, e.voce_id, e.lunghezza_m, e.node_start, e.node_end
FROM oim_edge e
WHERE e.node_start = :n OR e.node_end = :n;
```

Costruzione: `sql/06_analytics_topology.sql`

## 3. Export per analisi esterna

Cartella `export/`:

| File | Uso |
|------|-----|
| `oim_italia.gpkg` | QGIS: feature + `oim_node` + `oim_edge` + legenda |
| `oim_italia.dump` | ripristino PostGIS |
| `oim_feature.csv` | stats in Excel/R/Python/Pandas |
| `oim_edge.csv` / `oim_node.csv` | grafo rete (NetworkX, R igraph) |
| `v_stats_categoria.csv` / `v_stats_voce.csv` | aggregati pronti |

### Python (stats + grafo)

```python
import pandas as pd
import networkx as nx

feat = pd.read_csv("export/oim_feature.csv")
print(feat.groupby("category_id")["lunghezza_m"].sum())

edges = pd.read_csv("export/oim_edge.csv")
G = nx.from_pandas_edgelist(edges, "node_start", "node_end",
                            edge_attr=["lunghezza_m", "voce_id", "category_id"])
print(G.number_of_nodes(), G.number_of_edges())
```

## 4. Cosa usare quando

| Obiettivo | Strumento |
|-----------|-----------|
| Aggregati, distribuzione, filtri | `v_stats_*` in PostGIS o Parquet/DuckDB |
| Connettività rete, grado, path | `oim_node` + `oim_edge` in PostGIS |
| Mappa interattiva / check visivo | QGIS + `.gpkg` |
| ML / dataframe | CSV + Pandas/Polars; grafo con NetworkX su edge/node |

## 5. Numeri topologia (Italia)

- nodi (`oim_node`): ~123 729
- archi (`oim_edge`): ~74 735 (tutte le LineString)
- viste stats: `v_stats_categoria`, `v_stats_voce`, `v_stats_geom_type`, `v_node_degree`
