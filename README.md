# terminal — energia & infrastruttura Italia

Workspace con pacchetti dati sotto `db/` (consumi, mercati, ENTSO-E, meteo, socio, impianti, OIM, Terna, …).

## Metadati

- Indice: `db/CATALOG.md` / `db/catalog.csv`
- Per pacchetto: `db/<nome>/METADATI.txt` + `catalog.csv`
- Rigenera: `python db/scripts/build_metadata_catalogs.py`

## Note sul repo

I file molto grandi (PBF OSM, GPKG, ZIP ARERA, merge meteo orari, patenti MIT, …) **non** sono in git (limite 100 MB / dimensione repo).

**Dump completo** (zip / parti): Release privata  
https://github.com/Lucertae/db-energia-italia/releases/tag/data-full-v1  

Istruzioni restore: asset `README_RELEASE.md` nella release.

**Non in repo né in release:** credenziali (`*.key`, `*.credentials`) e artefatti build Rust (`silice/target`).
