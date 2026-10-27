#!/bin/bash
# Bare neck, 8 ms, 12 ranks each.
#   cal74  surface skin, wire 140/40, laser and Marangoni off
#   cal75  the same skin, with Marangoni and recoil on
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/slit_bare_first.log) 2>&1
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
echo "WAVE cal74 surface and cal75 flow"
BARE_PARALLEL=1 BARE_SKIP_BUILD=1 BARE_TAG=cal74 BARE_MODE=surface \
    "$ROOT/results/calibration/launch_slit_bare.sh" &
p1=$!
BARE_PARALLEL=1 BARE_SKIP_BUILD=1 BARE_TAG=cal75 BARE_MODE=flow \
    "$ROOT/results/calibration/launch_slit_bare.sh" &
p2=$!
wait "$p1" || fail=1
wait "$p2" || fail=1
echo "BARE_FIRST_DONE fail=$fail"
exit "$fail"
