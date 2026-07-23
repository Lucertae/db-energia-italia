# ENTSO-E Italia

Download Transparency Platform per l’Italia (paese + bidding zones + confini).

**Stato:** harvest lungo in corso / resume-safe. Snapshot tipico: centinaia di MB, migliaia di CSV.

## Avvio

```powershell
python db/entsoe-italia/scripts/harvest_all_italia.py
```

Chiave: `entsoe.key` (non versionare). Scheda: [`METADATI.txt`](METADATI.txt)

## Contenuto

- Zone: IT + North / Centre-North / Centre-South / South / Sicily / Sardinia / Calabria  
- Serie: load, generation, forecast wind/solar, capacity, hydro, unavailability, DA/ID prices (zone), imbalance, generation_per_plant  
- Confini: FR, CH, AT, SI, GR, MT, ME  
- Periodo: **2015 → oggi**

## Output

```
data/<zona>/<dataset>/<anno>.csv
logs/harvest_*.jsonl
```

CSV a **0 byte** = “no data” ENTSO (es. prezzi sul codice paese `IT`). I prezzi day-ahead stare sulle **zone**.

## Sicurezza

Se la API key è stata in chat, ruotala sul portale ENTSO-E.
