#!/bin/bash
# Restart the two full-track oxide-skin cases from the painted field and
# write the volume every 0.1 ms through 20 ms.
#
# 200 frames at 20 fps is 10 s. skincold keeps the laser and recoil off.
# skinfull keeps both on, so the clip can show the slit open and then close.
# Four ranks each. A 32-way split of this neck was about 10 s/step.
#
#   bash launch_dense_demos.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"

PY="$TAO_PY"
NP=4
HELD=0

hold_slots() {
    tao_acquire "$1"
    HELD=$1
}

drop_slots() {
    if (( HELD > 0 )); then
        tao_release "$HELD"
        HELD=0
    fi
}

trap drop_slots EXIT

arm_case() {
    local case="$1"
    if [[ ! -d "$case/processor0/0" ]]; then
        echo "missing painted time 0 in $case" >&2
        exit 1
    fi
    python3 - "$case" <<'PY'
import shutil, sys
from pathlib import Path
case = Path(sys.argv[1])
roots = [case, *sorted(case.glob("processor*"))]
for root in roots:
    if not root.is_dir():
        continue
    for d in root.iterdir():
        if not d.is_dir():
            continue
        try:
            tv = float(d.name)
        except ValueError:
            continue
        if tv > 1e-12:
            shutil.rmtree(d)
            print("removed", d)
PY
    python3 - "$case/system/controlDict" <<'PY'
import re, sys
from pathlib import Path
p = Path(sys.argv[1])
t = p.read_text()
t2, n = re.subn(
    r"(?m)^endTime\s+[0-9.eE+-]+;",
    "endTime         0.020;",
    t,
    count=1,
)
if n != 1:
    raise SystemExit("endTime not patched")
t2, n = re.subn(
    r"(writeControl    adjustable;\n\nwriteInterval\s+)[0-9.eE+-]+;",
    r"\g<1>0.0001;",
    t2,
    count=1,
)
if n != 1:
    raise SystemExit("volume writeInterval not patched")
t2, n = re.subn(
    r"(writeControl    adjustableRunTime;\n\s*writeInterval\s+)[0-9.eE+-]+;",
    r"\g<1>0.020;",
    t2,
    count=1,
)
if n != 1:
    raise SystemExit("side-plane writeInterval not patched")
if "startFrom       latestTime;" not in t2:
    raise SystemExit("startFrom is not latestTime")
p.write_text(t2)
print("controlDict", p, "end 0.020 write 0.0001")
PY
    if compgen -G "$case/processor0/0.*" >/dev/null; then
        echo "later times still present in $case" >&2
        exit 1
    fi
    "$PY" "$DIR/score_film.py" "$case" 0
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

note_case() {
    local name="$1" pid="$2" case="$3" log="$4"
    local scored_var="$5"
    if [[ -f "$log" ]] && grep -q "FOAM FATAL" "$log"; then
        echo "KILL $name foam fatal"
        kill -TERM "$pid" 2>/dev/null || true
    fi
    local latest=""
    latest="$(latest_time "$case")" || latest=""
    local prev="${!scored_var}"
    if [[ -n "$latest" && "$latest" != "0" && "$latest" != "$prev" ]]; then
        echo "SCORE $name t=$latest"
        "$PY" "$DIR/score_film.py" "$case" "$latest" || true
        printf -v "$scored_var" '%s' "$latest"
    fi
    if [[ -f "$log" ]]; then
        echo "-- $name --"
        grep -E '^Time = |OxideSkin: cells|laser: incident' "$log" | tail -2 || true
    fi
}

main() {
    local cold="$TAO_ROOT/cases/wire_cavity_skincold"
    local full="$TAO_ROOT/cases/wire_cavity_skinfull"
    echo "ARM dense demos $(date --iso-8601=seconds)"
    arm_case "$cold"
    arm_case "$full"
    grep -q "recoil      false;" "$cold/constant/meltProperties"
    grep -q "enabled         false;" "$cold/constant/meltProperties"
    grep -q "recoil      true;" "$full/constant/meltProperties"
    grep -q "tStart          0;" "$full/constant/meltProperties"
    tao_source_foam
    hold_slots 8
    (
        cd "$cold"
        exec nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
            laserWireDEDFoam -parallel > "$cold/log.laserWireDEDFoam" 2>&1
    ) &
    local pc=$!
    (
        cd "$full"
        exec nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
            laserWireDEDFoam -parallel > "$full/log.laserWireDEDFoam" 2>&1
    ) &
    local pf=$!
    echo "PIDS cold $pc full $pf"
    local scored_c="" scored_f=""
    while kill -0 "$pc" 2>/dev/null || kill -0 "$pf" 2>/dev/null; do
        sleep 30
        if kill -0 "$pc" 2>/dev/null; then
            note_case cold "$pc" "$cold" "$cold/log.laserWireDEDFoam" scored_c
        fi
        if kill -0 "$pf" 2>/dev/null; then
            note_case full "$pf" "$full" "$full/log.laserWireDEDFoam" scored_f
        fi
    done
    wait "$pc" || true
    wait "$pf" || true
    drop_slots
    echo "DENSE_DEMOS_DONE"
}

main "$@"
