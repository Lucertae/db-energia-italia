# entsoe-py adapter

Uses [entsoe-py](https://github.com/EnergieID/entsoe-py) when installed; falls back to
`scripts/desk_harvest/harvest_entsoe.py` (stdlib XML).

```bash
pip install entsoe-py pandas
set ENTSOE_API_TOKEN=...
python scripts/spine_build.py
```

Output: updates `cache/PDE.csv` etc. + `cache/spine/modules/entsoe_py_harvest.json`.
