#!/bin/bash
# cal113 heat with feed 26 mm/s. Scan stays 3 mm/s. To 0.65 s.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal127_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal127"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.026 \
    --beam-powers 100,100,700 \
    --absorptivity-substrate 0.55 \
    --preheat 900 \
    --end-time 0.65 --write-interval 0.10 --np "$NP" \
    --theta-receding 20 --theta-advancing 55 \
    --theta-receding-wire 10 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 10 --theta-advancing-wire-trail 70 \
    --wire-sector-half-angle 60 --wire-sector-blend 20
tao_run "$NP" "$CASE"
tao_post cal127 "$CASE"
echo "CAL127_DONE"
