# OWID Italia — Design (approccio A)

## Goal

Offline Italy-only extract from all OWID public *data* repos with country-level series, plus product-level energy-use dataset.

## Sources

| Source | Global kept? | Italy extract |
|--------|--------------|---------------|
| energy-data | codebook + optional full CSV | yes |
| co2-data | codebook | yes |
| poverty-data | codebook | yes |
| covid-19-data | codebook | yes (main `owid-covid-data.csv`) |
| energy-use-products | full (no country) | n/a — copy as-is |
| owid-datasets (~766) | no | one CSV per dataset with Italy rows + `catalog.csv` |

## Layout

`db/owid-italia/sources/<repo>/…` + `scripts/harvest_all.py`

## Filter

Case-insensitive match on columns: `country`, `entity`, `location`, `nation` (and title-case variants) equals `italy`.
