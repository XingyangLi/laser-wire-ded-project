#!/bin/bash
# cal114 heat. Front wire floor 20/70. Trailing sector only: receding 55, advancing 90, over 60 deg of +x. The ~30 deg trail cells recede. To 0.70 s.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal122_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal122"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --absorptivity-substrate 0.65 \
    --end-time 0.70 --write-interval 0.10 --np "$NP" \
    --theta-receding 10 --theta-advancing 40 \
    --theta-receding-wire 20 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 55 --theta-advancing-wire-trail 90 \
    --wire-sector-half-angle 60 --wire-sector-blend 20
tao_run "$NP" "$CASE"
tao_post cal122 "$CASE"
echo "CAL122_DONE"
