#!/bin/bash
# Setup libero DB pipeline on ciccio (Tailscale). Run once or after updates.
set -euo pipefail
LIBERO="${HOME}/lavoro/libero"
DESK_CACHE="${LIBERO}/export"
mkdir -p "$LIBERO" "$DESK_CACHE"
cd "$LIBERO"
export PATH="${HOME}/.local/bin:${PATH}"
PY=python3
if [ -f venv/bin/python3 ]; then
  PY=venv/bin/python3
else
  echo "using system python3"
  if ! ${PY} -c "import pandas" 2>/dev/null; then
    ${PY} -m pip install --user --break-system-packages -q -r requirements.txt
  fi
fi
export LIBERO_DB="${LIBERO}/libero.db"
export LIBERO_EXPORT="${DESK_CACHE}"
${PY} fetch_all.py all
echo "libero OK -> ${DESK_CACHE}"
