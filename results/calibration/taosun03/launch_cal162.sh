#!/bin/bash
# cal117 heat. Rear beam at 0.25x from 0.50 to 0.78 s. To 0.95 s.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal162_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal162"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --absorptivity-substrate 0.65 \
    --end-time 0.95 --write-interval 0.10 --np "$NP" \
    --theta-receding 10 --theta-advancing 40 \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 30 --theta-advancing-wire-trail 100 \
    --wire-sector-half-angle 90 --wire-sector-blend 30 \
    --marangoni --oxygen-sigma-only --oxygen-ppm 100 \
    --rear-power-dip 0.50,0.78,0.25
tao_run "$NP" "$CASE"
tao_post cal162 "$CASE"
echo "CAL162_DONE"

