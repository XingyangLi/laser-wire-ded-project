#!/bin/bash
# cal35. Taller bulb. Half the scan speed, feed held near 18 mm/s so the
# steady section is about 7.1 mm^2, and more of the power is in the rear spot.
# Wire window stays cal08 (30/90): the angle sweep is cal32-cal34.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal35_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal35"
tao_cal08_case "$CASE" \
    --scan-speed 0.002 --wire-feed-speed 0.018 \
    --beam-powers 120,120,560 \
    --end-time 0.45 --write-interval 0.15 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal35 "$CASE"
echo "CAL35_DONE"
