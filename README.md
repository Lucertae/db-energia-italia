# terminal — energia & infrastruttura Italia

Workspace con pacchetti dati sotto `db/` (consumi, mercati, ENTSO-E, meteo, socio, impianti, OIM, Terna, …).

## Metadati

- Indice: `db/CATALOG.md` / `db/catalog.csv`
- Per pacchetto: `db/<nome>/METADATI.txt` + `catalog.csv`
- Rigenera: `python db/scripts/build_metadata_catalogs.py`

## Note sul repo

I file molto grandi (PBF OSM, GPKG, ZIP ARERA, merge meteo orari, patenti MIT, …) sono in `.gitignore` (limite GitHub 100 MB / dimensione repo). Restano in locale; si ripopolano con gli script di harvest.

**Non commitare** `*.key` / `*.credentials`.
