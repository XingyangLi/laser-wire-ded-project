#!/bin/bash
# cal71. cal36 powers (100+100+700 W) on a full-width mesh.
# The half-domain wake centroid sits near y = 1 mm even when the cavity
# touches the symmetry plane. This asks whether the wake is actually centred.
# One rank, nice 10. Coarse cells, about twice the half-domain count.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal71_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal71"
tao_cal08_case "$CASE" \
    --domain-y full \
    --scan-speed 0.003 --wire-feed-speed 0.020 \
    --beam-powers 100,100,700 \
    --end-time 0.30 --write-interval 0.15 --np "$NP"
tao_run "$NP" "$CASE"
tao_post cal71 "$CASE"
echo "CAL71_DONE"
