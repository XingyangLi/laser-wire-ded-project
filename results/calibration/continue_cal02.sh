#!/bin/bash
# Continue cal02 from the latest time to 0.48 s. controlDict endTime is already 0.48
# and startFrom is latestTime. Do not rerun Allrun: that rebuilds the mesh.
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
CASE="$ROOT/cases/wire_cavity_cal02"
set +euo pipefail
# shellcheck disable=SC1091
source /usr/lib/openfoam/openfoam2406/etc/bashrc
set -euo pipefail
export PATH="${FOAM_USER_APPBIN}:$PATH"
cd "$CASE"
mpirun --use-hwthread-cpus -np 24 laserWireDEDFoam -parallel >> log.laserWireDEDFoam 2>&1
python3 "$ROOT/scripts/quantify_pores.py" --case "$CASE" || true
echo "CAL02B_DONE"
