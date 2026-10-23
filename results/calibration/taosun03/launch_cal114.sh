#!/bin/bash
# cal114. cal103 at 0.65 s pinned every wire cell (mean 39 deg, z 1.30-1.91 mm)
# on a 1.76 / 1.15 mm dome, but only 4 of 13 trail columns melted.
# Same 10/40 plate and 30/100 trail, substrate absorptivity 0.65 instead of
# 0.55, no preheat. One rank, nice 10, to 0.70 s.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal114_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal114"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --absorptivity-substrate 0.65 \
    --end-time 0.70 --write-interval 0.10 --np "$NP" \
    --theta-receding 10 --theta-advancing 40 \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 30 --theta-advancing-wire-trail 100 \
    --wire-sector-half-angle 90 --wire-sector-blend 30
tao_run "$NP" "$CASE"
tao_post cal114 "$CASE"
echo "CAL114_DONE"
