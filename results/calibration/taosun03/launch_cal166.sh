#!/bin/bash
# cal131 heat. Rear beam at 0.30x from 0.64 to 0.80 s. To 1.00 s.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal166_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal166"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.028 \
    --beam-powers 100,100,700 \
    --absorptivity-substrate 0.65 \
    --end-time 1.00 --write-interval 0.10 --np "$NP" \
    --theta-receding 10 --theta-advancing 40 \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 30 --theta-advancing-wire-trail 100 \
    --wire-sector-half-angle 90 --wire-sector-blend 30 \
    --marangoni --oxygen-sigma-only --oxygen-ppm 100 \
    --rear-power-dip 0.64,0.80,0.30
tao_run "$NP" "$CASE"
tao_post cal166 "$CASE"
echo "CAL166_DONE"

