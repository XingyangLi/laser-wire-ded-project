#!/bin/bash
# cal113, the crest-compliant score-8 recipe, at --wire-refine 2. One rank. Not the refined 60/140 case. To 0.40 s.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal129_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal129"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --absorptivity-substrate 0.55 \
    --preheat 900 \
    --end-time 0.40 --write-interval 0.10 --np "$NP" \
    --theta-receding 20 --theta-advancing 55 \
    --theta-receding-wire 10 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 10 --theta-advancing-wire-trail 70 \
    --wire-sector-half-angle 60 --wire-sector-blend 20 \
    --wire-refine 2
tao_run "$NP" "$CASE"
tao_post cal129 "$CASE"
echo "CAL129_DONE"
