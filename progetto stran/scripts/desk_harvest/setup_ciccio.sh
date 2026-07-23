#!/bin/bash
# Setup desk harvest on ciccio10. Run after deploy from sync_desk.ps1
set -euo pipefail
DESK="${HOME}/lavoro/desk"
LIBERO="${HOME}/lavoro/libero"
CACHE="${DESK}/cache"
mkdir -p "$DESK" "$CACHE" "$CACHE/fred" "$CACHE/ecb" "$CACHE/crypto" "$CACHE/stooq" "$CACHE/eia"
cd "$DESK"
export PATH="${HOME}/.local/bin:${PATH}"
export DESK_ROOT="$DESK"
export DESK_CACHE="$CACHE"
export LIBERO_DIR="$LIBERO"
export LIBERO_DB="${LIBERO}/libero.db"
export LIBERO_EXPORT="${CACHE}"

PY=python3
if [ -f "${LIBERO}/venv/bin/python3" ]; then
  PY="${LIBERO}/venv/bin/python3"
elif ! ${PY} -c "import pandas" 2>/dev/null; then
  ${PY} -m pip install --user --break-system-packages -q -r "${LIBERO}/requirements.txt" 2>/dev/null || true
fi

echo "desk harvest start $(date -Iseconds)"
${PY} harvest_all.py 2>&1 | tee -a harvest.log
echo "desk harvest done $(date -Iseconds)"
