#!/bin/bash
# Feed 28 mm/s, no oxygen, trail window 50/95 deg over 40 deg. To 0.75 s.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal159_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal159"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.028 \
    --beam-powers 100,100,700 \
    --absorptivity-substrate 0.65 \
    --end-time 0.75 --write-interval 0.10 --np "$NP" \
    --theta-receding 10 --theta-advancing 40 \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 50 --theta-advancing-wire-trail 95 \
    --wire-sector-half-angle 40 --wire-sector-blend 15
tao_run "$NP" "$CASE"
tao_post cal159 "$CASE"
echo "CAL159_DONE"

