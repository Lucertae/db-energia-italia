-- Analytics + topologia su oim_feature
-- 1) Viste statistiche
-- 2) Nodi / archi da estremi linee (grafo grezzo per topologia di rete)

DROP VIEW IF EXISTS v_stats_categoria CASCADE;
DROP VIEW IF EXISTS v_stats_voce CASCADE;
DROP VIEW IF EXISTS v_stats_geom_type CASCADE;

CREATE OR REPLACE VIEW v_stats_categoria AS
SELECT
  category_id,
  count(*) AS n,
  count(*) FILTER (WHERE geom_type = 'LineString') AS n_linee,
  count(*) FILTER (WHERE geom_type = 'Point') AS n_punti,
  count(*) FILTER (WHERE geom_type = 'Polygon') AS n_poligoni,
  round(sum(COALESCE(lunghezza_m, 0))::numeric, 1) AS lunghezza_tot_m,
  round(avg(sslm_start_m)::numeric, 1) AS sslm_media_m,
  round(min(sslm_start_m)::numeric, 1) AS sslm_min_m,
  round(max(sslm_start_m)::numeric, 1) AS sslm_max_m
FROM oim_feature
GROUP BY category_id;

CREATE OR REPLACE VIEW v_stats_voce AS
SELECT
  category_id,
  voce_id,
  count(*) AS n,
  round(sum(COALESCE(lunghezza_m, 0))::numeric, 1) AS lunghezza_tot_m,
  round(avg(lunghezza_m) FILTER (WHERE lunghezza_m > 0)::numeric, 1) AS lunghezza_media_m,
  round(avg(sslm_start_m)::numeric, 1) AS sslm_media_m
FROM oim_feature
GROUP BY category_id, voce_id;

CREATE OR REPLACE VIEW v_stats_geom_type AS
SELECT geom_type, count(*) AS n,
  round(sum(COALESCE(lunghezza_m, 0))::numeric, 1) AS lunghezza_tot_m
FROM oim_feature
GROUP BY geom_type;

-- Nodi: estremi unici delle linee (arrotondati ~1.1 m @ 5 decimali)
DROP TABLE IF EXISTS oim_edge CASCADE;
DROP TABLE IF EXISTS oim_node CASCADE;

CREATE TABLE oim_node (
  node_id bigserial PRIMARY KEY,
  lon numeric(9,5) NOT NULL,
  lat numeric(9,5) NOT NULL,
  sslm_m double precision,
  geom geometry(Point, 4326) NOT NULL,
  UNIQUE (lon, lat)
);

CREATE TABLE oim_edge (
  edge_id bigserial PRIMARY KEY,
  feature_id bigint NOT NULL REFERENCES oim_feature(id),
  osm_id bigint,
  category_id text,
  voce_id text,
  name text,
  ref text,
  lunghezza_m double precision,
  sslm_start_m double precision,
  sslm_end_m double precision,
  node_start bigint REFERENCES oim_node(node_id),
  node_end bigint REFERENCES oim_node(node_id),
  geom geometry(Geometry, 4326) NOT NULL
);

-- Popola nodi da start/end di tutte le LineString
INSERT INTO oim_node (lon, lat, sslm_m, geom)
SELECT lon, lat, avg(sslm) AS sslm_m, ST_SetSRID(ST_MakePoint(lon::float8, lat::float8), 4326)
FROM (
  SELECT round(lon_start::numeric, 5) AS lon, round(lat_start::numeric, 5) AS lat, sslm_start_m AS sslm
  FROM oim_feature WHERE geom_type = 'LineString'
  UNION ALL
  SELECT round(lon_end::numeric, 5), round(lat_end::numeric, 5), sslm_end_m
  FROM oim_feature WHERE geom_type = 'LineString'
) s
GROUP BY lon, lat;

CREATE INDEX oim_node_geom_gix ON oim_node USING GIST (geom);
CREATE INDEX oim_node_lonlat_idx ON oim_node (lon, lat);

-- Archi = linee collegate ai nodi start/end
INSERT INTO oim_edge (
  feature_id, osm_id, category_id, voce_id, name, ref,
  lunghezza_m, sslm_start_m, sslm_end_m, node_start, node_end, geom
)
SELECT
  f.id,
  f.osm_id,
  f.category_id,
  f.voce_id,
  f.name,
  f.ref,
  f.lunghezza_m,
  f.sslm_start_m,
  f.sslm_end_m,
  ns.node_id,
  ne.node_id,
  f.geom
FROM oim_feature f
JOIN oim_node ns
  ON ns.lon = round(f.lon_start::numeric, 5)
 AND ns.lat = round(f.lat_start::numeric, 5)
JOIN oim_node ne
  ON ne.lon = round(f.lon_end::numeric, 5)
 AND ne.lat = round(f.lat_end::numeric, 5)
WHERE f.geom_type = 'LineString';

CREATE INDEX oim_edge_geom_gix ON oim_edge USING GIST (geom);
CREATE INDEX oim_edge_cat_idx ON oim_edge (category_id);
CREATE INDEX oim_edge_voce_idx ON oim_edge (voce_id);
CREATE INDEX oim_edge_nodes_idx ON oim_edge (node_start, node_end);
CREATE INDEX oim_edge_feature_idx ON oim_edge (feature_id);

-- Grado nodale (quante linee toccano il nodo)
CREATE OR REPLACE VIEW v_node_degree AS
SELECT
  n.node_id,
  n.lon,
  n.lat,
  n.sslm_m,
  count(e.edge_id) AS grado,
  n.geom
FROM oim_node n
LEFT JOIN oim_edge e
  ON e.node_start = n.node_id OR e.node_end = n.node_id
GROUP BY n.node_id, n.lon, n.lat, n.sslm_m, n.geom;

ANALYZE oim_node;
ANALYZE oim_edge;

INSERT INTO meta(key, value) VALUES
  ('topology_at', now()::text),
  ('topology_nodes', (SELECT count(*)::text FROM oim_node)),
  ('topology_edges', (SELECT count(*)::text FROM oim_edge))
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

SELECT 'nodes' AS k, count(*)::text AS v FROM oim_node
UNION ALL SELECT 'edges', count(*)::text FROM oim_edge
UNION ALL SELECT 'stats_categorie', count(*)::text FROM v_stats_categoria;
