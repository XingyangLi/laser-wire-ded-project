#!/bin/bash
# Mesh and run the short single-wire demo (pinning + porosity), then summarise.
# OpenFOAM.com v2406+ must be installed. Usage: ./scripts/run_single_wire_demo.sh [case_dir]
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CASE="${1:-$ROOT/cases/single_wire_demo}"
if [ -z "${WM_PROJECT_DIR:-}" ]; then
    if [ -f /usr/lib/openfoam/openfoam2406/etc/bashrc ]; then
        # shellcheck disable=SC1091
        source /usr/lib/openfoam/openfoam2406/etc/bashrc
    elif [ -f /usr/lib/openfoam/openfoam2412/etc/bashrc ]; then
        # shellcheck disable=SC1091
        source /usr/lib/openfoam/openfoam2412/etc/bashrc
    else
        echo "OpenFOAM bashrc not found. Source openfoam2406 or openfoam2412 first." >&2
        exit 1
    fi
fi
if ! command -v laserWireDEDFoam >/dev/null 2>&1; then
    echo "laserWireDEDFoam is not on PATH. From the repo: cd solver && ./Allwmake" >&2
    exit 1
fi
cd "$CASE"
./Allclean >/dev/null 2>&1 || true
./Allrun 1
python3 "$ROOT/scripts/quantify_pores.py" --case "$CASE" --expect-demo
