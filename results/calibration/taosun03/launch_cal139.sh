#!/bin/bash
# cal113 heat. Narrow rear arc (30 deg), window 100-140 deg. To 0.65 s.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal139_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal139"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --absorptivity-substrate 0.55 \
    --preheat 900 \
    --end-time 0.65 --write-interval 0.10 --np "$NP" \
    --theta-receding 20 --theta-advancing 55 \
    --theta-receding-wire 10 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 100 --theta-advancing-wire-trail 140 \
    --wire-sector-half-angle 30 --wire-sector-blend 12
tao_run "$NP" "$CASE"
tao_post cal139 "$CASE"
echo "CAL139_DONE"
