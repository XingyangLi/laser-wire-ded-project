#!/bin/bash
# cal56 oxide skin on this machine's 3 mm slab, then the physics in stages.
#
# Stage skin: 300 ppm Sahoo-Belton sigma, plate 10/40, trailing face 140/140,
# sector blend 0, painted 0.05 mm film, 19 um neck, laser / Marangoni / recoil
# off, 0 to 6 ms. Four ranks: on a ~40k-cell mesh on this machine, 4 ranks
# were faster than 8, and a 32-way split spends the step in GAMG. Four stays
# inside the 32-rank cap.
#
# If that film is still open and at least 0.25 mm deep, the next stages are
# recoil, then Marangoni, then the beams, 6 ms each.
#
#   ./launch_oxide_skin.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"

CASE="$TAO_ROOT/cases/wire_cavity_skin56"
PY="$TAO_PY"
NP=4
LOG="$TAO_OUT/skin56.log"
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

patch_dict() {
    python3 - "$CASE/constant/meltProperties" <<'PY'
import re, sys
from pathlib import Path
p = Path(sys.argv[1])
t = p.read_text()
t = t.replace("    marangoni           true;", "    marangoni           false;", 1)
t = t.replace("    recoil      true;", "    recoil      false;", 1)
t = re.sub(r"(?m)^(\s*)tStart\s+[0-9.eE+-]+;", r"\1tStart          9;", t, count=1)
p.write_text(t)
print("DICT skin only: marangoni off, recoil off, laser tStart 9")
PY
}

enable_term() {
    local term="$1" tend="$2"
    python3 - "$CASE/constant/meltProperties" "$term" "$tend" <<'PY'
import re, sys
from pathlib import Path
p = Path(sys.argv[1])
term, tend = sys.argv[2], sys.argv[3]
t = p.read_text()
if term == "recoil":
    t = t.replace("    recoil      false;", "    recoil      true;", 1)
elif term == "marangoni":
    t = t.replace("    marangoni           false;", "    marangoni           true;", 1)
elif term == "beams":
    t = re.sub(r"(?m)^(\s*)tStart\s+[0-9.eE+-]+;", rf"\1tStart          {tend};", t, count=1)
else:
    sys.exit(f"unknown term {term}")
p.write_text(t)
print(f"DICT {term} on at {tend}")
PY
}

film_window() {
    local t0="$1" t1="$2"
    "$PY" "$DIR/score_film.py" "$CASE" --window "$t0" "$t1"
}

run_stage() {
    local tend="$1" log="$2"
    tao_source_foam
    (
        cd "$CASE"
        foamDictionary -entry endTime -set "$tend" system/controlDict >/dev/null
    )
    hold_slots
    set +e
    (
        cd "$CASE"
        nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
            laserWireDEDFoam -parallel > "$log" 2>&1
    ) &
    local pid=$!
    local scored=""
    while kill -0 "$pid" 2>/dev/null; do
        sleep 20
        if [[ -f "$log" ]] && grep -q "FOAM FATAL" "$log"; then
            echo "KILL $log foam fatal"
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
            local rc=0
            "$PY" "$DIR/neck_state.py" "$CASE" "$latest" --calm-max 25 --smear-max 0.9 || rc=$?
            "$PY" "$DIR/score_film.py" "$CASE" "$latest" || true
            scored="$latest"
            if (( rc == 3 )); then
                echo "KILL violent at t=$latest"
                pkill -TERM -P "$pid" || true
                kill -TERM "$pid" 2>/dev/null || true
                break
            fi
        fi
    done
    wait "$pid" || true
    set -e
    drop_slots
}

prepare_case() {
    echo "GENERATE skin56 $(date --iso-8601=seconds)"
    tao_source_foam
    tao_build
    python3 "$TAO_ROOT/generate_case.py" --case "$CASE" \
        --laser-config triple \
        --wire-type solid --material 316L --resolution coarse --domain-y half \
        --upstream 1.0e-3 --downstream 2.0e-3 --half-width 1.2e-3 \
        --substrate-thickness 0.6e-3 \
        --gas-height 2.0e-3 --gas-uniform-height 1.8e-3 \
        --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.08e-3 --feed-start 0 \
        --scan-speed 0.004 --wire-feed-speed 0.020 \
        --beam-azimuths 30,-30,180 \
        --beam-inclinations=-26,-26,-38 \
        --beam-powers 160,160,420 \
        --beam-radii-each 0.26e-3,0.26e-3,0.26e-3 \
        --beam-aim-radii 0.60e-3,0.60e-3,0.24e-3 \
        --beam-aim-heights 0.08e-3,0.08e-3,0.55e-3 \
        --end-time 0.006 --write-interval 0.002 --np "$NP" --laser-ramp 1e-4 \
        --max-co 0.4 --capillary-dt-factor 1 \
        --neck-refine 3 \
        --c-alpha-neck 4 \
        --oxygen-ppm 300 --oxygen-sigma-only \
        --oxide-skin --oxide-skin-mu 20 --oxide-skin-k 1e14 \
        --oxide-skin-gap 0.10e-3 --oxide-skin-ppm-ref 300 \
        --contact-pinning --pin-wire --porosity --wire-cavity \
        --theta-receding 10 --theta-advancing 40 \
        --theta-receding-wire 25 --theta-advancing-wire 70 \
        --wire-sector \
        --theta-receding-wire-trail 140 --theta-advancing-wire-trail 140 \
        --wire-sector-half-angle 90 --wire-sector-blend 0 \
        --contact-force-factor 6 \
        --no-recoil --no-marangoni \
        --wire-pin-frame head \
        --rigid-substrate 100
    patch_dict
    grep -q "oxideSkin" "$CASE/constant/meltProperties"
    grep -q "muSkin          20;" "$CASE/constant/meltProperties"
    grep -q "Kskin           1e14;" "$CASE/constant/meltProperties" \
        || grep -q "Kskin           1e+14;" "$CASE/constant/meltProperties" \
        || grep -q "Kskin           100000000000000;" "$CASE/constant/meltProperties"
    grep -q "marangoni           false;" "$CASE/constant/meltProperties"
    grep -q "recoil      false;" "$CASE/constant/meltProperties"
    grep -q "thetaRecedingWireTrail 140" "$CASE/constant/meltProperties"
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
    tao_source_foam
    (
        cd "$CASE"
        foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict >/dev/null
        foamDictionary -entry coeffs.n -set "(2 2 1)" system/decomposeParDict >/dev/null
        decomposePar -force > log.decomposePar 2>&1
        touch case.foam
    )
    echo "PREPARE_OK skin56"
}

main() {
    prepare_case
    echo "STAGE skin 0 -> 0.006"
    run_stage 0.006 "$CASE/log.skin"
    if ! film_window 0.002 0.006; then
        echo "SKIN_FILM_FAILED"
        echo "SKIN56_DONE"
        return 0
    fi
    echo "STAGE recoil 0.006 -> 0.012"
    enable_term recoil 0.006
    run_stage 0.012 "$CASE/log.recoil"
    if ! film_window 0.008 0.012; then
        echo "RECOIL_FILM_FAILED"
        echo "SKIN56_DONE"
        return 0
    fi
    echo "STAGE marangoni 0.012 -> 0.018"
    enable_term marangoni 0.012
    run_stage 0.018 "$CASE/log.marangoni"
    if ! film_window 0.014 0.018; then
        echo "MARANGONI_FILM_FAILED"
        echo "SKIN56_DONE"
        return 0
    fi
    echo "STAGE beams 0.018 -> 0.024"
    enable_term beams 0.018
    run_stage 0.024 "$CASE/log.beams"
    "$PY" "$DIR/neck_state.py" "$CASE" --latest --smear-max 0.9 || true
    echo "SKIN56_DONE"
}

main "$@"
