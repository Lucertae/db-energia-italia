# OPS DESK — progetto stran

Cartella principale del software (ex root `terminal/`).

## Locale (Windows)

```bat
cd "progetto stran"
build.bat
run.bat
```

## Bridge modulare (Python)

Moduli research/adapter registrati in `config/modules.json`:

```bat
python scripts\spine_codegen.py
python scripts\spine_build.py
rem oppure:
scripts\bridge_build.bat
```

Output:
- `cache/spine/modules/fx_graph.json` — grafo FX + cicli Bellman-Ford
- `cache/spine/modules/fx_carry.json` — carry / momentum 63d
- `cache/exports/pysystemtrade/` — CSV per [pysystemtrade](https://github.com/pst-group/pysystemtrade)

Vedi `docs/STACK_OPEN_SOURCE.md`, **`docs/STACK_WEATHER.md`**, `docs/MODULES.md`, **`docs/REFERENCE_PROJECTS.md`** (catalogo 30 progetti).

## Deploy su ciccio10

```powershell
.\scripts\deploy_ciccio10.ps1
```

Percorso remoto: `~/lavoro/progetto stran` (symlink: `~/lavoro/progetto-stran`)

Log harvest remoto: `~/lavoro/progetto stran/nohup_setup.log`

## Sync cache da remoto (legacy desk)

```powershell
.\scripts\sync_desk.ps1
```
