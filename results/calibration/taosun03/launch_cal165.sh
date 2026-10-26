#!/bin/bash
# cal117 heat. Trail window 70/120 deg over 30 deg of +x. To 0.75 s.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal165_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal165"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --absorptivity-substrate 0.65 \
    --end-time 0.75 --write-interval 0.10 --np "$NP" \
    --theta-receding 10 --theta-advancing 40 \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 70 --theta-advancing-wire-trail 120 \
    --wire-sector-half-angle 30 --wire-sector-blend 12 \
    --marangoni --oxygen-sigma-only --oxygen-ppm 100
tao_run "$NP" "$CASE"
tao_post cal165 "$CASE"
echo "CAL165_DONE"

