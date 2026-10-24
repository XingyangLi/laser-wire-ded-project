#!/bin/bash
# cal73. Same 750 W as cal43, shifted further rearward: 25+25+700 W.
# Scan 3 mm/s, feed 18 mm/s. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal73_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal73"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.018 \
    --beam-powers 25,25,700 \
    --end-time 0.40 --write-interval 0.10 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal73 "$CASE"
echo "CAL73_DONE"
