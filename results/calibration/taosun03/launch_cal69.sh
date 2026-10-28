#!/bin/bash
# cal69. cal43's 50+50+650 W, which gave the lowest leading crest,
# with the feed raised to 28 mm/s. Scan 3 mm/s. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal69_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal69"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.028 \
    --beam-powers 50,50,650 \
    --end-time 0.40 --write-interval 0.10 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal69 "$CASE"
echo "CAL69_DONE"
