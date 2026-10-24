#!/bin/bash
# cal36. More power into the wire. Rear spot 700 W, front spots only 100 W,
# scan 3 mm/s, feed 20 mm/s (steady section about 5.2 mm^2).
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal36_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal36"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --end-time 0.36 --write-interval 0.12 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal36 "$CASE"
echo "CAL36_DONE"
