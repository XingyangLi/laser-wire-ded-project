#!/bin/bash
# Full-domain oxide-skin slit with the beams off and recoil off.
#
# The same mesh with beams, Marangoni and recoil on held an open
# 0.060 x 0.800 mm film at 4 ms and lost it by 8 ms (0.140 mm wide,
# 0.175 mm deep). Hot recoil is the part the full track cannot carry.
# This run keeps the oxide skin, Sahoo-Belton sigma, Marangoni and the
# wire feed, and switches the laser and recoil off. Same 19 um neck,
# 4 ranks, nice 10. 32 ranks was about 10 s/step on this mesh.
#
#   bash launch_oxide_cold.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"

SRC="$TAO_ROOT/cases/wire_cavity_skinfull"
CASE="$TAO_ROOT/cases/wire_cavity_skincold"
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
    if [[ -d "$CASE/processor0/constant" && -d "$CASE/processor0/0" ]]; then
        echo "CASE already prepared"
    else
        echo "COPY mesh and painted 0 from skinfull $(date --iso-8601=seconds)"
        rm -rf "$CASE"
        mkdir -p "$CASE"
        rsync -a \
            --exclude 'processor*' \
            --exclude 'log.*' \
            --exclude 'postProcessing' \
            --exclude 'dynamicCode' \
            "$SRC/" "$CASE/"
        # The hot run's later times are not a restart state.
        find "$CASE" -mindepth 1 -maxdepth 1 -type d -regextype posix-extended \
            -regex '.*/[0-9].*' ! -name '0' -exec rm -rf {} +
        local p name
        for p in "$SRC"/processor*; do
            name="$(basename "$p")"
            mkdir -p "$CASE/$name"
            rsync -a "$p/constant" "$CASE/$name/"
            rsync -a "$p/0" "$CASE/$name/"
        done
    fi
    python3 - "$CASE/constant/meltProperties" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1])
text = path.read_text()
old = text
laser = (
    "laser   // ray-traced; radius = 1/e^2 radius; "
    "absorptivity = substrate (wire: wireMaterial)\n"
    "{\n"
    "    enabled         true;"
)
laser_off = laser.replace("enabled         true;", "enabled         false;")
if laser not in text:
    raise SystemExit("laser block not found")
text = text.replace(laser, laser_off, 1)
recoil = "vaporisation\n{\n    recoil      true;"
recoil_off = "vaporisation\n{\n    recoil      false;"
if recoil not in text:
    raise SystemExit("recoil block not found")
text = text.replace(recoil, recoil_off, 1)
start = "    tStart          0;\n    tRamp           0.0001;"
start_off = "    tStart          1;\n    tRamp           0.0001;"
if start not in text:
    raise SystemExit("laser tStart not found")
text = text.replace(start, start_off, 1)
if "marangoni           true;" not in text:
    raise SystemExit("marangoni should stay on")
if "oxideSkin" not in text or "muSkin          20;" not in text:
    raise SystemExit("oxide skin missing")
if text == old:
    raise SystemExit("patch did nothing")
path.write_text(text)
print("PATCHED beams off, recoil off, Marangoni on, skin on")
PY
    tao_source_foam
    (
        cd "$CASE"
        foamDictionary -entry endTime -set 0.012 system/controlDict >/dev/null
        foamDictionary -entry writeInterval -set 0.004 system/controlDict >/dev/null
        foamDictionary -entry startFrom -set latestTime system/controlDict >/dev/null
    )
    grep -q "recoil      false;" "$CASE/constant/meltProperties"
    grep -q "enabled         false;" "$CASE/constant/meltProperties"
    grep -q "tStart          1;" "$CASE/constant/meltProperties"
    grep -q "marangoni           true;" "$CASE/constant/meltProperties"
    grep -q "Kskin           1e+14;" "$CASE/constant/meltProperties"
    if [[ ! -d "$CASE/processor0/0" ]]; then
        echo "painted time 0 missing" >&2
        exit 1
    fi
    # Later hot times must not be on this case.
    if compgen -G "$CASE/processor0/0.*" >/dev/null; then
        echo "refusing to start from a later time" >&2
        exit 1
    fi
    "$PY" "$DIR/score_film.py" "$CASE" 0
    echo "PREPARE_OK skincold"
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
            "$PY" "$DIR/score_film.py" "$CASE" --window 0 "$latest" || true
            scored="$latest"
        fi
        if [[ -f "$LOG" ]]; then
            grep -E '^Time = |OxideSkin: cells|laser: incident' "$LOG" | tail -3 || true
        fi
    done
    wait "$pid" || true
    set -e
    drop_slots
    echo "SKINCOLD_DONE"
}

main() {
    prepare_case
    run_case
}

main "$@"
