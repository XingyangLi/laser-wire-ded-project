#!/bin/bash
# cal81. Slower scan with the front spots cut further: 40+40+560 W,
# scan 2 mm/s, feed 16 mm/s. Asks whether the leading crest falls below
# cal58's 1.15 mm. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal81_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal81"
tao_cal08_case "$CASE" \
    --scan-speed 0.002 --wire-feed-speed 0.016 \
    --beam-powers 40,40,560 \
    --end-time 0.45 --write-interval 0.15 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal81 "$CASE"
echo "CAL81_DONE"
