#!/bin/bash
# cal42. More wire into the cal08 heat. Feed 28 mm/s, scan 4 mm/s, section about 5.5 mm^2.
# One rank. Concurrent with the other taosun03 screens. Cap is 32 ranks.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal42_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal42"
tao_cal08_case "$CASE" \
    --end-time 0.32 --write-interval 0.16 --np "$NP" \
    --wire-feed-speed 0.028

tao_run "$NP" "$CASE"
tao_post cal42 "$CASE"
echo "CAL42_DONE"
