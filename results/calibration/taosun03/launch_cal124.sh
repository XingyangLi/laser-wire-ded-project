#!/bin/bash
# cal113 heat. Front floor 15/70. Trailing sector receding 50/85 over 60 deg of +x. To 0.65 s.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal124_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal124"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --absorptivity-substrate 0.55 \
    --preheat 900 \
    --end-time 0.65 --write-interval 0.10 --np "$NP" \
    --theta-receding 20 --theta-advancing 55 \
    --theta-receding-wire 15 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 50 --theta-advancing-wire-trail 85 \
    --wire-sector-half-angle 60 --wire-sector-blend 20
tao_run "$NP" "$CASE"
tao_post cal124 "$CASE"
echo "CAL124_DONE"
