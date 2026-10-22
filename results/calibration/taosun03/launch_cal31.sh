#!/bin/bash
# cal31. cal08 settings on a wire box refined twice in x and y (~38 um).
# No trailing sector: that combination is cal10 on TaoSun-01.
# One rank. On the 35k-cell coarse mesh, 10 ranks spent the step inside
# MPI and 1 rank was about 7x faster; the refined mesh is timed the same way
# before this script is launched, and NP is kept at 1 unless that timing
# says otherwise. End time is where cal08 already held a tall crest.
# z is left coarse so the capillary step follows the 38 um edges.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal31_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_cal31"
tao_cal08_case "$CASE" \
    --end-time 0.40 --write-interval 0.10 --np "$NP" \
    --wire-refine 2
tao_run "$NP" "$CASE"
tao_post cal31 "$CASE"
echo "CAL31_DONE"
