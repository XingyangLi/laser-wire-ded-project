#!/bin/bash
# cal96. The 50+50+650 W split at scan 2 mm/s, feed lowered to 16 mm/s.
# Less wire on the recipe with the 0.54 mm leading crest. One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal96_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal96"
tao_cal08_case "$CASE" \
    --scan-speed 0.002 --wire-feed-speed 0.016 \
    --beam-powers 50,50,650 \
    --end-time 0.50 --write-interval 0.10 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal96 "$CASE"
echo "CAL96_DONE"
