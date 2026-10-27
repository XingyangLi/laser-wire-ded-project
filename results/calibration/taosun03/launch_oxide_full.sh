#!/bin/bash
# Full-track demo of the oxide-skin slit.
#
# The slab smoke held an open 0.060 mm film through beams, Marangoni and
# recoil (0.575-0.625 mm deep over the last 4 ms). This is that recipe on
# the cal08 track: wire feeding, bead forming, 19 um neck, 32 ranks, nice 10.
# Columns stay intact (nz = 1). Fields every 4 ms, through 20 ms.
#
# 32 ranks was measured at about 10 s/step: the 19 um neck is one x-slice, so
# the other ranks only add GAMG waits. Four ranks is the count that integrated
# the same neck on the slab.
#
# The 0.10 mm shell held the film at 4 ms. By 7.3 ms a gas cell 0.17 mm off
# the wire was at several km/s and the film depth was 0.10 mm. The shell is
# 0.20 mm so that cell is inside it.
#
#   bash launch_oxide_full.sh
#   bash launch_oxide_full.sh resume
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"

CASE="$TAO_ROOT/cases/wire_cavity_skinfull"
PY="$TAO_PY"
NP=4
LOG="$CASE/log.laserWireDEDFoam"
HELD=0

hold_slots() {
    tao_acquire "$NP"
    HELD=$NP
}

drop_slots() {
    if (( HELD > 0 )); then
        tao_release "$HELD"
        HELD=0
    fi
}

trap drop_slots EXIT

prepare_case() {
    echo "GENERATE skinfull $(date --iso-8601=seconds)"
    tao_source_foam
    tao_build
    python3 "$TAO_ROOT/generate_case.py" --case "$CASE" \
        --laser-config triple \
        --wire-type solid --material 316L --resolution coarse --domain-y half \
        --upstream 4e-3 --downstream 7e-3 --half-width 3.5e-3 \
        --substrate-thickness 2e-3 --gas-height 3.5e-3 --gas-uniform-height 2.6e-3 \
        --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.08e-3 --feed-start 0 \
        --scan-speed 0.004 --wire-feed-speed 0.020 \
        --beam-azimuths 30,-30,180 \
        --beam-inclinations=-26,-26,-38 \
        --beam-powers 160,160,420 \
        --beam-radii-each 0.26e-3,0.26e-3,0.26e-3 \
        --beam-aim-radii 0.60e-3,0.60e-3,0.24e-3 \
        --beam-aim-heights 0.08e-3,0.08e-3,0.55e-3 \
        --end-time 0.020 --write-interval 0.004 --np "$NP" --laser-ramp 1e-4 \
        --max-co 0.4 --capillary-dt-factor 1 \
        --neck-refine 3 \
        --c-alpha-neck 4 \
        --oxygen-ppm 300 --oxygen-sigma-only \
        --oxide-skin --oxide-skin-mu 20 --oxide-skin-k 1e14 \
        --oxide-skin-gap 0.20e-3 --oxide-skin-ppm-ref 300 \
        --contact-pinning --pin-wire --porosity --wire-cavity \
        --theta-receding 10 --theta-advancing 40 \
        --theta-receding-wire 25 --theta-advancing-wire 70 \
        --wire-sector \
        --theta-receding-wire-trail 140 --theta-advancing-wire-trail 140 \
        --wire-sector-half-angle 90 --wire-sector-blend 0 \
        --contact-force-factor 6 \
        --wire-pin-frame head \
        --rigid-substrate 100
    grep -q "oxideSkin" "$CASE/constant/meltProperties"
    grep -q "muSkin          20;" "$CASE/constant/meltProperties"
    grep -q "Kskin           1e+14;" "$CASE/constant/meltProperties" \
        || grep -q "Kskin           1e14;" "$CASE/constant/meltProperties"
    grep -q "marangoni           true;" "$CASE/constant/meltProperties"
    grep -q "recoil      true;" "$CASE/constant/meltProperties"
    grep -q "tStart          0;" "$CASE/constant/meltProperties"
    if grep -q "oxygenAngleTable" "$CASE/constant/meltProperties"; then
        echo "oxygen angle table must stay off" >&2
        exit 1
    fi
    tao_source_foam
    (
        cd "$CASE"
        MESH_ONLY=1 ./Allrun 1
    )
    "$PY" "$TAO_ROOT/results/calibration/paint_slit_meniscus.py" \
        --case "$CASE" --wire-t 300 --film-mm 0.05
    "$PY" "$DIR/score_film.py" "$CASE" 0
    decompose_case
    echo "PREPARE_OK skinfull"
}

decompose_case() {
    if [[ -d "$CASE/processor0" ]]; then
        echo "DECOMPOSE already present"
        return 0
    fi
    tao_source_foam
    (
        cd "$CASE"
        foamDictionary -entry endTime -set 0.020 system/controlDict >/dev/null
        foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict >/dev/null
        foamDictionary -entry method -set simple system/decomposeParDict >/dev/null
        # Split only in x. A y split of this graded mesh left two ranks with
        # no cells, and an empty rank aborts in MPI_Allreduce. nz stays 1 so
        # a laser column is not cut in z.
        foamDictionary -entry coeffs.n -set "(4 1 1)" system/decomposeParDict >/dev/null
        decomposePar -force > log.decomposePar 2>&1
        if grep -q "Number of cells = 0" log.decomposePar; then
            echo "decompose left an empty rank" >&2
            exit 1
        fi
        touch case.foam
    )
}

run_case() {
    tao_source_foam
    hold_slots
    set +e
    (
        cd "$CASE"
        nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
            laserWireDEDFoam -parallel > "$LOG" 2>&1
    ) &
    local pid=$!
    local scored=""
    while kill -0 "$pid" 2>/dev/null; do
        sleep 30
        if [[ -f "$LOG" ]] && grep -q "FOAM FATAL" "$LOG"; then
            echo "KILL foam fatal"
            pkill -TERM -P "$pid" || true
            kill -TERM "$pid" 2>/dev/null || true
            break
        fi
        local latest=""
        latest="$("$PY" - "$CASE" <<'PY'
import sys
sys.path.insert(0, "/home/asb6102/laser-wire-ded-project/results/calibration/taosun03")
import neck_state as ns
names = ns.time_dirs(sys.argv[1])
print(names[-1] if names else "")
PY
)" || latest=""
        if [[ -n "$latest" && "$latest" != "0" && "$latest" != "$scored" ]]; then
            echo "SCORE t=$latest"
            "$PY" "$DIR/score_film.py" "$CASE" "$latest" || true
            scored="$latest"
        fi
        if [[ -f "$LOG" ]]; then
            grep -E '^Time = |OxideSkin: cells|laser: incident' "$LOG" | tail -3 || true
        fi
    done
    wait "$pid" || true
    set -e
    drop_slots
    echo "SKINFULL_DONE"
}

main() {
    if [[ "${1:-}" == "resume" ]]; then
        echo "RESUME skinfull $(date --iso-8601=seconds)"
        decompose_case
    else
        prepare_case
    fi
    run_case
}

main "$@"
