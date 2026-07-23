# pysystemtrade adapter — OPS DESK bridge

Exports daily FX proxy prices from desk `cache/*.csv` (FRED legs) into
`cache/exports/pysystemtrade/` for systematic research with
[pysystemtrade](https://github.com/pst-group/pysystemtrade).

## What gets exported

For each pair in `config/fx_manifest.json` with a `cme_future` code:

| CME | Pair   | Desk source        |
|-----|--------|--------------------|
| 6E  | EURUSD | EUF / USD series   |
| 6J  | EURJPY | JPF cross          |
| 6B  | EURGBP | GBF cross          |
| 6M  | EURMXN | MXF cross          |
| …   | …      | …                  |

Files: `{CME}_daily_prices.csv` with columns `date,price`.

## Regenerate

```bash
cd "progetto stran"
python -m bridge.module_runner
# or full spine:
python scripts/spine_build.py
```

## Use with pysystemtrade

1. Clone [pst-group/pysystemtrade](https://github.com/pst-group/pysystemtrade)
2. Copy or symlink `cache/exports/pysystemtrade/*.csv` into your pysystemtrade
   data directory (see their `docs/data.md` for csv futures layout)
3. Map instrument codes in your system config (`6E`, `6J`, …)
4. Run carry / EWMAC rules from Carver's framework on the exported series

**Important:** These are **daily FRED/ECB proxies**, not exchange futures
prices. Use for signal research and pipeline wiring — not for claiming
live execution parity.

## Environment

Optional: set `PYSYSTEMTRADE_DATA` to your pysystemtrade data root when
copying exports via script.

## NautilusTrader

Same CSVs can be loaded as custom bars in
[NautilusTrader](https://github.com/nautechsystems/nautilus_trader) for
execution simulation; strategy logic remains external.
