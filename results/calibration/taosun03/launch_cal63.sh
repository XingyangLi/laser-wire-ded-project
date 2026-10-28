#!/bin/bash
# cal63. cal36 (100+100+700 W, scan 3 mm/s, feed 20 mm/s, wire window 30/90)
# on the wire box refined twice in x and y. Not cal10: that refined run is
# the 60/140 window on TaoSun-01. One rank. z stays coarse.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal63_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal63"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --end-time 0.25 --write-interval 0.10 --np "$NP" \
    --wire-refine 2
tao_run "$NP" "$CASE"
tao_post cal63 "$CASE"
echo "CAL63_DONE"
