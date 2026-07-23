# findatapy (Cuemacro / Saeed Amen)

FX-native unified download: Bloomberg, Eikon, FRED/ALFRED, Dukascopy tick, Quandl, Yahoo.
Storage: ArcticDB, Parquet chunked.

## Install

```bash
pip install findatapy
# optional storage:
pip install arcticdb
```

## Role in OPS DESK

| Layer | Tool |
|-------|------|
| Ingestion | findatapy |
| Event studies | finmarketpy (same author) |
| Storage | ArcticDB on `cache/arctic/` or S3 |

## Enable

1. `pip install findatapy`
2. Set API keys per vendor in env or `bridge/adapters/findatapy/config.yaml`
3. Enable module `findatapy_harvest` in `config/modules.json`

Desk exports FRED daily today; findatapy replaces ad-hoc harvest for **intraday** and **multi-vendor** when you add keys.

Reference: [findatapy](https://github.com/cuemacro/findatapy)
