#!/bin/bash
# Short rate check for cal08 settings at --wire-refine 2, one rank.
# Not the science run. End time covers a few dozen capillary steps.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/cal31_probe.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
CASE="$TAO_ROOT/cases/wire_cavity_cal31_probe"
tao_cal08_case "$CASE" \
    --end-time 0.0004 --write-interval 0.0004 --np "$NP" \
    --wire-refine 2
tao_run "$NP" "$CASE"
echo "CAL31_PROBE_DONE"
