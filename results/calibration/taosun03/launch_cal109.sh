#!/bin/bash
# cal109. Plate 20/55 with the hotter plate from cal105: absorptivity 0.60,
# preheat 800 K, front spots 180 W, rear spot 700 W, wire trail 30/100.
# One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal109_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal109"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 180,180,700 \
    --absorptivity-substrate 0.60 \
    --preheat 800 \
    --end-time 0.40 --write-interval 0.10 --np "$NP" \
    --theta-receding 20 --theta-advancing 55 \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 30 --theta-advancing-wire-trail 100 \
    --wire-sector-half-angle 90 --wire-sector-blend 30
tao_run "$NP" "$CASE"
tao_post cal109 "$CASE"
echo "CAL109_DONE"
