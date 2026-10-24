#!/bin/bash
# cal68. The 700 W rear spot with a faster feed, 32 mm/s, scan 3 mm/s.
# Extra wire on the power split that raised the trail. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal68_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal68"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.032 \
    --beam-powers 100,100,700 \
    --end-time 0.40 --write-interval 0.10 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal68 "$CASE"
echo "CAL68_DONE"
