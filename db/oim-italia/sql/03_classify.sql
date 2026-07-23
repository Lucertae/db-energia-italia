-- Classificazione Italia: assegna category_id + voce_id sulle feature staging

CREATE OR REPLACE FUNCTION oim_parse_voltage(v text)
RETURNS double precision
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT CASE
    WHEN v IS NULL OR btrim(v) = '' THEN 0
    ELSE (
      SELECT max(
        CASE
          WHEN x IS NULL THEN 0
          WHEN x < 1000 THEN x * 1000  -- valori in kV → volt
          ELSE x
        END
      )
      FROM (
        SELECT NULLIF(regexp_replace(part, '[^0-9.]', '', 'g'), '')::double precision AS x
        FROM unnest(string_to_array(v, ';')) AS part
      ) s
    )
  END;
$$;

CREATE OR REPLACE FUNCTION oim_is_hvdc(freq text)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT freq IS NOT NULL AND btrim(freq) <> '' AND NULLIF(regexp_replace(freq, '[^0-9.]', '', 'g'), '')::double precision = 0;
$$;

CREATE OR REPLACE FUNCTION oim_is_traction(freq text)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT freq IS NOT NULL AND btrim(freq) <> ''
    AND NULLIF(regexp_replace(freq, '[^0-9.]', '', 'g'), '')::double precision
        NOT IN (0, 50, 60);
$$;

CREATE OR REPLACE FUNCTION oim_is_underground(location text, tunnel text, power_type text)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
AS $$
  SELECT
    COALESCE(location, '') IN ('underground', 'underwater')
    OR COALESCE(tunnel, '') IN ('yes', 'true', '1')
    OR (COALESCE(power_type, '') IN ('cable', 'minor_cable') AND COALESCE(location, '') = '');
$$;

TRUNCATE oim_feature RESTART IDENTITY;

-- ========== LINEE ELETTRICHE ==========
INSERT INTO oim_feature (
  osm_id, osm_type, category_id, voce_id, geom_type, name, operator, ref,
  voltage_v, frequency, location, tags, is_underground, has_ref, geom
)
SELECT
  osm_id,
  osm_type,
  'linee_elettriche',
  CASE
    WHEN oim_is_hvdc(frequency) THEN 'hvdc'
    WHEN oim_is_traction(frequency) THEN 'trazione'
    WHEN oim_parse_voltage(voltage) >= 550000 THEN 'ge_550kv'
    WHEN oim_parse_voltage(voltage) >= 310000 THEN 'ge_310kv'
    WHEN oim_parse_voltage(voltage) >= 220000 THEN 'ge_220kv'
    WHEN oim_parse_voltage(voltage) >= 132000 THEN 'ge_132kv'
    WHEN oim_parse_voltage(voltage) >= 52000 THEN 'ge_52kv'
    WHEN oim_parse_voltage(voltage) >= 25000 THEN 'ge_25kv'
    WHEN oim_parse_voltage(voltage) >= 10000 THEN 'ge_10kv'
    ELSE 'lt_10kv'
  END,
  'LineString',
  NULLIF(name, ''),
  NULLIF(operator, ''),
  NULLIF(ref, ''),
  oim_parse_voltage(voltage),
  frequency,
  location,
  tags,
  oim_is_underground(location, tunnel, power),
  (ref IS NOT NULL AND btrim(ref) <> ''),
  geom
FROM staging_power_line;

-- Flag sotterranea come seconda riga? No: campo is_underground.
-- Matricola: has_ref; opzionale vista dedicata.

-- ========== CENTRALI ==========
INSERT INTO oim_feature (
  osm_id, osm_type, category_id, voce_id, geom_type, name, operator, source, tags, geom
)
SELECT
  osm_id, osm_type, 'centrali_elettriche',
  CASE plant_source
    WHEN 'coal' THEN 'carbone'
    WHEN 'geothermal' THEN 'geotermico'
    WHEN 'hydro' THEN 'idroelettrico'
    WHEN 'nuclear' THEN 'nucleare'
    WHEN 'oil' THEN 'gas_petrolio'
    WHEN 'gas' THEN 'gas_petrolio'
    WHEN 'diesel' THEN 'gas_petrolio'
    WHEN 'solar' THEN 'solare'
    WHEN 'wind' THEN 'eolico'
    WHEN 'biomass' THEN 'biomassa'
    WHEN 'waste' THEN 'termovalorizzatore'
    WHEN 'battery' THEN 'batterie'
    ELSE 'other_unknown'
  END,
  CASE WHEN ST_GeometryType(geom) LIKE '%Point%' THEN 'Point' ELSE 'Polygon' END,
  NULLIF(name, ''), NULLIF(operator, ''), plant_source, tags, geom
FROM staging_power_plant;

-- ========== GENERATORI ==========
INSERT INTO oim_feature (
  osm_id, osm_type, category_id, voce_id, geom_type, name, operator, source, tags, geom
)
SELECT
  osm_id, osm_type, 'generatori',
  CASE
    WHEN generator_source = 'wind' THEN 'turbina_eolica'
    WHEN generator_source = 'solar' AND ST_GeometryType(geom) LIKE '%Point%' THEN 'pannello_solare_nodo'
    WHEN generator_source = 'solar' THEN 'pannello_solare'
    ELSE 'generatore_altro'
  END,
  CASE WHEN ST_GeometryType(geom) LIKE '%Point%' THEN 'Point' ELSE 'Polygon' END,
  NULLIF(name, ''), NULLIF(operator, ''), generator_source, tags, geom
FROM staging_power_generator;

-- ========== SUPPORTI ==========
INSERT INTO oim_feature (
  osm_id, osm_type, category_id, voce_id, geom_type, name, ref, tags, geom
)
SELECT
  osm_id, osm_type, 'supporti_linee',
  CASE
    WHEN power IN ('tower', 'portal') AND transition THEN 'traliccio_transizione'
    WHEN power IN ('tower', 'portal') THEN 'torre_traliccio'
    WHEN power = 'pole' AND transition THEN 'palo_transizione'
    ELSE 'palo_elettrico'
  END,
  CASE WHEN ST_GeometryType(geom) LIKE '%Line%' THEN 'LineString' ELSE 'Point' END,
  NULLIF(name, ''), NULLIF(ref, ''), tags, geom
FROM staging_power_support;

-- ========== SWITCHGEAR ==========
INSERT INTO oim_feature (
  osm_id, osm_type, category_id, voce_id, geom_type, name, voltage_v, tags, geom
)
SELECT
  osm_id, osm_type, 'apparecchiature_manovra',
  CASE
    WHEN power = 'converter' OR substation = 'converter' THEN 'conversione_dc'
    WHEN power = 'transformer' AND transformer_type = 'current' THEN 'current_transformer'
    WHEN power = 'transformer' AND transformer_type = 'potential' THEN 'potential_transformer'
    WHEN power = 'transformer' AND (windings = '3' OR voltage_tertiary IS NOT NULL) THEN 'trasformatore_3'
    WHEN power = 'transformer' THEN 'trasformatore'
    WHEN power = 'switch' AND switch = 'disconnector' THEN 'sezionatore'
    WHEN power = 'switch' AND switch = 'circuit_breaker' THEN 'interruttore'
    WHEN power = 'switch' THEN 'organo_manovra_generico'
    WHEN compensator = 'series_reactor' OR power_type = 'series_reactor' THEN 'reattanza_serie'
    WHEN compensator = 'shunt_reactor' OR power_type = 'shunt_reactor' THEN 'reattanza_shunt'
    WHEN compensator = 'series_capacitor' OR power_type = 'series_capacitor' THEN 'condensatore_serie'
    WHEN compensator = 'shunt_capacitor' OR power_type = 'shunt_capacitor' THEN 'condensatore_shunt'
    WHEN compensator = 'filter' OR power_type = 'filter' THEN 'filtro'
    WHEN power = 'compensator' THEN 'compensatore_altro'
    ELSE 'compensatore_altro'
  END,
  CASE WHEN ST_GeometryType(geom) LIKE '%Point%' THEN 'Point' ELSE 'Polygon' END,
  NULLIF(name, ''), oim_parse_voltage(voltage), tags, geom
FROM staging_power_switchgear;

-- ========== TELECOM ==========
INSERT INTO oim_feature (osm_id, osm_type, category_id, voce_id, geom_type, name, operator, tags, geom)
SELECT osm_id, osm_type, 'telecomunicazioni', 'cavo', 'LineString',
  NULLIF(name, ''), NULLIF(operator, ''), tags, geom
FROM staging_telecom_cable;

INSERT INTO oim_feature (osm_id, osm_type, category_id, voce_id, geom_type, name, operator, tags, geom)
SELECT osm_id, osm_type, 'telecomunicazioni', 'torre_palo_telecom',
  CASE WHEN ST_GeometryType(geom) LIKE '%Point%' THEN 'Point' ELSE 'Polygon' END,
  NULLIF(name, ''), NULLIF(operator, ''), tags, geom
FROM staging_telecom_mast;

INSERT INTO oim_feature (osm_id, osm_type, category_id, voce_id, geom_type, name, operator, tags, geom)
SELECT osm_id, osm_type, 'telecomunicazioni',
  CASE WHEN kind IN ('data_center', 'data_centre') THEN 'datacenter' ELSE 'centrale_telefonica' END,
  CASE WHEN ST_GeometryType(geom) LIKE '%Point%' THEN 'Point' ELSE 'Polygon' END,
  NULLIF(name, ''), NULLIF(operator, ''), tags, geom
FROM staging_telecom_building;

INSERT INTO oim_feature (osm_id, osm_type, category_id, voce_id, geom_type, name, operator, tags, geom)
SELECT osm_id, osm_type, 'telecomunicazioni', 'armadio',
  CASE WHEN ST_GeometryType(geom) LIKE '%Point%' THEN 'Point' ELSE 'Polygon' END,
  NULLIF(name, ''), NULLIF(operator, ''), tags, geom
FROM staging_telecom_cabinet;

-- ========== PIPELINES (gas / petrolio / acqua / other) ==========
INSERT INTO oim_feature (
  osm_id, osm_type, category_id, voce_id, geom_type, name, operator,
  substance, usage, diameter, pressure, tags, geom
)
SELECT
  osm_id, osm_type,
  CASE
    WHEN substance IN ('gas','natural_gas','cng','lpg','lng') THEN 'gas'
    WHEN substance IN ('oil','fuel','ngl','y-grade','hydrocarbons','condensate','naphtha','hydrogen') THEN 'petrolio'
    WHEN substance IN ('water','rainwater','hot_water','wastewater','sewage','waterwaste','steam') THEN 'acqua'
    ELSE 'other_pipelines'
  END,
  CASE
    -- gas
    WHEN substance IN ('gas','natural_gas','cng','lpg','lng') AND usage = 'transmission' AND COALESCE(diameter,0) >= 700 THEN 'gas_tx_dn700'
    WHEN substance IN ('gas','natural_gas','cng','lpg','lng') AND usage = 'transmission' AND COALESCE(diameter,0) >= 300 THEN 'gas_tx_dn300'
    WHEN substance IN ('gas','natural_gas','cng','lpg','lng') AND usage = 'transmission' THEN 'gas_tx_lt_dn300'
    WHEN substance IN ('gas','natural_gas','cng','lpg','lng') AND (pressure = 'high' OR COALESCE(NULLIF(regexp_replace(pressure,'[^0-9.]','','g'),'')::double precision,0) >= 1) THEN 'gas_dist_high'
    WHEN substance IN ('gas','natural_gas','cng','lpg','lng') AND (pressure = 'intermediate' OR COALESCE(NULLIF(regexp_replace(pressure,'[^0-9.]','','g'),'')::double precision,0) >= 0.1) THEN 'gas_dist_intermediate'
    WHEN substance IN ('gas','natural_gas','cng','lpg','lng') THEN 'gas_dist_low'
    -- petrolio
    WHEN substance = 'oil' THEN 'petrolio_oil'
    WHEN substance IN ('ngl','y-grade','hydrocarbons','condensate','naphtha') THEN 'prodotti_intermedi'
    WHEN substance = 'fuel' THEN 'carburante'
    WHEN substance = 'hydrogen' THEN 'idrogeno'
    -- acqua
    WHEN substance IN ('water','rainwater') THEN 'acqua_dolce'
    WHEN substance = 'hot_water' THEN 'acqua_calda'
    WHEN substance = 'steam' THEN 'vapore'
    WHEN substance IN ('wastewater','sewage','waterwaste') THEN 'acque_reflue'
    -- other
    WHEN substance = 'oxygen' THEN 'oxygen'
    WHEN substance = 'carbon_dioxide' THEN 'co2'
    WHEN substance = 'nitrogen' THEN 'nitrogen'
    WHEN substance = 'beer' THEN 'beer'
    ELSE 'altro_pipeline'
  END,
  'LineString',
  NULLIF(name, ''), NULLIF(operator, ''), substance, usage, diameter, pressure, tags, geom
FROM staging_pipeline;

-- ========== PETROLIO SITI ==========
INSERT INTO oim_feature (osm_id, osm_type, category_id, voce_id, geom_type, name, tags, geom)
SELECT osm_id, osm_type, 'petrolio', 'infrastrutture_petrolifere',
  CASE WHEN ST_GeometryType(geom) LIKE '%Point%' THEN 'Point' ELSE 'Polygon' END,
  NULLIF(name, ''), tags, geom
FROM staging_petroleum_site;

-- ========== ACQUA IMPIANTI ==========
INSERT INTO oim_feature (osm_id, osm_type, category_id, voce_id, geom_type, name, tags, geom)
SELECT osm_id, osm_type, 'acqua', 'impianto_trattamento_acque',
  CASE WHEN ST_GeometryType(geom) LIKE '%Point%' THEN 'Point' ELSE 'Polygon' END,
  NULLIF(name, ''), tags, geom
FROM staging_water_treatment;

INSERT INTO oim_feature (osm_id, osm_type, category_id, voce_id, geom_type, name, tags, geom)
SELECT osm_id, osm_type, 'acqua', 'impianto_depurazione',
  CASE WHEN ST_GeometryType(geom) LIKE '%Point%' THEN 'Point' ELSE 'Polygon' END,
  NULLIF(name, ''), tags, geom
FROM staging_wastewater_plant;

INSERT INTO oim_feature (osm_id, osm_type, category_id, voce_id, geom_type, name, substance, tags, geom)
SELECT osm_id, osm_type, 'acqua',
  CASE
    WHEN substance = 'water' THEN 'stazione_pompaggio_acque'
    WHEN substance = 'sewage' THEN 'stazione_pompaggio_reflui'
    ELSE 'stazione_pompaggio_altro'
  END,
  CASE WHEN ST_GeometryType(geom) LIKE '%Point%' THEN 'Point' ELSE 'Polygon' END,
  NULLIF(name, ''), substance, tags, geom
FROM staging_pumping_station;

ANALYZE oim_feature;

INSERT INTO meta(key, value) VALUES
  ('classified_at', now()::text),
  ('feature_count', (SELECT count(*)::text FROM oim_feature))
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
