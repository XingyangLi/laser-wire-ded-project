#!/bin/bash
# Oxide on the trailing neck, unpainted, no trailDrag.
# Feed 24 mm/s, 10 ms from the settled neck, ppm 50/100/300.
# Two coverage laws, both with the membrane off (mu = 0, K = 0):
#   oxg  coverage grows on the exposed trailing surface
#   oxp  fixed trailing patch, coverage = min(ppm/300, 1)
# Either law scales sigma by (1 - 0.5*coverage) and blends the wire
# contact-angle window toward the oxide window. Alpha and velocity
# are not held. Laser off, recoil off, Marangoni on.
# Stop a case on a fatal error, alpha above 1.5, or a collapsed step.
# A width of 0 is a result, not a stop.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"

SRC="$TAO_ROOT/cases/wire_cavity_smokeS"
T0="0.7047"
PY="$TAO_PY"
NP=4
DUR="0.010"
TEND="$(python3 -c "print(float('$T0') + float('$DUR'))")"
TGATE="$(python3 -c "print(float('$T0') + 0.002)")"
ABORT="/tmp/taosun03-oxsurf-abort"
LOG="$TAO_OUT/oxsurf_launch.log"

# mode feed ppm   mode is grow or patch
CASES=(
    "grow 24 100"
    "grow 24 50"
    "grow 24 300"
    "patch 24 100"
    "patch 24 50"
    "patch 24 300"
)

case_dir() {
    local mode="$1" feed="$2" ppm="$3"
    local tag="oxg"
    if [[ "$mode" == "patch" ]]; then
        tag="oxp"
    fi
    echo "$TAO_ROOT/cases/wire_cavity_${tag}${feed}_p${ppm}"
}

prepare_case() {
    local mode="$1" feed="$2" ppm="$3"
    local CASE
    CASE="$(case_dir "$mode" "$feed" "$ppm")"
    local marker="oxsurf ${mode} feed ${feed} ppm ${ppm}"
    if [[ -d "$CASE/processor0/$T0" && -f "$CASE/constant/meltProperties" ]]; then
        if grep -q "$marker" "$CASE/constant/meltProperties"; then
            echo "CASE exists ${mode} ${feed} ${ppm}; resetting times after $T0"
            find "$CASE" -mindepth 2 -maxdepth 2 -type d -regextype posix-extended \
                -regex '.*/[0-9].*' ! -name "$T0" -exec rm -rf {} +
            rm -f "$CASE/log.laserWireDEDFoam"
            if ! grep -q "div(phi,oxideCoverage)" "$CASE/system/fvSchemes"; then
                sed -i '/div(phi,meltHistory)/a\    div(phi,oxideCoverage) Gauss upwind;' \
                    "$CASE/system/fvSchemes"
            fi
            return 0
        fi
    fi
    echo "COPY ${mode} ${feed} ${ppm} from smokeS t=$T0"
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
    local uz
    uz="$(python3 -c 'import sys; print(f"{-float(sys.argv[1])/1000:.6f}")' "$feed")"
    python3 - "$CASE" "$T0" "$TEND" "$ppm" "$uz" "$mode" "$marker" <<'PY'
import re, sys
from pathlib import Path
case, t0, tend, ppm, uz, mode, marker = sys.argv[1:]
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
t2, n = re.subn(r"(?m)^(\s*)wireSector\s+true;", r"\1wireSector      false;", t, count=1)
if n != 1:
    raise SystemExit("wireSector line missing")
t = t2
if not re.search(r"(?m)^\s*wireBand\s+", t):
    t2, n = re.subn(
        r"(?m)^(\s*wireVelocity\s+head;.*)$",
        r"\1\n    wireBand        0.0003;  // reach of the angle condition, not a velocity hold",
        t,
        count=1,
    )
    if n != 1:
        raise SystemExit("wireVelocity line missing")
    t = t2
t = re.sub(r"\ntrailDrag\b.*", "", t, count=1, flags=re.S)
t = re.sub(r"\noxideSkin\b.*", "", t, count=1, flags=re.S)
dyn = "true" if mode == "grow" else "false"
t += f"""
oxideSkin   // {marker}
// No painted film and no trailDrag. Coverage scales sigma and the
// wire angle window. mu and K stay 0, so there is no membrane damper.
{{
    enabled         true;
    surface         true;
    dynamic         {dyn};
    trailOnly       true;
    sigmaDrop       0.5;
    muSkin          0;
    Kskin           0;
    genTime         0.0005;
    leaveTime       0.0002;
    band            0.0003;
    sectorDeg       90;
    zMin            0.0004;
    zMax            0.0017;
    ppmRef          300;
    interval        50;
}}
"""
mp.write_text(t)
sch = Path(case) / "system/fvSchemes"
st = sch.read_text()
if "div(phi,oxideCoverage)" not in st:
    st2, n = re.subn(
        r"(?m)^(\s*div\(phi,meltHistory\)\s+Gauss upwind;)",
        r"\1\n    div(phi,oxideCoverage) Gauss upwind;",
        st,
        count=1,
    )
    if n != 1:
        raise SystemExit("meltHistory div scheme missing")
    sch.write_text(st2)
cd = Path(case) / "system/controlDict"
c = cd.read_text()
c2, n = re.subn(r"(?m)^endTime\s+[0-9.eE+-]+;", f"endTime         {tend};", c, count=1)
if n != 1:
    raise SystemExit("endTime missing")
c2, n = re.subn(
    r"(?m)^(writeInterval\s+)[0-9.eE+-]+;",
    r"\g<1>0.001;",
    c2,
    count=1,
)
if n != 1:
    raise SystemExit("writeInterval missing")
cd.write_text(c2)
print(f"PATCH {mode} feed {float(uz)*-1000:.0f} mm/s ppm {ppm} end {tend}")
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
    local mode="$1" feed="$2" ppm="$3"
    local CASE tag
    CASE="$(case_dir "$mode" "$feed" "$ppm")"
    local prefix="oxg"
    if [[ "$mode" == "patch" ]]; then
        prefix="oxp"
    fi
    tag="${prefix}${feed}_p${ppm}"
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
        sleep 30
        if [[ -f "$ABORT" ]]; then
            echo "KILL $tag abort file"
            kill -TERM "$pid" 2>/dev/null || true
            break
        fi
        if [[ -f "$CASE/log.laserWireDEDFoam" ]] && grep -qE "FOAM FATAL|Signal: Floating point exception" "$CASE/log.laserWireDEDFoam"; then
            echo "KILL $tag foam fatal"
            echo "$tag foam fatal" > "$ABORT"
            kill -TERM "$pid" 2>/dev/null || true
            break
        fi
        local amax=""
        amax="$(grep 'Max(alpha.metal)' "$CASE/log.laserWireDEDFoam" | tail -1 | sed -n 's/.*Max(alpha.metal) = //p' || true)"
        if [[ -n "$amax" ]]; then
            if python3 - "$amax" <<'PY'
import sys
raise SystemExit(0 if float(sys.argv[1]) > 1.5 else 1)
PY
            then
                echo "KILL $tag alpha max $amax"
                echo "$tag alpha max $amax" > "$ABORT"
                kill -TERM "$pid" 2>/dev/null || true
                break
            fi
        fi
        local dt_now=""
        dt_now="$(grep '^deltaT = ' "$CASE/log.laserWireDEDFoam" | tail -1 | awk '{print $3}' || true)"
        if [[ -n "$dt_now" ]] && python3 - "$dt_now" <<'PY'
import sys
raise SystemExit(0 if float(sys.argv[1]) < 1e-8 else 1)
PY
        then
            echo "KILL $tag timestep collapse dt=$dt_now"
            echo "$tag timestep collapse dt=$dt_now" > "$ABORT"
            kill -TERM "$pid" 2>/dev/null || true
            break
        fi
        local latest=""
        latest="$(latest_time "$CASE")" || latest=""
        if [[ -z "$latest" || "$latest" == "$scored" ]]; then
            grep -E 'OxideSurface:|deltaT = |FOAM FATAL' "$CASE/log.laserWireDEDFoam" | tail -1 || true
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
        if (( gated == 0 )); then
            local gate_rc=0
            python3 - "$latest" "$TGATE" <<'PY' || gate_rc=$?
import sys
raise SystemExit(0 if float(sys.argv[1]) + 1e-9 >= float(sys.argv[2]) else 1)
PY
            if (( gate_rc == 0 )); then
                gated=1
                echo "GATE $tag 2 ms passed t=$latest dt=$dt_now"
            fi
        fi
        scored="$latest"
        grep -E 'OxideSurface:' "$CASE/log.laserWireDEDFoam" | tail -1 || true
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
    local spec mode feed ppm
    for spec in "${CASES[@]}"; do
        # shellcheck disable=SC2086
        prepare_case $spec
    done
    tao_source_foam
    tao_build
    local pids=()
    for spec in "${CASES[@]}"; do
        # shellcheck disable=SC2086
        run_one $spec &
        pids+=($!)
    done
    local rc=0
    for pid in "${pids[@]}"; do
        wait "$pid" || rc=1
    done
    if [[ -f "$ABORT" ]]; then
        echo "OXSURF_ABORT $(cat "$ABORT")"
        exit 1
    fi
    echo "OXSURF_DONE"
    exit "$rc"
}

main "$@"
