#!/bin/bash
# cal97. Rear spot 600 W, fronts 50 W, scan 2 mm/s, feed 18 mm/s.
# Cooler than cal72, to see whether the wake can close. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal97_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal97"
tao_cal08_case "$CASE" \
    --scan-speed 0.002 --wire-feed-speed 0.018 \
    --beam-powers 50,50,600 \
    --end-time 0.50 --write-interval 0.10 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal97 "$CASE"
echo "CAL97_DONE"
