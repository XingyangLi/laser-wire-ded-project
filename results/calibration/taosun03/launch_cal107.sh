#!/bin/bash
# cal107. The 20/55 plate window pinned the line on cal100, and it did not
# melt the plate. This adds substrate absorptivity 0.55, which took the
# plate surface through the solidus on cal103. Same 700 W notch. One rank.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal107_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal107"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --absorptivity-substrate 0.55 \
    --end-time 0.40 --write-interval 0.10 --np "$NP" \
    --theta-receding 20 --theta-advancing 55 \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 30 --theta-advancing-wire-trail 100 \
    --wire-sector-half-angle 90 --wire-sector-blend 30
tao_run "$NP" "$CASE"
tao_post cal107 "$CASE"
echo "CAL107_DONE"
