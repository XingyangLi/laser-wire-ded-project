#!/bin/bash
# Baseline 3D melt bead. Original fixed triple aims, no slit.
#
# Beams stay where the production track puts them: azimuths 55 / -55 / 180 deg,
# inclinations +32 / +32 / +22 deg, powers 700 / 700 / 450 W, 1/e^2 radii
# 0.70 / 0.70 / 0.55 mm, aim radii 1.40 / 1.40 / 0.90 mm, aim heights
# 0.40 / 0.40 / 0.30 mm. Plate window 20/90, wire window 25/70.
# No trailing-sector pin, no trailDrag, no oxygen.
#
# Production 30 mm/s feed leaves the wire core solid: the spots are on the
# plate, and melting the 1 mm wire takes about 200 W. Scan 4 mm/s and feed
# 18 mm/s keep these aims and let the pools melt the tip. Fed section is
# about 3.5 mm^2. Feed starts at 0.05 s, after the spots are liquid.
#
# One rank, nice 10, inside the 32-core cap. End time 0.55 s is 2.2 mm of travel.
DIR="$(cd "$(dirname "$0")" && pwd)"
exec > >(tee -a "$DIR/baseline_bead_launch.log") 2>&1
set -euo pipefail
source "$DIR/lib.sh"
NP=1
tao_acquire "$NP"
trap 'tao_release '"$NP" EXIT
tao_build
CASE="$TAO_ROOT/cases/wire_cavity_baseline"
python3 "$TAO_ROOT/generate_case.py" --case "$CASE" --laser-config triple \
    --wire-type solid --material 316L --resolution coarse --domain-y half \
    --upstream 5e-3 --downstream 5e-3 --half-width 3.5e-3 \
    --substrate-thickness 2e-3 --gas-height 3.5e-3 --gas-uniform-height 2.6e-3 \
    --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.15e-3 --feed-start 0.05 \
    --scan-speed 0.004 --wire-feed-speed 0.018 \
    --end-time 0.55 --write-interval 0.05 --np "$NP" --laser-ramp 2e-3 \
    --contact-pinning --pin-wire --porosity --wire-cavity \
    --theta-receding 20 --theta-advancing 90 \
    --theta-receding-wire 25 --theta-advancing-wire 70 \
    --wire-pin-frame head \
    --rigid-substrate 100
echo "---- beams ----"
grep -E 'beam[123]_' "$CASE/constant/meltProperties"
set +e
tao_run "$NP" "$CASE"
rc=$?
set -e
"$TAO_PY" "$DIR/render_baseline_bead.py" --case "$CASE" \
    --out "$DIR/baseline_bead_views.png" || true
echo "BASELINE_BEAD_RC $rc"
exit "$rc"
