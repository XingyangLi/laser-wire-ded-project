#!/bin/bash
# cal11. Continue the refined cal10 case from the written 0.40 s to 1.0 s.
# Same mesh, same 60/140 trailing window. 12 ranks, nice 10.
# Do not Allrun: that remeshes and wipes the restart.
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/cal11_launch.log) 2>&1
set -euo pipefail
CASE=/home/xingyang/laser-wire-ded-project/cases/wire_cavity_cal10
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
sed -i 's/endTime         0.4;/endTime         1.0;/' system/controlDict
grep -n 'endTime' system/controlDict
nproc_dirs=$(ls -d processor* | wc -l)
echo "processor dirs: $nproc_dirs"
test -d processor0/0.4
echo "RESTART_CAL11 from 0.4 to 1.0 on 12 ranks"
nice -n 10 mpirun --use-hwthread-cpus -np 12 laserWireDEDFoam -parallel >> log.laserWireDEDFoam 2>&1
echo "CAL11_DONE"
