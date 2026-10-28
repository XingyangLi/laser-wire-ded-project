#!/bin/bash
# Melt track with three beams 120 deg apart, cal08 heat on a coarse mesh.
# The wire stays a metal region. The true-wall cut and the hard pin come
# after this track exists (launch_pin_on_track.sh).
#
# Azimuths 60, -60, 180. Half-domain symmetryY folds y < 0 and halves each
# beam's power, so the negative beam has to stay in the dictionary.
# Each axis meets the plate 0.55 mm from the wire. The 0.26 mm spot is
# mostly on the substrate and the inner wing meets the wire. Inclination is
# 15 deg, so that wing strikes the wire near 0.8 mm rather than at the foot.
# The aim is fixed. The first metal along each ray absorbs the power.
#
#   TRACK_TAG   case tag (default cal90)
#   TRACK_END   end time [s] (default 0.60)
#   TRACK_SKIP_BUILD
#
# 12 ranks, nice 10. Lasers on. No painted drop.
exec > >(tee -a /home/xingyang/laser-wire-ded-project/results/calibration/track120_launch.log) 2>&1
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
TAG=${TRACK_TAG:-cal90}
END=${TRACK_END:-0.60}
if [ "${TRACK_PARALLEL:-0}" != 1 ] && ps -u xingyang -o cmd | grep -q '[l]aserWireDEDFoam'; then
    echo "a solver is already running" >&2
    exit 1
fi
set +e
set +u
set +o pipefail
# shellcheck disable=SC1091
source /usr/lib/openfoam/openfoam2406/etc/bashrc
set -e
set -u
set -o pipefail
export PATH="${FOAM_USER_APPBIN}:$PATH"
hash -r
if [ "${TRACK_SKIP_BUILD:-0}" != 1 ]; then
    cd "$ROOT/solver"
    ./Allwmake
    cd "$ROOT"
fi

case="$ROOT/cases/wire_cavity_${TAG}"
log="$ROOT/results/calibration/${TAG}_launch.log"
{
    echo "=== equilateral track ${TAG}: feed 0.024, azimuths 60,-60,180, end ${END} ==="
    python3 "$ROOT/generate_case.py" --case "$case" --laser-config triple \
        --wire-type solid --material 316L --resolution coarse --domain-y half \
        --upstream 4e-3 --downstream 7e-3 --half-width 3.5e-3 \
        --substrate-thickness 2e-3 --gas-height 3.5e-3 --gas-uniform-height 2.6e-3 \
        --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.08e-3 --feed-start 0.05 \
        --scan-speed 0.004 --wire-feed-speed 0.024 \
        --beam-azimuths 60,-60,180 \
        --beam-inclinations=-15,-15,-15 \
        --beam-powers 160,160,420 \
        --beam-radii-each 0.26e-3,0.26e-3,0.26e-3 \
        --beam-aim-radii 0.604e-3,0.604e-3,0.604e-3 \
        --beam-aim-heights 0.20e-3,0.20e-3,0.20e-3 \
        --end-time "$END" --write-interval 0.20 --np 12 --laser-ramp 2e-3 \
        --contact-pinning --pin-wire --porosity --wire-cavity \
        --theta-receding 110 --theta-advancing 150 \
        --theta-receding-wire 30 --theta-advancing-wire 90 \
        --contact-force-factor 6 \
        --no-marangoni \
        --wire-pin-frame head \
        --rigid-substrate 100
    python3 "$ROOT/results/calibration/check_beam_azimuths.py" "$case"
    if grep -q "linePin" "$case/constant/meltProperties"; then
        echo "track case must not carry a line pin" >&2
        exit 1
    fi
    if grep -q "oxideAngle" "$case/constant/meltProperties"; then
        echo "track case must not carry oxideAngle" >&2
        exit 1
    fi
    cd "$case"
    MESH_ONLY=1 ./Allrun 12
    python3 "$ROOT/results/calibration/plot_track_views.py" \
        --case "$case" --tag "$TAG" \
        --out "$ROOT/results/calibration/${TAG}_beams_top.png"
    touch case.foam
    nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np 12 laserWireDEDFoam -parallel \
        > log.laserWireDEDFoam 2>&1
    echo "TRACK120_DONE ${TAG}"
} > "$log" 2>&1
echo "TRACK120_WAIT_DONE ${TAG}"
