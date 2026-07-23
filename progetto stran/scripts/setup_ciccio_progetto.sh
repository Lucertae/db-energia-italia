#!/bin/bash
# Full OPS DESK / progetto stran setup on ciccio10 (Linux harvest node).
set -euo pipefail
ROOT="${HOME}/lavoro/progetto stran"
DESK="${ROOT}/scripts/desk_harvest"
LIBERO="${ROOT}/scripts/libero"
CACHE="${ROOT}/cache"
mkdir -p "$CACHE"/{fred,ecb,crypto,stooq,eia,entsoe,portwatch,intel,spine,owid,electricity_market}
cd "$ROOT"
export PATH="${HOME}/.local/bin:${PATH}"
export DESK_ROOT="$ROOT"
export DESK_CACHE="$CACHE"
export LIBERO_DIR="$LIBERO"
export LIBERO_DB="${LIBERO}/libero.db"
export LIBERO_EXPORT="$CACHE"

PY=python3
if [ -f "${LIBERO}/venv/bin/python3" ]; then
  PY="${LIBERO}/venv/bin/python3"
fi
if ! ${PY} -c "import pandas" 2>/dev/null; then
  ${PY} -m pip install --user --break-system-packages -q -r "${ROOT}/research/requirements.txt" 2>/dev/null || true
  ${PY} -m pip install --user --break-system-packages -q -r "${LIBERO}/requirements.txt" 2>/dev/null || true
fi

echo "=== progetto stran setup $(date -Iseconds) ==="
echo "ROOT=$ROOT"
${PY} "${DESK}/harvest_all.py" 2>&1 | tee -a "${ROOT}/harvest_ciccio.log"
${PY} "${ROOT}/scripts/spine_build.py" 2>&1 | tee -a "${ROOT}/harvest_ciccio.log"
echo "=== done $(date -Iseconds) ==="
