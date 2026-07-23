#!/bin/bash
# Refresh external bulk datasets on ciccio10 (no git required).
set -euo pipefail
ROOT="${HOME}/lavoro"
OWID="${ROOT}/owid-energy-data"
MKT="${ROOT}/datasets/electricity_market"
mkdir -p "$OWID" "$MKT"
BASE="https://raw.githubusercontent.com/owid/energy-data/master"
curl -fsSL -o "${OWID}/owid-energy-data.csv" "${BASE}/owid-energy-data.csv"
curl -fsSL -o "${OWID}/owid-energy-codebook.csv" "${BASE}/owid-energy-codebook.csv"
curl -fsSL -o "${OWID}/README.md" "${BASE}/README.md"
echo "OWID ok -> ${OWID} ($(du -sh "${OWID}/owid-energy-data.csv" | cut -f1))"
if [ -f "${ROOT}/datasets/archive.zip" ]; then
  unzip -o "${ROOT}/datasets/archive.zip" -d "${ROOT}/datasets/electricity_market"
  echo "electricity_market ok -> ${MKT}"
fi
