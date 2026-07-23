-- Estrazione geometrie: start/end, WKT, GeoJSON per tutte le feature

ALTER TABLE oim_feature ADD COLUMN IF NOT EXISTS wkt text;
ALTER TABLE oim_feature ADD COLUMN IF NOT EXISTS geojson jsonb;
ALTER TABLE oim_feature ADD COLUMN IF NOT EXISTS lon_start double precision;
ALTER TABLE oim_feature ADD COLUMN IF NOT EXISTS lat_start double precision;
ALTER TABLE oim_feature ADD COLUMN IF NOT EXISTS lon_end double precision;
ALTER TABLE oim_feature ADD COLUMN IF NOT EXISTS lat_end double precision;
ALTER TABLE oim_feature ADD COLUMN IF NOT EXISTS lunghezza_m double precision;
ALTER TABLE oim_feature ADD COLUMN IF NOT EXISTS n_punti integer;

CREATE OR REPLACE FUNCTION oim_geom_start(g geometry)
RETURNS geometry
LANGUAGE sql
IMMUTABLE
STRICT
AS $$
  SELECT CASE
    WHEN ST_GeometryType(g) IN ('ST_Point') THEN g
    WHEN ST_GeometryType(g) IN ('ST_MultiPoint') THEN ST_GeometryN(g, 1)
    WHEN ST_GeometryType(g) IN ('ST_LineString') THEN ST_StartPoint(g)
    WHEN ST_GeometryType(g) IN ('ST_MultiLineString') THEN ST_StartPoint(ST_GeometryN(g, 1))
    WHEN ST_GeometryType(g) IN ('ST_Polygon') THEN ST_PointN(ST_ExteriorRing(g), 1)
    WHEN ST_GeometryType(g) IN ('ST_MultiPolygon') THEN ST_PointN(ST_ExteriorRing(ST_GeometryN(g, 1)), 1)
    WHEN ST_GeometryType(g) IN ('ST_GeometryCollection') THEN oim_geom_start(ST_CollectionHomogenize(g))
    ELSE ST_PointOnSurface(g)
  END;
$$;

CREATE OR REPLACE FUNCTION oim_geom_end(g geometry)
RETURNS geometry
LANGUAGE sql
IMMUTABLE
STRICT
AS $$
  SELECT CASE
    WHEN ST_GeometryType(g) IN ('ST_Point') THEN g
    WHEN ST_GeometryType(g) IN ('ST_MultiPoint') THEN ST_GeometryN(g, ST_NumGeometries(g))
    WHEN ST_GeometryType(g) IN ('ST_LineString') THEN ST_EndPoint(g)
    WHEN ST_GeometryType(g) IN ('ST_MultiLineString') THEN ST_EndPoint(ST_GeometryN(g, ST_NumGeometries(g)))
    WHEN ST_GeometryType(g) IN ('ST_Polygon') THEN ST_PointN(ST_ExteriorRing(g), ST_NPoints(ST_ExteriorRing(g)))
    WHEN ST_GeometryType(g) IN ('ST_MultiPolygon') THEN
      ST_PointN(
        ST_ExteriorRing(ST_GeometryN(g, ST_NumGeometries(g))),
        ST_NPoints(ST_ExteriorRing(ST_GeometryN(g, ST_NumGeometries(g))))
      )
    WHEN ST_GeometryType(g) IN ('ST_GeometryCollection') THEN oim_geom_end(ST_CollectionHomogenize(g))
    ELSE ST_PointOnSurface(g)
  END;
$$;

UPDATE oim_feature SET
  wkt = ST_AsText(geom),
  geojson = ST_AsGeoJSON(geom, 9)::jsonb,
  n_punti = ST_NPoints(geom),
  lunghezza_m = CASE
    WHEN ST_Dimension(geom) >= 1 THEN round(ST_Length(ST_CollectionExtract(geom, 2)::geography)::numeric, 3)::double precision
    ELSE 0
  END,
  lon_start = ST_X(oim_geom_start(geom)),
  lat_start = ST_Y(oim_geom_start(geom)),
  lon_end = ST_X(oim_geom_end(geom)),
  lat_end = ST_Y(oim_geom_end(geom));

ANALYZE oim_feature;

INSERT INTO meta(key, value) VALUES
  ('geom_extract_at', now()::text),
  ('geom_extract_count', (SELECT count(*)::text FROM oim_feature WHERE wkt IS NOT NULL))
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;

-- verifica
SELECT
  count(*) AS totale,
  count(wkt) AS con_wkt,
  count(geojson) AS con_geojson,
  count(lon_start) AS con_start,
  count(lon_end) AS con_end
FROM oim_feature;

SELECT id, voce_id, geom_type,
  round(lunghezza_m::numeric, 1) AS lunghezza_m,
  n_punti,
  lon_start, lat_start, lon_end, lat_end,
  left(wkt, 80) AS wkt_preview
FROM oim_feature
WHERE geom_type = 'LineString'
LIMIT 3;
