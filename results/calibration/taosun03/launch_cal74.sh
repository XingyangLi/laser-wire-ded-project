#!/bin/bash
# cal74. cal36's 100+100+700 W with the rear spot tightened to 0.18 mm.
# The wide 0.40 mm rear spot is cal64. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal74_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal74"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --beam-radii-each 0.26e-3,0.26e-3,0.18e-3 \
    --end-time 0.36 --write-interval 0.12 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal74 "$CASE"
echo "CAL74_DONE"
