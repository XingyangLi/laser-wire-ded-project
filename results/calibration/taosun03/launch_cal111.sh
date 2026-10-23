#!/bin/bash
# cal111. Same heated 20/55 plate as cal110, with a narrower trailing pin
# 20/45 over 45 deg of +x. Angles outside that band get a restoring force
# on the face behind the wire. One rank, nice 10, to 0.60 s.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal111_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal111"
tao_cal08_case "$CASE" \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --absorptivity-substrate 0.55 \
    --preheat 900 \
    --end-time 0.60 --write-interval 0.10 --np "$NP" \
    --theta-receding 20 --theta-advancing 55 \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-sector \
    --theta-receding-wire-trail 20 --theta-advancing-wire-trail 45 \
    --wire-sector-half-angle 45 --wire-sector-blend 20
tao_run "$NP" "$CASE"
tao_post cal111 "$CASE"
echo "CAL111_DONE"
