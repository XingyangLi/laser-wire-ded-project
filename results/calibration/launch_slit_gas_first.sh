#!/bin/bash
# First gas-cavity pair, from a 0.1 mm painted film. 300 ppm, 20 mm/s.
# Oxide skin is off. Two jobs, 12 ranks each, nice 10, 6 ms.
#
#   cal68  5 kPa support, no gas flux
#   cal69  gas flux 5 mm/s at the triple line, no support pressure
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/slit_gas_first.log) 2>&1
set -u
ROOT=/home/xingyang/laser-wire-ded-project
set --
set +e
set +u
set +o pipefail
# shellcheck disable=SC1091
source /usr/lib/openfoam/openfoam2406/etc/bashrc
set -e
set -u
set -o pipefail
export PATH="${FOAM_USER_APPBIN}:$PATH"
hash -r
cd "$ROOT/solver"
./Allwmake
cd "$ROOT"

if ps -u xingyang -o cmd | grep -q '[l]aserWireDEDFoam'; then
    echo "a solver is already running" >&2
    exit 1
fi

run_one() {
    GAS_PARALLEL=1 GAS_SKIP_BUILD=1 \
        GAS_TAG="$1" GAS_P="$2" GAS_Q="$3" GAS_DEPTH=0.1 \
        GAS_PPM=300 GAS_FEED=0.020 \
        "$ROOT/results/calibration/launch_slit_gas.sh"
}

fail=0
echo "WAVE cal68 p=5000 and cal69 q=0.005"
run_one cal68 5000 0 &
p1=$!
run_one cal69 0 0.005 &
p2=$!
wait "$p1" || fail=1
wait "$p2" || fail=1
echo "GAS_FIRST_DONE fail=$fail"
exit "$fail"
