#!/bin/bash
# cal62. cal36 made the tallest trailing crest (1.76 mm) with 100+100+700 W.
# This slows the scan to 2 mm/s at the same feed so that crest has more
# time to become a bulb. Plain 30/90 wire window, as in cal36. One rank.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal62_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal62"
tao_cal08_case "$CASE" \
    --scan-speed 0.002 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --end-time 0.60 --write-interval 0.20 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal62 "$CASE"
echo "CAL62_DONE"
