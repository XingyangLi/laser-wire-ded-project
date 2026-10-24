#!/bin/bash
# cal106. Plate 15/45, substrate absorptivity 0.60, preheat 700 K, scan 2 mm/s
# and feed 18 mm/s, powers 80+80+650 W, wire trail 30/100. The slower pass
# gives the plate time to melt while the notch window is kept. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal106_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal106"
tao_cal08_case "$CASE" \
    --scan-speed 0.002 --wire-feed-speed 0.018 \
    --beam-powers 80,80,650 \
    --absorptivity-substrate 0.60 \
    --preheat 700 \
    --end-time 0.45 --write-interval 0.10 --np "$NP" \
    --theta-receding 15 --theta-advancing 45 \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 30 --theta-advancing-wire-trail 100 \
    --wire-sector-half-angle 90 --wire-sector-blend 30
tao_run "$NP" "$CASE"
tao_post cal106 "$CASE"
echo "CAL106_DONE"
