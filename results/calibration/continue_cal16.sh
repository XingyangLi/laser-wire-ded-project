#!/bin/bash
# cal16 was killed at t = 0.438 s on 24 Oct 2026. The last written field is
# 0.40 s. A 0.15 mm liquid-shelled pore was still in the pool at 0.433 s.
# Restart that field to 0.70 s. Same 500 ppm sigma, same 10/40 plate window,
# same 60/140 trailing window. Do not Allrun: that remeshes and wipes the
# restart. Do not rebuild first: this continuation uses the binary that wrote
# 0.40 s. Twelve ranks, nice 10.
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/cal16_launch.log) 2>&1
set -euo pipefail
CASE=/home/xingyang/laser-wire-ded-project/cases/wire_cavity_cal16
if ps -u xingyang -o cmd | grep -q '[l]aserWireDEDFoam'; then
    echo "a solver is already running" >&2
    exit 1
fi
set +euo pipefail
# shellcheck disable=SC1091
source /usr/lib/openfoam/openfoam2406/etc/bashrc
set -euo pipefail
export PATH="${FOAM_USER_APPBIN}:$PATH"
hash -r
cd "$CASE"
test -d processor0/0.4
test -d processor11/0.4
foamDictionary system/controlDict -entry endTime -set 0.7 > /dev/null
grep -n 'endTime' system/controlDict
nproc_dirs=$(ls -d processor* | wc -l)
echo "processor dirs: $nproc_dirs"
echo "RESTART_CAL16 from 0.4 to 0.7 on 12 ranks"
nice -n 10 mpirun --use-hwthread-cpus -np 12 laserWireDEDFoam -parallel >> log.laserWireDEDFoam 2>&1
python3 /home/xingyang/laser-wire-ded-project/scripts/quantify_pores.py --case "$CASE" || true
echo "CAL16_DONE"
