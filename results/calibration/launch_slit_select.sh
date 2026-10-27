#!/bin/bash
# Corrected gas flux at the cavity, and a skin whose length is feed*tau.
# Both from a 0.1 mm film. 12 ranks each, nice 10, 6 ms.
#
#   cal70  q = 0.05 m/s at the gas-facing contact, no support pressure
#   cal71  skin on from t = 0 over 0.072 mm (18 mm/s * 4 ms)
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/slit_select.log) 2>&1
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

fail=0
echo "WAVE cal70 flux and cal71 oxide length"
GAS_PARALLEL=1 GAS_SKIP_BUILD=1 \
    GAS_TAG=cal70 GAS_P=0 GAS_Q=0.05 GAS_DEPTH=0.1 \
    GAS_PPM=300 GAS_FEED=0.020 \
    "$ROOT/results/calibration/launch_slit_gas.sh" &
p1=$!
OXIDE_PARALLEL=1 OXIDE_SKIP_BUILD=1 \
    OXIDE_TAG=cal71 OXIDE_TAU=0.004 OXIDE_FEED=0.018 \
    OXIDE_DEPTH=0.1 OXIDE_PPM=300 \
    "$ROOT/results/calibration/launch_slit_oxide_length.sh" &
p2=$!
wait "$p1" || fail=1
wait "$p2" || fail=1
echo "SELECT_DONE fail=$fail"
exit "$fail"
