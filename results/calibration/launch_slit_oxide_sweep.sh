#!/bin/bash
# cal56 flags, two smokes at a time (12 ranks each, nice 10, 6 ms).
# Beams, Marangoni and recoil stay off. ppmRef stays 300, so the skin
# strength is min(ppm/300, 1).
#
#   cal57  50 ppm,  20 mm/s
#   cal58 100 ppm,  20 mm/s
#   cal59 200 ppm,  20 mm/s
#   cal60 300 ppm,  18 mm/s
#   cal61 300 ppm,  24 mm/s
#   cal62 300 ppm,  28 mm/s
#
# cal56 (300 ppm, 20 mm/s) is the benchmark and is not rerun.
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/slit_oxide_sweep.log) 2>&1
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
        OXIDE_TAG="$1" OXIDE_PPM="$2" OXIDE_FEED="$3" \
        "$ROOT/results/calibration/launch_slit_oxide.sh"
}

fail=0
wave() {
    echo "WAVE $1 $2 and $3 $4"
    run_one "$1" "$2" "$5" &
    local p1=$!
    run_one "$3" "$4" "$6" &
    local p2=$!
    wait "$p1" || fail=1
    wait "$p2" || fail=1
    echo "WAVE_DONE $1 $3 fail=$fail"
}

# tag ppm feed, tag ppm feed
wave cal57 50 cal58 100 0.020 0.020
wave cal59 200 cal60 300 0.020 0.018
wave cal61 300 cal62 300 0.024 0.028
echo "SWEEP_DONE fail=$fail"
exit "$fail"
