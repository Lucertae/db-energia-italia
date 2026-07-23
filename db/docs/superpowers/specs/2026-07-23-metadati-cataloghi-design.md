# Design — Metadati dataset db/*

**Date:** 2026-07-23  
**Status:** approved (user: procedi, opzione B)  
**Also:** delete `db/GAPS.md` and remove references.

## Goal

Every `*-italia` package (plus `imprese-energia-italia`) has:

1. `METADATI.txt` — human narrative: what / coverage / how much / refresh / license  
2. `catalog.csv` — one row per **logical dataset** with measured disk stats  

Plus `db/catalog.csv` global index.  
`GAPS.md` removed; known holes live in each package METADATI “Buchi noti”.

## Catalog columns

```
package,dataset,path,description,geo,time_start,time_end,granularity,rows_or_records,n_files,bytes,unit_notes,source,license,status
```

## Builder

`db/scripts/build_metadata_catalogs.py` — scans packages via dataset→glob map, measures bytes/files, samples CSV for rows/years when cheap, writes catalogs + regenerates `<!-- AUTO-STATS -->` blocks in METADATI.txt.
