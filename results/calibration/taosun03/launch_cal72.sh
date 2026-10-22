#!/bin/bash
# cal72. The 50+50+650 W split at the slow scan that built the tall crest.
# Scan 2 mm/s, feed 18 mm/s (same section as cal35). One rank, nice 10.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal72_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal72"
tao_cal08_case "$CASE" \
    --scan-speed 0.002 --wire-feed-speed 0.018 \
    --beam-powers 50,50,650 \
    --end-time 0.50 --write-interval 0.10 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal72 "$CASE"
echo "CAL72_DONE"
