#!/bin/bash
# Unpainted settled neck, laser and recoil off, feed 24 mm/s.
# The trailing-face shell (trailDrag) is held at alpha = 1 and the feed
# velocity and moves down with the wire. The pool outside it is free.
# Stop at 2 ms if the neck runs away, the step collapses, or a wide gas
# column appears. Otherwise continue to 10 ms.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"

SRC="$TAO_ROOT/cases/wire_cavity_smokeS"
CASE="$TAO_ROOT/cases/wire_cavity_drag24"
T0="0.7047"
PY="$TAO_PY"
NP=4
HELD=0
TEND="$(python3 -c 'print(0.7047 + 0.010)')"
TGATE="$(python3 -c 'print(0.7047 + 0.002)')"

hold_slots() { tao_acquire "$1"; HELD=$1; }
drop_slots() {
    if (( HELD > 0 )); then tao_release "$HELD"; HELD=0; fi
}
trap drop_slots EXIT

prepare_case() {
    if [[ -d "$CASE/processor0/$T0" && -f "$CASE/constant/meltProperties" ]]; then
        if grep -q "trailDrag" "$CASE/constant/meltProperties"; then
            echo "CASE exists"
            return 0
        fi
    fi
    echo "COPY drag24 from smokeS t=$T0"
    rm -rf "$CASE"
    mkdir -p "$CASE"
    rsync -a \
        --exclude 'processor*' \
        --exclude 'log.*' \
        --exclude 'postProcessing' \
        --exclude 'dynamicCode' \
        "$SRC/" "$CASE/"
    find "$CASE" -mindepth 1 -maxdepth 1 -type d -regextype posix-extended \
        -regex '.*/[0-9].*' -exec rm -rf {} +
    local p name
    for p in "$SRC"/processor*; do
        name="$(basename "$p")"
        mkdir -p "$CASE/$name/constant" "$CASE/$name/$T0"
        rsync -a "$p/constant/" "$CASE/$name/constant/"
        rsync -a "$p/$T0/" "$CASE/$name/$T0/"
    done
    python3 - "$CASE" "$T0" "$TEND" <<'PY'
import re, sys
from pathlib import Path
case, t0, tend = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
mp = case / "constant/meltProperties"
t = mp.read_text()
t = t.replace("    marangoni           true;", "    marangoni           false;", 1)
t = t.replace("    recoil      false;", "    recoil      false;", 1)
# laser block: the ray-traced one, not porosity or statistics
i = t.find("laser   //")
j = t.find("\n}", i)
if i < 0 or j < 0:
    raise SystemExit("laser block missing")
block = t[i:j]
block2 = block.replace("enabled         true;", "enabled         false;", 1)
if block2 == block:
    raise SystemExit("laser enabled line missing")
t = t[:i] + block2 + t[j:]
t = t.replace("    tFeedStart      0.706;", f"    tFeedStart      {t0};", 1)
t = t.replace("    tFeedRamp       0.002;", "    tFeedRamp       0;", 1)
if "trailDrag" not in t:
    t += """
trailDrag   // imposed trailing-face shell, pool outside it is free
{
    enabled         true;
    radialCells     2;
    axialCells      3;
    sectorDeg       75;
}
"""
mp.write_text(t)
cd = case / "system/controlDict"
c = cd.read_text()
c2, n = re.subn(r"(?m)^endTime\s+[0-9.eE+-]+;", f"endTime         {tend};", c, count=1)
if n != 1:
    raise SystemExit("endTime missing")
c2, n = re.subn(
    r"(?m)^(writeInterval\s+)[0-9.eE+-]+;",
    r"\g<1>0.0005;",
    c2, count=1,
)
if n != 1:
    raise SystemExit("writeInterval missing")
cd.write_text(c2)
print(f"PATCH drag24 t0 {t0} end {tend} laser off recoil off feed 24 mm/s Marangoni off")
PY
}

latest_time() {
    "$PY" - "$1" <<'PY'
import sys
from pathlib import Path
root = Path(sys.argv[1]) / "processor0"
names = []
for p in root.iterdir():
    if not p.is_dir():
        continue
    try:
        float(p.name)
    except ValueError:
        continue
    if (p / "alpha.metal").is_file():
        names.append(p.name)
names.sort(key=float)
print(names[-1] if names else "")
PY
}

main() {
    prepare_case
    grep -q "trailDrag" "$CASE/constant/meltProperties"
    grep -q "enabled         false;" "$CASE/constant/meltProperties"
    tao_source_foam
    tao_build
    "$PY" "$DIR/score_film.py" "$CASE" "$T0" || true
    hold_slots "$NP"
    (
        cd "$CASE"
        exec nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
            laserWireDEDFoam -parallel > "$CASE/log.laserWireDEDFoam" 2>&1
    ) &
    local pid=$!
    echo "PID drag $pid"
    local scored="" gated=0
    while kill -0 "$pid" 2>/dev/null; do
        sleep 20
        if [[ -f "$CASE/log.laserWireDEDFoam" ]] && grep -q "FOAM FATAL" "$CASE/log.laserWireDEDFoam"; then
            echo "KILL foam fatal"
            kill -TERM "$pid" 2>/dev/null || true
            break
        fi
        local latest=""
        latest="$(latest_time "$CASE")" || latest=""
        if [[ -z "$latest" || "$latest" == "$scored" ]]; then
            grep -E 'TrailDrag:|deltaT = |FOAM FATAL' "$CASE/log.laserWireDEDFoam" | tail -1 || true
            continue
        fi
        echo "SCORE t=$latest"
        "$PY" "$DIR/score_film.py" "$CASE" "$latest" || true
        local rc=0
        "$PY" "$DIR/neck_state.py" "$CASE" "$latest" --calm-max 15 || rc=$?
        if (( rc == 3 )); then
            echo "KILL violent neck at t=$latest"
            kill -TERM "$pid" 2>/dev/null || true
            break
        fi
        local dt=""
        # "deltaT limited by capillary condition" is a note, not the step size.
        dt="$(grep '^deltaT = ' "$CASE/log.laserWireDEDFoam" | tail -1 | awk '{print $3}' || true)"
        if [[ -z "$dt" ]]; then
            scored="$latest"
            continue
        fi
        python3 - "$dt" "$latest" "$TGATE" <<'PY' || {
import sys
try:
    dt = float(sys.argv[1])
except ValueError:
    raise SystemExit(0)
t = float(sys.argv[2])
gate = float(sys.argv[3])
if t + 1e-9 >= gate and dt < 1.5e-7:
    raise SystemExit(1)
raise SystemExit(0)
PY
            echo "KILL timestep collapse dt=$dt at t=$latest"
            kill -TERM "$pid" 2>/dev/null || true
            break
        }
        if (( gated == 0 )); then
            python3 - "$latest" "$TGATE" <<'PY'
import sys
raise SystemExit(0 if float(sys.argv[1]) + 1e-9 >= float(sys.argv[2]) else 1)
PY
            if (( $? == 0 )); then
                gated=1
                echo "GATE 2 ms passed t=$latest dt=$dt"
            fi
        fi
        # A wide gas column in the first 2 ms is the old snap, not a slit.
        if python3 - "$latest" "$TGATE" <<'PY'
import sys
raise SystemExit(0 if float(sys.argv[1]) <= float(sys.argv[2]) + 1e-9 else 1)
PY
        then
            if "$PY" "$DIR/score_film.py" "$CASE" "$latest" | grep -q "width 0.1[5-9]\|width 0.[2-9]\|width [1-9]"; then
                echo "KILL wide gas column at t=$latest"
                kill -TERM "$pid" 2>/dev/null || true
                break
            fi
        fi
        scored="$latest"
        grep -E 'TrailDrag:' "$CASE/log.laserWireDEDFoam" | tail -1 || true
    done
    wait "$pid" || true
    drop_slots
    echo "DRAG_DONE"
}

main "$@"
