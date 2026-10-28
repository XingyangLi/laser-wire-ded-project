#!/bin/bash
# Unpainted settled neck. Oxide coverage starts at 0 and grows only where
# the free surface is exposed. Laser on, recoil cap 5e4 Pa, Marangoni on,
# feed 24 mm/s. Stop at 2 ms if the neck runs away, the step collapses, or
# a wide gas column appears.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"

SRC="$TAO_ROOT/cases/wire_cavity_smokeS"
CASE="$TAO_ROOT/cases/wire_cavity_oxdyn"
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
    if [[ -f "$CASE/constant/meltProperties" ]] && grep -q "dynamic         true;" "$CASE/constant/meltProperties"; then
        echo "CASE exists"
        return 0
    fi
    echo "COPY oxdyn from smokeS t=$T0"
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
t = t.replace("    recoil      false;", "    recoil      true;", 1)
t = t.replace("    recoilMax   2e5;", "    recoilMax   5e4;", 1)
t = t.replace("    tFeedStart      0.706;", f"    tFeedStart      {t0};", 1)
t = t.replace("    tStart          0.706;", f"    tStart          {t0};", 1)
if "dynamic         true;" not in t:
    t += """
oxideSkin   // coverage starts at 0; generated on the exposed surface
{
    enabled         true;
    dynamic         true;
    genTime         0.001;
    leaveTime       0.0002;
    muSkin          20;
    Kskin           1e14;
    gapThreshold    0.0001;
    zMin            0.0003;
    zMax            0.00155;
    ppmRef          300;
    alphaGas        0.98;
}
"""
mp.write_text(t)
fv = case / "system/fvSchemes"
s = fv.read_text()
if "div(phi,oxideCoverage)" not in s:
    s = s.replace(
        "    div(phi,meltHistory) Gauss upwind;\n",
        "    div(phi,meltHistory) Gauss upwind;\n"
        "    div(phi,oxideCoverage) Gauss upwind;\n",
        1,
    )
    fv.write_text(s)
cd = case / "system/controlDict"
c = cd.read_text()
c2, n = re.subn(r"(?m)^endTime\s+[0-9.eE+-]+;", f"endTime         {tend};", c, count=1)
if n != 1:
    raise SystemExit("endTime missing")
c2, n = re.subn(
    r"(?m)^(writeInterval\s+)[0-9.eE+-]+;",
    r"\g<1>0.0002;",
    c2, count=1,
)
if n != 1:
    raise SystemExit("writeInterval missing")
cd.write_text(c2)
print(f"PATCH oxdyn t0 {t0} end {tend} laser on recoil cap 5e4 Marangoni on feed 24")
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

guard() {
    local pid="$1"
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
            grep -E 'OxideSkin:|deltaT = |FOAM FATAL' "$CASE/log.laserWireDEDFoam" | tail -1 || true
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
            local gate_rc=0
            python3 - "$latest" "$TGATE" <<'PY' || gate_rc=$?
import sys
raise SystemExit(0 if float(sys.argv[1]) + 1e-9 >= float(sys.argv[2]) else 1)
PY
            if (( gate_rc == 0 )); then
                gated=1
                echo "GATE 2 ms passed t=$latest dt=$dt"
            fi
        fi
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
        grep -E 'OxideSkin:' "$CASE/log.laserWireDEDFoam" | tail -1 || true
    done
    wait "$pid" || true
}

main() {
    prepare_case
    grep -q "dynamic         true;" "$CASE/constant/meltProperties"
    grep -q "div(phi,oxideCoverage)" "$CASE/system/fvSchemes"
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
    echo "PID oxdyn $pid"
    guard "$pid"
    drop_slots
    echo "OXDYN_DONE"
}

main "$@"
