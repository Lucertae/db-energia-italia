# Moduli bridge — OPS DESK

Architettura plugin per collegare il desk C a stack quant open source.

## Layout

```
config/
  desk_spine.json      # serie + pipeline health
  fx_manifest.json     # coppie FX canoniche (base/quote)
  modules.json         # registry moduli abilitati
  reference_projects.json  # catalogo 30 progetti open source
  generated/           # output spine_codegen (non editare)

bridge/
  module_runner.py     # esecutore moduli
  spine_io.py          # lettura cache / ECB / FRED
  graph/
    fx_graph.py        # grafo + Bellman-Ford
    carry.py           # carry CIP + momentum
  weather/
    open_meteo.py      # ingestion JSON 15 zone
    hdd_cdd.py         # anomalie HDD/CDD → energia
    enso.py            # ONI → FX commodity
    signals.py         # PWR/FX/GAS segnali trading
  adapters/
    pysystemtrade/     # export CSV futures proxy
    herbie/            # NWP GRIB (stub)
    cdsapi/            # ERA5 (stub)
    atlite/            # CF profiles (stub)

cache/spine/modules/   # output JSON consumati da world_clocks.exe
cache/exports/         # export verso tool esterni
```

## Aggiungere un modulo

1. Crea `bridge/my_pkg/my_mod.py` con `def run(root: Path | None = None) -> dict`
2. Registra in `config/modules.json`:

```json
{
  "id": "my_mod",
  "enabled": true,
  "entry": "bridge.my_pkg.my_mod:run",
  "outputs": ["cache/spine/modules/my_mod.json"]
}
```

3. Esegui `python scripts/spine_build.py`
4. (Opzionale) Estendi `src/modules.c` per mostrare output in UI

## Contratto `run()`

Return dict minimo:

```python
{
  "ok": True,
  "module": "my_mod",
  "message": "human summary",
  "outputs": ["cache/spine/modules/my_mod.json"],
}
```

## Adapter esterni

Registry completo: `config/data_sources.json`, `config/reference_projects.json` e `docs/REFERENCE_PROJECTS.md`.

| Integrazione | Progetti |
|--------------|----------|
| **integrated** | pysystemtrade (export on), entsoe-py (harvest on) |
| **partial harvest** | World Monitor, GlobeOps, mkt, pftui, triphopp, OpenBB, OBSYD, OpenSanctions |
| **adapter off** | gridstatus, herbie, epftoolbox, findatapy, databento |
| **reference** | altri 20 — UI/pattern, vedi catalogo |

| ID | Settore | Repo | Stato moduli |
|----|---------|------|--------------|
| entsoe-py | energy | EnergieID/entsoe-py | `entsoe_py_harvest` on |
| gridstatus | energy | gridstatus/gridstatus | off |
| epftoolbox | energy | javieralbacete/epftoolbox | off |
| findatapy | fx | cuemacro/findatapy | off |
| databento | fx | databento/databento-python | off |
| pysystemtrade | fx | pst-group/pysystemtrade | export on |
| nautilus_trader | fx | nautechsystems/nautilus_trader | doc |
| weather_open_meteo | weather→energy/fx | open-meteo.com | **on** |
| weather_hdd_cdd | weather→energy | stdlib | **on** |
| weather_enso | weather→fx | NOAA CPC | **on** |
| weather_signals | weather→energy/fx | bridge | **on** |
| `backtest_pwr_signals` | Backtest PWR-02/PWR-01 → IC, hit rate, promotion gate | **ON** |

### Validazione segnali (prima di promuovere)

```
weather_* → backtest_pwr_signals → cache/spine/signals_candidate.json
                                      ↓ (solo se passed)
                              config/signals.json
```

Gate default: `|IC|≥0.04`, `hit≥52%`, `|t|≥1.96`, `n≥120`. Output in `cache/spine/modules/backtest_pwr_signals.json`.

| era5_harvest | weather→energy | ecmwf/cdsapi | off |
| atlite_profiles | weather→energy | PyPSA/atlite | off |

### Pipeline meteo → economia

```
open_meteo → hdd_cdd → enso → weather_signals → UI WEATHER + signals_live
```

Settore **energy:** segnali `PWR-*`, entsoe-py, epftoolbox (futuro).  
Settore **fx:** segnali `FX-ENSO`, `GAS-X`, export pysystemtrade.

Vedi `docs/STACK_WEATHER.md` per la catena NWP completa (Herbie, ERA5, zarr, quantili).

Gli adapter **non** girano nel processo C — scrivono `cache/exports/` e `cache/spine/modules/`.

## Grafo FX

Pesi: `-log(rate * (1 - fee))`. Ciclo negativo ⇒ prodotto tassi > 1 (dopo fee).

**Nota:** dati daily ECB/FRED — utile per research e regime, non arb eseguibile.
