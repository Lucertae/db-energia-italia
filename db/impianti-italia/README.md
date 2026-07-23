# Impianti Italia

Anagrafica impianti / centrali da fonti complementari a OIM e GSE.

## Refresh

```powershell
python db/scripts/harvest_impianti_complementari.py
```

## Sorgenti

- `sources/wikidata/` — SPARQL centrali e asset power IT
- `sources/wri_gppd/` — WRI Global Power Plant Database (filter Italy)
- `sources/poweratlas/` — PowerAtlas Italy CSV
- `sources/gem/` — Global Energy Monitor (se scaricabile)
- `sources/osm/` — Overpass power=plant/generator
