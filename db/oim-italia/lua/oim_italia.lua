-- osm2pgsql flex style for Open Infrastructure Map filters (Italia)
-- Creates staging_* tables used by 03_classify.sql

local tables = {}

local function add_tags_json(attrs)
  local out = {}
  for k, v in pairs(attrs) do
    out[k] = v
  end
  return out
end

tables.power_line = osm2pgsql.define_table({
  name = 'staging_power_line',
  ids = { type = 'any', id_column = 'osm_id', type_column = 'osm_type' },
  columns = {
    { column = 'power', type = 'text' },
    { column = 'voltage', type = 'text' },
    { column = 'frequency', type = 'text' },
    { column = 'location', type = 'text' },
    { column = 'tunnel', type = 'text' },
    { column = 'name', type = 'text' },
    { column = 'operator', type = 'text' },
    { column = 'ref', type = 'text' },
    { column = 'tags', type = 'jsonb' },
    { column = 'geom', type = 'linestring', projection = 4326, not_null = true },
  }
})

tables.power_plant = osm2pgsql.define_table({
  name = 'staging_power_plant',
  ids = { type = 'any', id_column = 'osm_id', type_column = 'osm_type' },
  columns = {
    { column = 'plant_source', type = 'text' },
    { column = 'name', type = 'text' },
    { column = 'operator', type = 'text' },
    { column = 'tags', type = 'jsonb' },
    { column = 'geom', type = 'geometry', projection = 4326, not_null = true },
  }
})

tables.power_generator = osm2pgsql.define_table({
  name = 'staging_power_generator',
  ids = { type = 'any', id_column = 'osm_id', type_column = 'osm_type' },
  columns = {
    { column = 'generator_source', type = 'text' },
    { column = 'name', type = 'text' },
    { column = 'operator', type = 'text' },
    { column = 'tags', type = 'jsonb' },
    { column = 'geom', type = 'geometry', projection = 4326, not_null = true },
  }
})

tables.power_support = osm2pgsql.define_table({
  name = 'staging_power_support',
  ids = { type = 'any', id_column = 'osm_id', type_column = 'osm_type' },
  columns = {
    { column = 'power', type = 'text' },
    { column = 'transition', type = 'bool' },
    { column = 'name', type = 'text' },
    { column = 'ref', type = 'text' },
    { column = 'tags', type = 'jsonb' },
    { column = 'geom', type = 'geometry', projection = 4326, not_null = true },
  }
})

tables.power_switchgear = osm2pgsql.define_table({
  name = 'staging_power_switchgear',
  ids = { type = 'any', id_column = 'osm_id', type_column = 'osm_type' },
  columns = {
    { column = 'power', type = 'text' },
    { column = 'power_type', type = 'text' },
    { column = 'switch', type = 'text' },
    { column = 'transformer_type', type = 'text' },
    { column = 'compensator', type = 'text' },
    { column = 'substation', type = 'text' },
    { column = 'windings', type = 'text' },
    { column = 'voltage', type = 'text' },
    { column = 'voltage_tertiary', type = 'text' },
    { column = 'name', type = 'text' },
    { column = 'tags', type = 'jsonb' },
    { column = 'geom', type = 'geometry', projection = 4326, not_null = true },
  }
})

tables.telecom_cable = osm2pgsql.define_table({
  name = 'staging_telecom_cable',
  ids = { type = 'any', id_column = 'osm_id', type_column = 'osm_type' },
  columns = {
    { column = 'name', type = 'text' },
    { column = 'operator', type = 'text' },
    { column = 'tags', type = 'jsonb' },
    { column = 'geom', type = 'linestring', projection = 4326, not_null = true },
  }
})

tables.telecom_mast = osm2pgsql.define_table({
  name = 'staging_telecom_mast',
  ids = { type = 'any', id_column = 'osm_id', type_column = 'osm_type' },
  columns = {
    { column = 'name', type = 'text' },
    { column = 'operator', type = 'text' },
    { column = 'tags', type = 'jsonb' },
    { column = 'geom', type = 'geometry', projection = 4326, not_null = true },
  }
})

tables.telecom_building = osm2pgsql.define_table({
  name = 'staging_telecom_building',
  ids = { type = 'any', id_column = 'osm_id', type_column = 'osm_type' },
  columns = {
    { column = 'kind', type = 'text' },
    { column = 'name', type = 'text' },
    { column = 'operator', type = 'text' },
    { column = 'tags', type = 'jsonb' },
    { column = 'geom', type = 'geometry', projection = 4326, not_null = true },
  }
})

tables.telecom_cabinet = osm2pgsql.define_table({
  name = 'staging_telecom_cabinet',
  ids = { type = 'any', id_column = 'osm_id', type_column = 'osm_type' },
  columns = {
    { column = 'name', type = 'text' },
    { column = 'operator', type = 'text' },
    { column = 'tags', type = 'jsonb' },
    { column = 'geom', type = 'geometry', projection = 4326, not_null = true },
  }
})

tables.pipeline = osm2pgsql.define_table({
  name = 'staging_pipeline',
  ids = { type = 'any', id_column = 'osm_id', type_column = 'osm_type' },
  columns = {
    { column = 'substance', type = 'text' },
    { column = 'usage', type = 'text' },
    { column = 'diameter', type = 'real' },
    { column = 'pressure', type = 'text' },
    { column = 'name', type = 'text' },
    { column = 'operator', type = 'text' },
    { column = 'tags', type = 'jsonb' },
    { column = 'geom', type = 'linestring', projection = 4326, not_null = true },
  }
})

tables.petroleum_site = osm2pgsql.define_table({
  name = 'staging_petroleum_site',
  ids = { type = 'any', id_column = 'osm_id', type_column = 'osm_type' },
  columns = {
    { column = 'name', type = 'text' },
    { column = 'tags', type = 'jsonb' },
    { column = 'geom', type = 'geometry', projection = 4326, not_null = true },
  }
})

tables.water_treatment = osm2pgsql.define_table({
  name = 'staging_water_treatment',
  ids = { type = 'any', id_column = 'osm_id', type_column = 'osm_type' },
  columns = {
    { column = 'name', type = 'text' },
    { column = 'tags', type = 'jsonb' },
    { column = 'geom', type = 'geometry', projection = 4326, not_null = true },
  }
})

tables.wastewater_plant = osm2pgsql.define_table({
  name = 'staging_wastewater_plant',
  ids = { type = 'any', id_column = 'osm_id', type_column = 'osm_type' },
  columns = {
    { column = 'name', type = 'text' },
    { column = 'tags', type = 'jsonb' },
    { column = 'geom', type = 'geometry', projection = 4326, not_null = true },
  }
})

tables.pumping_station = osm2pgsql.define_table({
  name = 'staging_pumping_station',
  ids = { type = 'any', id_column = 'osm_id', type_column = 'osm_type' },
  columns = {
    { column = 'substance', type = 'text' },
    { column = 'name', type = 'text' },
    { column = 'tags', type = 'jsonb' },
    { column = 'geom', type = 'geometry', projection = 4326, not_null = true },
  }
})

local power_line_values = { line = true, minor_line = true, cable = true, minor_cable = true }
local power_support_values = { tower = true, pole = true, portal = true }
local power_switch_values = {
  switch = true, transformer = true, compensator = true, converter = true
}
local petroleum_industrial = {
  oil = true, fracking = true, oil_storage = true, petroleum_terminal = true,
  hydrocarbons = true, ['oil sands'] = true, oil_sands = true, gas = true,
  gas_storage = true, natural_gas = true, wellsite = true, well_cluster = true,
  refinery = true
}

local function insert_geom(table_obj, object, cols, prefer)
  if object.is_closed and (prefer == 'area' or prefer == 'any') and object:as_polygon() then
    cols.geom = object:as_polygon()
    table_obj:insert(cols)
    return
  end
  if prefer == 'line' or prefer == 'any' then
    local g = object:as_linestring()
    if g then
      cols.geom = g
      table_obj:insert(cols)
    end
  elseif prefer == 'point' then
    -- handled separately for nodes
  end
end

function osm2pgsql.process_node(object)
  local t = object.tags

  if t.power and power_support_values[t.power] then
    tables.power_support:insert({
      power = t.power,
      transition = (t['location:transition'] == 'yes'),
      name = t.name,
      ref = t.ref,
      tags = add_tags_json(t),
      geom = object:as_point()
    })
  end

  if t.power and power_switch_values[t.power] then
    tables.power_switchgear:insert({
      power = t.power,
      power_type = t.compensator or t.transformer or t.power,
      switch = t.switch,
      transformer_type = t.transformer,
      compensator = t.compensator,
      substation = t.substation,
      windings = t.windings,
      voltage = t.voltage,
      voltage_tertiary = t['voltage:tertiary'] or t.voltage_tertiary,
      name = t.name,
      tags = add_tags_json(t),
      geom = object:as_point()
    })
  end

  if t.power == 'substation' and t.substation == 'converter' then
    tables.power_switchgear:insert({
      power = 'converter',
      power_type = 'converter',
      substation = 'converter',
      voltage = t.voltage,
      name = t.name,
      tags = add_tags_json(t),
      geom = object:as_point()
    })
  end

  if t.power == 'generator' then
    tables.power_generator:insert({
      generator_source = t['generator:source'],
      name = t.name,
      operator = t.operator,
      tags = add_tags_json(t),
      geom = object:as_point()
    })
  end

  if t.power == 'plant' then
    tables.power_plant:insert({
      plant_source = t['plant:source'],
      name = t.name,
      operator = t.operator,
      tags = add_tags_json(t),
      geom = object:as_point()
    })
  end

  if (t.man_made == 'mast' or t.man_made == 'tower' or t.man_made == 'communications_tower'
      or t['tower:type'] == 'communication') then
    tables.telecom_mast:insert({
      name = t.name,
      operator = t.operator,
      tags = add_tags_json(t),
      geom = object:as_point()
    })
  end

  local telecom_kind = t.telecom or t.building or t.office or t.man_made
  if telecom_kind == 'data_center' or telecom_kind == 'data_centre'
     or telecom_kind == 'telephone_exchange' or telecom_kind == 'central_office'
     or telecom_kind == 'exchange' or telecom_kind == 'telecommunication'
     or telecom_kind == 'telephone_office' then
    tables.telecom_building:insert({
      kind = telecom_kind,
      name = t.name,
      operator = t.operator,
      tags = add_tags_json(t),
      geom = object:as_point()
    })
  end

  if t.man_made == 'street_cabinet' then
    tables.telecom_cabinet:insert({
      name = t.name,
      operator = t.operator,
      tags = add_tags_json(t),
      geom = object:as_point()
    })
  end

  if t.industrial and petroleum_industrial[t.industrial] then
    tables.petroleum_site:insert({
      name = t.name,
      tags = add_tags_json(t),
      geom = object:as_point()
    })
  end
  if t.man_made == 'petroleum_well' or t.man_made == 'oil_well' or t.man_made == 'offshore_platform' then
    tables.petroleum_site:insert({
      name = t.name,
      tags = add_tags_json(t),
      geom = object:as_point()
    })
  end

  if t.man_made == 'water_works' or t.man_made == 'desalination_plant' then
    tables.water_treatment:insert({ name = t.name, tags = add_tags_json(t), geom = object:as_point() })
  end
  if t.man_made == 'wastewater_plant' then
    tables.wastewater_plant:insert({ name = t.name, tags = add_tags_json(t), geom = object:as_point() })
  end
  if t.man_made == 'pumping_station' then
    tables.pumping_station:insert({
      substance = t.substance or t.pumping_station,
      name = t.name,
      tags = add_tags_json(t),
      geom = object:as_point()
    })
  end
end

function osm2pgsql.process_way(object)
  local t = object.tags

  if t.power and power_line_values[t.power] then
    local g = object:as_linestring()
    if g then
      tables.power_line:insert({
        power = t.power,
        voltage = t.voltage,
        frequency = t.frequency,
        location = t.location,
        tunnel = t.tunnel,
        name = t.name,
        operator = t.operator,
        ref = t.ref,
        tags = add_tags_json(t),
        geom = g
      })
    end
  end

  if t.power and power_support_values[t.power] then
    insert_geom(tables.power_support, object, {
      power = t.power,
      transition = (t['location:transition'] == 'yes'),
      name = t.name,
      ref = t.ref,
      tags = add_tags_json(t),
    }, object.is_closed and 'area' or 'line')
  end

  if t.power and power_switch_values[t.power] then
    local cols = {
      power = t.power,
      power_type = t.compensator or t.transformer or t.power,
      switch = t.switch,
      transformer_type = t.transformer,
      compensator = t.compensator,
      substation = t.substation,
      windings = t.windings,
      voltage = t.voltage,
      voltage_tertiary = t['voltage:tertiary'],
      name = t.name,
      tags = add_tags_json(t),
    }
    if object.is_closed then
      cols.geom = object:as_polygon()
      if cols.geom then tables.power_switchgear:insert(cols) end
    else
      -- skip open ways for switchgear
    end
  end

  if t.power == 'substation' and t.substation == 'converter' and object.is_closed then
    local g = object:as_polygon()
    if g then
      tables.power_switchgear:insert({
        power = 'converter', power_type = 'converter', substation = 'converter',
        voltage = t.voltage, name = t.name, tags = add_tags_json(t), geom = g
      })
    end
  end

  if t.power == 'plant' and object.is_closed then
    local g = object:as_polygon()
    if g then
      tables.power_plant:insert({
        plant_source = t['plant:source'], name = t.name, operator = t.operator,
        tags = add_tags_json(t), geom = g
      })
    end
  end

  if t.power == 'generator' then
    if object.is_closed then
      local g = object:as_polygon()
      if g then
        tables.power_generator:insert({
          generator_source = t['generator:source'], name = t.name, operator = t.operator,
          tags = add_tags_json(t), geom = g
        })
      end
    end
  end

  if t.communication == 'line' or t.communication == 'cable' then
    local g = object:as_linestring()
    if g then
      tables.telecom_cable:insert({
        name = t.name, operator = t.operator, tags = add_tags_json(t), geom = g
      })
    end
  end

  if (t.man_made == 'mast' or t.man_made == 'tower' or t.man_made == 'communications_tower'
      or t['tower:type'] == 'communication') and object.is_closed then
    local g = object:as_polygon()
    if g then
      tables.telecom_mast:insert({
        name = t.name, operator = t.operator, tags = add_tags_json(t), geom = g
      })
    end
  end

  local telecom_kind = t.telecom or t.building or t.office or t.man_made
  if object.is_closed and (telecom_kind == 'data_center' or telecom_kind == 'data_centre'
     or telecom_kind == 'telephone_exchange' or telecom_kind == 'central_office'
     or telecom_kind == 'exchange' or telecom_kind == 'telecommunication'
     or telecom_kind == 'telephone_office') then
    local g = object:as_polygon()
    if g then
      tables.telecom_building:insert({
        kind = telecom_kind, name = t.name, operator = t.operator,
        tags = add_tags_json(t), geom = g
      })
    end
  end

  if t.man_made == 'street_cabinet' and object.is_closed then
    local g = object:as_polygon()
    if g then
      tables.telecom_cabinet:insert({
        name = t.name, operator = t.operator, tags = add_tags_json(t), geom = g
      })
    end
  end

  if t.man_made == 'pipeline' or t['construction:man_made'] == 'pipeline' then
    local g = object:as_linestring()
    if g then
      local diam = nil
      if t.diameter then
        diam = tonumber((t.diameter:gsub('[^0-9%.]', '')))
      end
      tables.pipeline:insert({
        substance = t.substance,
        usage = t.usage,
        diameter = diam,
        pressure = t.pressure,
        name = t.name,
        operator = t.operator,
        tags = add_tags_json(t),
        geom = g
      })
    end
  end

  if t.waterway == 'pressurised' then
    local g = object:as_linestring()
    if g then
      tables.pipeline:insert({
        substance = t.substance or 'water',
        usage = t.usage,
        name = t.name,
        operator = t.operator,
        tags = add_tags_json(t),
        geom = g
      })
    end
  end

  if object.is_closed and t.industrial and petroleum_industrial[t.industrial] then
    local g = object:as_polygon()
    if g then
      tables.petroleum_site:insert({ name = t.name, tags = add_tags_json(t), geom = g })
    end
  end
  if object.is_closed and (t.man_made == 'offshore_platform' or t.pipeline == 'substation') then
    local g = object:as_polygon()
    if g then
      tables.petroleum_site:insert({ name = t.name, tags = add_tags_json(t), geom = g })
    end
  end

  if object.is_closed and (t.man_made == 'water_works' or t.man_made == 'desalination_plant') then
    local g = object:as_polygon()
    if g then tables.water_treatment:insert({ name = t.name, tags = add_tags_json(t), geom = g }) end
  end
  if object.is_closed and t.man_made == 'wastewater_plant' then
    local g = object:as_polygon()
    if g then tables.wastewater_plant:insert({ name = t.name, tags = add_tags_json(t), geom = g }) end
  end
  if object.is_closed and t.man_made == 'pumping_station' then
    local g = object:as_polygon()
    if g then
      tables.pumping_station:insert({
        substance = t.substance or t.pumping_station,
        name = t.name, tags = add_tags_json(t), geom = g
      })
    end
  end
end

function osm2pgsql.process_relation(object)
  local t = object.tags
  if t.type ~= 'multipolygon' and t.type ~= 'site' and t.route ~= 'power' then
    return
  end

  if t.power == 'plant' then
    local g = object:as_multipolygon()
    if g then
      tables.power_plant:insert({
        plant_source = t['plant:source'], name = t.name, operator = t.operator,
        tags = add_tags_json(t), geom = g
      })
    end
  end

  if t.power == 'generator' then
    local g = object:as_multipolygon()
    if g then
      tables.power_generator:insert({
        generator_source = t['generator:source'], name = t.name, operator = t.operator,
        tags = add_tags_json(t), geom = g
      })
    end
  end

  if t.route == 'power' or t.power == 'circuit' then
    -- circuit relations: members imported as ways already; skip duplicate
  end

  if t.man_made == 'pipeline' then
    -- skip; ways already covered
  end

  local telecom_kind = t.telecom or t.building
  if telecom_kind == 'data_center' or telecom_kind == 'data_centre'
     or telecom_kind == 'telephone_exchange' or telecom_kind == 'exchange' then
    local g = object:as_multipolygon()
    if g then
      tables.telecom_building:insert({
        kind = telecom_kind, name = t.name, operator = t.operator,
        tags = add_tags_json(t), geom = g
      })
    end
  end

  if t.industrial and petroleum_industrial[t.industrial] then
    local g = object:as_multipolygon()
    if g then tables.petroleum_site:insert({ name = t.name, tags = add_tags_json(t), geom = g }) end
  end

  if t.man_made == 'water_works' or t.man_made == 'desalination_plant' then
    local g = object:as_multipolygon()
    if g then tables.water_treatment:insert({ name = t.name, tags = add_tags_json(t), geom = g }) end
  end
  if t.man_made == 'wastewater_plant' then
    local g = object:as_multipolygon()
    if g then tables.wastewater_plant:insert({ name = t.name, tags = add_tags_json(t), geom = g }) end
  end
  if t.man_made == 'pumping_station' then
    local g = object:as_multipolygon()
    if g then
      tables.pumping_station:insert({
        substance = t.substance or t.pumping_station,
        name = t.name, tags = add_tags_json(t), geom = g
      })
    end
  end
end
