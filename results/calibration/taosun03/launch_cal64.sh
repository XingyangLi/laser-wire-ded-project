#!/bin/bash
# cal64. cal36's 100+100+700 W, but the rear spot is widened to 0.40 mm
# so the trail is heated as a patch rather than one cell layer.
# One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal64_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal64"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --beam-radii-each 0.26e-3,0.26e-3,0.40e-3 \
    --end-time 0.40 --write-interval 0.10 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal64 "$CASE"
echo "CAL64_DONE"
