#!/bin/bash
# Continue cal03 from the latest time. endTime in system/controlDict is 0.70 s.
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
CASE="$ROOT/cases/wire_cavity_cal03"
set +euo pipefail
# shellcheck disable=SC1091
source /usr/lib/openfoam/openfoam2406/etc/bashrc
set -euo pipefail
export PATH="${FOAM_USER_APPBIN}:$PATH"
cd "$CASE"
mpirun --use-hwthread-cpus -np 24 laserWireDEDFoam -parallel >> log.laserWireDEDFoam 2>&1
python3 "$ROOT/scripts/quantify_pores.py" --case "$CASE" || true
echo "CAL03B_DONE"
