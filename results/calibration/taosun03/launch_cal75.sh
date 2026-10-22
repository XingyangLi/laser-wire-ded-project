#!/bin/bash
# cal75. cal36's 100+100+700 W with the rear aim raised to z = 0.70 mm.
# z = 0.35 mm is cal67; z = 0.95 mm on the cal08 beams flattened the crest.
# One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal75_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal75"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --beam-aim-heights 0.08e-3,0.08e-3,0.70e-3 \
    --end-time 0.36 --write-interval 0.12 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal75 "$CASE"
echo "CAL75_DONE"
