#!/bin/bash
# Growing oxide skin, painted-depth check. Two smokes at a time
# (12 ranks each, nice 10, 6 ms). 300 ppm, feed 20 mm/s.
# Coverage starts at 0 and grows with oxygen and feed.
#
#   cal63  0.1 mm painted film
#   cal64  0 mm, wetted neck (no film, no groove)
#   cal65  0.3 mm
#   cal66  0.5 mm
#   cal67  0.75 mm
#
# The ppm/feed table is a later step, and only if these depths do not
# simply follow the paint.
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/slit_oxide_depth.log) 2>&1
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
    OXIDE_PARALLEL=1 OXIDE_SKIP_BUILD=1 \
        OXIDE_TAG="$1" OXIDE_PPM=300 OXIDE_FEED=0.020 OXIDE_DEPTH="$2" \
        "$ROOT/results/calibration/launch_slit_oxide.sh"
}

fail=0
wave() {
    echo "WAVE $1 depth $2 mm and $3 depth $4 mm"
    run_one "$1" "$2" &
    local p1=$!
    run_one "$3" "$4" &
    local p2=$!
    wait "$p1" || fail=1
    wait "$p2" || fail=1
    echo "WAVE_DONE $1 $3 fail=$fail"
}

wave cal63 0.1 cal64 0
wave cal65 0.3 cal66 0.5
echo "WAVE cal67 depth 0.75 mm"
run_one cal67 0.75 || fail=1
echo "DEPTH_DONE fail=$fail"
exit "$fail"
