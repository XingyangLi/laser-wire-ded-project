#!/bin/bash
# Metal-region pinned line on the unpainted settled neck.
# Nine cases: feed 18/24/28 mm/s by oxygen 50/100/300 ppm.
# Laser off, recoil off, Marangoni on. The trailing shell is held wet
# below a line that moves at the feed speed, and dry above that line.
# The pool outside the shell is free.
# td24_p100 writes every 0.36 ms so a 5 fps encode is about 10 s.
# The other eight write every 1 ms for the width/depth table.
# Each case is its own 4-rank mpirun, nice 10, pinned to four physical
# cores. Eight run at once (32 cores). The ninth waits for a free set.
# Stop that case only, once the first 1 ms is clearly off: fatal, alpha
# above 1.05, a collapsed step, a violent neck, or a wide gas column.
# A width of 0 is not a stop.
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
            echo "CASE exists td${feed}_p${ppm}; resetting times after $T0"
            find "$CASE" -mindepth 2 -maxdepth 2 -type d -regextype posix-extended \
                -regex '.*/[0-9].*' ! -name "$T0" -exec rm -rf {} +
            rm -f "$CASE/log.laserWireDEDFoam"
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
    local CASE tag cores="" rf="" wrc=0
    CASE="$(case_dir "$feed" "$ppm")"
    tag="td${feed}_p${ppm}"
    release() {
        if [[ -n "${cores:-}" ]]; then
            tao_release_cores "$cores" || true
            cores=""
        fi
        rm -f "${rf:-}"
    }
    trap release EXIT
    cores="$(tao_acquire_cores "$NP")"
    rf="$(mktemp /tmp/taosun03-rf-XXXXXX)"
    tao_write_rankfile "$cores" "$rf"
    echo "START $tag cores $cores"
    (
        cd "$CASE"
        exec nice -n 10 stdbuf -oL -eL mpirun --bind-to core -rf "$rf" -np "$NP" \
            laserWireDEDFoam -parallel > "$CASE/log.laserWireDEDFoam" 2>&1
    ) &
    local pid=$!
    echo "PID $tag $pid"
    tao_watch_case "$pid" "$CASE" "$CASE/log.laserWireDEDFoam" "$T0" "$tag" \
        "$PY" "$DIR/score_film.py" "$DIR/neck_state.py" || wrc=$?
    wait "$pid" || true
    release
    if (( wrc == 2 || wrc == 0 )); then
        return 0
    fi
    return 1
}

main() {
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
    echo "PINLINE_DONE"
    exit "$rc"
}

main "$@"
