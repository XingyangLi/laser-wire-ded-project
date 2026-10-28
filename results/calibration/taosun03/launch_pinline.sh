#!/bin/bash
# Metal-region pinned line on the unpainted settled neck.
# Nine cases: feed 18/24/28 mm/s by oxygen 50/100/300 ppm.
# Laser off, recoil off, Marangoni on. The trailing shell is held wet
# below a line that moves at the feed speed, and dry above that line.
# The pool outside the shell is free.
# td24_p100 writes every 0.36 ms so a 5 fps encode is about 10 s.
# The other eight write every 1 ms for the width/depth table.
# Stop a case (and the rest) if the 2 ms sample is a wide column, the
# neck runs away, or the swept face is still metal.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"

SRC="$TAO_ROOT/cases/wire_cavity_smokeS"
T0="0.7047"
PY="$TAO_PY"
NP=4
DUR="0.018"
TEND="$(python3 -c "print(float('$T0') + float('$DUR'))")"
TGATE="$(python3 -c "print(float('$T0') + 0.002)")"
ABORT="/tmp/taosun03-pinline-abort"
LOG="$TAO_OUT/pinline_launch.log"

# feed_mm_s ppm
CASES=(
    "24 100"
    "18 50"
    "18 100"
    "18 300"
    "24 50"
    "24 300"
    "28 50"
    "28 100"
    "28 300"
)

case_dir() {
    local feed="$1" ppm="$2"
    echo "$TAO_ROOT/cases/wire_cavity_td${feed}_p${ppm}"
}

write_iv() {
    local feed="$1" ppm="$2"
    if [[ "$feed" == "24" && "$ppm" == "100" ]]; then
        echo "0.00036"
    else
        echo "0.001"
    fi
}

prepare_case() {
    local feed="$1" ppm="$2"
    local CASE
    CASE="$(case_dir "$feed" "$ppm")"
    local marker="pinline feed ${feed} ppm ${ppm}"
    if [[ -d "$CASE/processor0/$T0" && -f "$CASE/constant/meltProperties" ]]; then
        if grep -q "$marker" "$CASE/constant/meltProperties"; then
            echo "CASE exists td${feed}_p${ppm}"
            return 0
        fi
    fi
    echo "COPY td${feed}_p${ppm} from smokeS t=$T0"
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
    local iv uz
    iv="$(write_iv "$feed" "$ppm")"
    uz="$(python3 -c 'import sys; print(f"{-float(sys.argv[1])/1000:.6f}")' "$feed")"
    python3 - "$CASE" "$T0" "$TEND" "$ppm" "$uz" "$iv" "$marker" <<'PY'
import re, sys
from pathlib import Path
case, t0, tend, ppm, uz, iv, marker = sys.argv[1:]
mp = Path(case) / "constant/meltProperties"
t = mp.read_text()
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
old_feed = "    feedVelocity    (-0 -0 -0.024);"
new_feed = f"    feedVelocity    (0 0 {uz});"
if old_feed not in t:
    raise SystemExit("feedVelocity line missing")
t = t.replace(old_feed, new_feed, 1)
old_ppm = "    chamberOxygenPpm 100;"
new_ppm = f"    chamberOxygenPpm {ppm};"
if old_ppm not in t:
    raise SystemExit("chamberOxygenPpm line missing")
t = t.replace(old_ppm, new_ppm, 1)
if "marangoni           true;" not in t:
    raise SystemExit("Marangoni is not on")
if "recoil      false;" not in t:
    raise SystemExit("recoil is not off")
# Drop a previous trailDrag block if a partial copy left one.
t = re.sub(r"\ntrailDrag\b.*", "", t, count=1, flags=re.S)
t += f"""
trailDrag   // {marker}
// Wet shell below the moving line, dry face above it.
// Pool outside the shell is free. Marangoni stays on.
{{
    enabled         true;
    radialCells     3;
    axialCells      3;
    sectorDeg       75;
}}
"""
mp.write_text(t)
cd = Path(case) / "system/controlDict"
c = cd.read_text()
c2, n = re.subn(r"(?m)^endTime\s+[0-9.eE+-]+;", f"endTime         {tend};", c, count=1)
if n != 1:
    raise SystemExit("endTime missing")
c2, n = re.subn(
    r"(?m)^(writeInterval\s+)[0-9.eE+-]+;",
    rf"\g<1>{iv};",
    c2, count=1,
)
if n != 1:
    raise SystemExit("writeInterval missing")
cd.write_text(c2)
print(f"PATCH td feed {float(uz)*-1000:.0f} mm/s ppm {ppm} end {tend} write {iv}")
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

run_one() {
    local feed="$1" ppm="$2"
    local CASE tag
    CASE="$(case_dir "$feed" "$ppm")"
    tag="td${feed}_p${ppm}"
    local held=0
    release() {
        if (( held > 0 )); then tao_release "$held"; held=0; fi
    }
    trap release EXIT
    tao_acquire "$NP"
    held=$NP
    echo "START $tag"
    (
        cd "$CASE"
        exec nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
            laserWireDEDFoam -parallel > "$CASE/log.laserWireDEDFoam" 2>&1
    ) &
    local pid=$!
    echo "PID $tag $pid"
    local scored="" gated=0
    while kill -0 "$pid" 2>/dev/null; do
        sleep 20
        if [[ -f "$ABORT" ]]; then
            echo "KILL $tag abort file"
            kill -TERM "$pid" 2>/dev/null || true
            break
        fi
        if [[ -f "$CASE/log.laserWireDEDFoam" ]] && grep -q "FOAM FATAL" "$CASE/log.laserWireDEDFoam"; then
            echo "KILL $tag foam fatal"
            echo "$tag foam fatal" > "$ABORT"
            kill -TERM "$pid" 2>/dev/null || true
            break
        fi
        local latest=""
        latest="$(latest_time "$CASE")" || latest=""
        if [[ -z "$latest" || "$latest" == "$scored" ]]; then
            grep -E 'TrailDrag:|deltaT = |FOAM FATAL' "$CASE/log.laserWireDEDFoam" | tail -1 || true
            continue
        fi
        echo "SCORE $tag t=$latest"
        "$PY" "$DIR/score_film.py" "$CASE" "$latest" || true
        local rc=0
        "$PY" "$DIR/neck_state.py" "$CASE" "$latest" --calm-max 15 || rc=$?
        if (( rc == 3 )); then
            echo "KILL $tag violent neck at t=$latest"
            echo "$tag violent neck at $latest" > "$ABORT"
            kill -TERM "$pid" 2>/dev/null || true
            break
        fi
        local dt=""
        dt="$(grep '^deltaT = ' "$CASE/log.laserWireDEDFoam" | tail -1 | awk '{print $3}' || true)"
        if [[ -z "$dt" ]]; then
            scored="$latest"
            continue
        fi
        if ! python3 - "$dt" "$latest" "$TGATE" <<'PY'
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
        then
            echo "KILL $tag timestep collapse dt=$dt at t=$latest"
            echo "$tag timestep collapse at $latest" > "$ABORT"
            kill -TERM "$pid" 2>/dev/null || true
            break
        fi
        local gate_rc=0
        python3 - "$latest" "$TGATE" <<'PY' || gate_rc=$?
import sys
raise SystemExit(0 if float(sys.argv[1]) + 1e-9 >= float(sys.argv[2]) else 1)
PY
        if (( gate_rc == 0 )); then
            if (( gated == 0 )); then
                gated=1
                echo "GATE $tag 2 ms passed t=$latest dt=$dt"
            fi
            local line=""
            line="$("$PY" "$DIR/score_film.py" "$CASE" "$latest" | head -1 || true)"
            echo "CHECK $tag $line"
            if echo "$line" | grep -q "width 0.1[5-9]\|width 0.[2-9]\|width [1-9]"; then
                echo "KILL $tag wide gas column at t=$latest"
                echo "$tag wide column at $latest" > "$ABORT"
                kill -TERM "$pid" 2>/dev/null || true
                break
            fi
            # The swept face should be a measurable gap by 2 ms.
            # Width 0 means the line moved inside solid metal again.
            if echo "$line" | grep -q "width 0.000"; then
                echo "KILL $tag no gap at t=$latest"
                echo "$tag no gap at $latest" > "$ABORT"
                kill -TERM "$pid" 2>/dev/null || true
                break
            fi
        fi
        scored="$latest"
        grep -E 'TrailDrag:' "$CASE/log.laserWireDEDFoam" | tail -1 || true
    done
    wait "$pid" || true
    release
    echo "DONE $tag"
}

main() {
    rm -f "$ABORT"
    mkdir -p "$TAO_OUT"
    : > "$LOG"
    exec > >(tee -a "$LOG") 2>&1
    local pair feed ppm
    for pair in "${CASES[@]}"; do
        # shellcheck disable=SC2086
        prepare_case $pair
    done
    tao_source_foam
    tao_build
    local CASE
    CASE="$(case_dir 24 100)"
    "$PY" "$DIR/score_film.py" "$CASE" "$T0" || true
    local pids=()
    for pair in "${CASES[@]}"; do
        # shellcheck disable=SC2086
        run_one $pair &
        pids+=($!)
    done
    local rc=0
    for pid in "${pids[@]}"; do
        wait "$pid" || rc=1
    done
    if [[ -f "$ABORT" ]]; then
        echo "PINLINE_ABORT $(cat "$ABORT")"
        exit 1
    fi
    echo "PINLINE_DONE"
    exit "$rc"
}

main "$@"
