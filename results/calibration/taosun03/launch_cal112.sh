#!/bin/bash
# cal112. cal109 heat (plate 20/55, absorptivity 0.60, preheat 800 K,
# fronts 180 W, rear 700 W) with the 15/50 trailing pin over 60 deg of +x.
# One rank, nice 10, to 0.60 s.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal112_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal112"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 180,180,700 \
    --absorptivity-substrate 0.60 \
    --preheat 800 \
    --end-time 0.60 --write-interval 0.10 --np "$NP" \
    --theta-receding 20 --theta-advancing 55 \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 15 --theta-advancing-wire-trail 50 \
    --wire-sector-half-angle 60 --wire-sector-blend 20
tao_run "$NP" "$CASE"
tao_post cal112 "$CASE"
echo "CAL112_DONE"
