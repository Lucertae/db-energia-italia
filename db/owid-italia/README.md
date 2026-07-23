# Our World in Data — Italia

Estratti **solo Italia** dalle repo dati OWID (approccio A). **~156 MB**.

## Refresh

```powershell
python db/owid-italia/scripts/harvest_all.py
```

Scheda: [`METADATI.txt`](METADATI.txt)

## Sorgenti

| Cartella | Contenuto |
|----------|-----------|
| `sources/energy-data/` | Energia Italia (+ codebook) |
| `sources/co2-data/` | CO₂ / GHG Italia |
| `sources/poverty-data/` | Povertà PIP Italia |
| `sources/covid-19-data/` | COVID Italia |
| `sources/energy-use-products/` | Uso energia prodotti (non per paese) |
| `sources/owid-datasets/` | `catalog.csv` + **363** CSV in `italy/` |

Legacy: `db/owid-energy-italia/` → `sources/energy-data/`.
