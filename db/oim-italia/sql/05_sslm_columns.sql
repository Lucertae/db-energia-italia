-- Quote s.s.l.m. (sul livello del mare) su start/end
ALTER TABLE oim_feature ADD COLUMN IF NOT EXISTS sslm_start_m double precision;
ALTER TABLE oim_feature ADD COLUMN IF NOT EXISTS sslm_end_m double precision;

CREATE TABLE IF NOT EXISTS elevation_cache (
  lon_r numeric(8,4) NOT NULL,
  lat_r numeric(8,4) NOT NULL,
  elevation_m double precision,
  PRIMARY KEY (lon_r, lat_r)
);

CREATE INDEX IF NOT EXISTS elevation_cache_elev_idx ON elevation_cache (elevation_m);
