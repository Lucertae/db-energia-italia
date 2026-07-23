-- Open Infrastructure Map — schema Italia
CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS meta (
  key text PRIMARY KEY,
  value text NOT NULL
);

CREATE TABLE IF NOT EXISTS legend_category (
  id text PRIMARY KEY,
  label_it text NOT NULL,
  label_en text,
  layer_oim text NOT NULL
);

CREATE TABLE IF NOT EXISTS legend_voce (
  id text PRIMARY KEY,
  category_id text NOT NULL REFERENCES legend_category(id),
  label_it text NOT NULL,
  sort_order int NOT NULL DEFAULT 0
);

-- Feature table unificata (tutte le geometrie classificate)
CREATE TABLE IF NOT EXISTS oim_feature (
  id bigserial PRIMARY KEY,
  osm_id bigint NOT NULL,
  osm_type char(1) NOT NULL CHECK (osm_type IN ('n','w','r','N','W','R')),
  category_id text REFERENCES legend_category(id),
  voce_id text REFERENCES legend_voce(id),
  geom_type text NOT NULL,
  name text,
  operator text,
  ref text,
  voltage_v double precision,
  frequency text,
  substance text,
  source text,
  usage text,
  diameter double precision,
  pressure text,
  location text,
  tags jsonb NOT NULL DEFAULT '{}'::jsonb,
  is_underground boolean NOT NULL DEFAULT false,
  has_ref boolean NOT NULL DEFAULT false,
  geom geometry(Geometry, 4326) NOT NULL,
  wkt text,
  geojson jsonb,
  lon_start double precision,
  lat_start double precision,
  lon_end double precision,
  lat_end double precision,
  lunghezza_m double precision,
  n_punti integer,
  sslm_start_m double precision,
  sslm_end_m double precision
);

CREATE INDEX IF NOT EXISTS oim_feature_geom_gix ON oim_feature USING GIST (geom);
CREATE INDEX IF NOT EXISTS oim_feature_cat_idx ON oim_feature (category_id);
CREATE INDEX IF NOT EXISTS oim_feature_voce_idx ON oim_feature (voce_id);
CREATE INDEX IF NOT EXISTS oim_feature_osm_idx ON oim_feature (osm_type, osm_id);
CREATE INDEX IF NOT EXISTS oim_feature_tags_gin ON oim_feature USING GIN (tags);

-- Tabelle grezze osm2pgsql flex (create dallo style Lua se non esistono)
-- power / telecom / pipeline / water staging
