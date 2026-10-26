#!/bin/bash
# Steep 130/165 trail arc of cal138, with 100 ppm Marangoni. To 0.70 s.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal152_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal152"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --absorptivity-substrate 0.65 \
    --end-time 0.70 --write-interval 0.10 --np "$NP" \
    --theta-receding 10 --theta-advancing 40 \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 130 --theta-advancing-wire-trail 165 \
    --wire-sector-half-angle 25 --wire-sector-blend 10 \
    --marangoni --oxygen-sigma-only --oxygen-ppm 100
tao_run "$NP" "$CASE"
tao_post cal152 "$CASE"
echo "CAL152_DONE"

