#!/bin/bash
# cal84. cal36's 100+100+700 W at a faster scan, 5 mm/s, feed 22 mm/s.
# The 3 mm/s pool recorded 56 pinch-offs and kept the wake open.
# This asks whether a quicker pass lets one of them freeze.
# One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal84_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal84"
tao_cal08_case "$CASE" \
    --scan-speed 0.005 --wire-feed-speed 0.022 \
    --beam-powers 100,100,700 \
    --end-time 0.32 --write-interval 0.08 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal84 "$CASE"
echo "CAL84_DONE"
