#!/bin/bash
# Unpainted settled neck. The wire contact line is no-slip on the feed,
# and the trailing force band is 0.30 mm so it covers the neck meniscus.
# Laser and recoil off. Marangoni on, so ppm changes sigma and the angle
# window. Feeds 18/24/28 mm/s, oxygen 50/100/300 ppm. 4 ranks, at most 8
# at once (32-rank cap). Stop a case at 2 ms if it runs away.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"

SRC="$TAO_ROOT/cases/wire_cavity_smokeS"
T0="0.7047"
PY="$TAO_PY"
NP=4
# 16 ms: 18 mm/s travels 0.29 mm, 28 mm/s travels 0.45 mm.
DT="0.016"
TEND="$(python3 -c "print(0.7047 + $DT)")"
TGATE="$(python3 -c 'print(0.7047 + 0.002)')"
FEEDS=(18 24 28)
PPMS=(50 100 300)

case_of() { echo "$TAO_ROOT/cases/wire_cavity_cl${1}p${2}"; }
log_of() { echo "$TAO_OUT/cl${1}p${2}.log"; }

prepare_one() {
    local feed_mm="$1" ppm="$2"
    local case
    case="$(case_of "$feed_mm" "$ppm")"
    if [[ -f "$case/constant/meltProperties" ]] && grep -q "wireDragK       1e9;" "$case/constant/meltProperties"; then
        echo "CASE f${feed_mm} p${ppm} exists"
        return 0
    fi
    echo "COPY f${feed_mm} p${ppm}"
    rm -rf "$case"
    mkdir -p "$case"
    rsync -a \
        --exclude 'processor*' --exclude 'log.*' \
        --exclude 'postProcessing' --exclude 'dynamicCode' \
        "$SRC/" "$case/"
    find "$case" -mindepth 1 -maxdepth 1 -type d -regextype posix-extended \
        -regex '.*/[0-9].*' -exec rm -rf {} +
    local p name
    for p in "$SRC"/processor*; do
        name="$(basename "$p")"
        mkdir -p "$case/$name/constant" "$case/$name/$T0"
        rsync -a "$p/constant/" "$case/$name/constant/"
        rsync -a "$p/$T0/" "$case/$name/$T0/"
    done
    python3 - "$case" "$T0" "$TEND" "$feed_mm" "$ppm" <<'PY'
import re, sys
from pathlib import Path
case, t0, tend, feed_mm, ppm = Path(sys.argv[1]), sys.argv[2], sys.argv[3], int(sys.argv[4]), int(sys.argv[5])
vz = -feed_mm / 1000.0
mp = case / "constant/meltProperties"
t = mp.read_text()
t = t.replace("    chamberOxygenPpm 100;", f"    chamberOxygenPpm {ppm};", 1)
t = t.replace("    feedVelocity    (-0 -0 -0.024);", f"    feedVelocity    (-0 -0 {vz:.3f});", 1)
t = t.replace("    tFeedStart      0.706;", f"    tFeedStart      {t0};", 1)
t = t.replace("    tFeedRamp       0.002;", "    tFeedRamp       0;", 1)
old = "    wireVelocity    head;   // head: kink fixed in the lab frame; wire: stuck to the feed"
new = "    wireVelocity    wire;\n    wireBand        0.0003;\n    wireDragK       1e9;"
if old not in t:
    raise SystemExit("wireVelocity line missing")
t = t.replace(old, new, 1)
i = t.find("laser   //")
j = t.find("\n}", i)
block = t[i:j].replace("enabled         true;", "enabled         false;", 1)
if block == t[i:j]:
    raise SystemExit("laser enabled line missing")
t = t[:i] + block + t[j:]
(case / "constant/meltProperties").write_text(t)
cd = case / "system/controlDict"
c = cd.read_text()
c, n = re.subn(r"(?m)^endTime\s+[0-9.eE+-]+;", f"endTime         {tend};", c, count=1)
if n != 1:
    raise SystemExit("endTime missing")
c, n = re.subn(r"(?m)^(writeInterval\s+)[0-9.eE+-]+;", r"\g<1>0.001;", c, count=1)
if n != 1:
    raise SystemExit("writeInterval missing")
cd.write_text(c)
print(f"PATCH f{feed_mm} p{ppm} Uz {vz:.3f} end {tend}")
PY
}

latest_time() {
    "$PY" - "$1" <<'PY'
import sys
from pathlib import Path
root = Path(sys.argv[1]) / "processor0"
names = []
for p in root.iterdir():
    if p.is_dir():
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
    local feed_mm="$1" ppm="$2"
    local case log
    case="$(case_of "$feed_mm" "$ppm")"
    log="$(log_of "$feed_mm" "$ppm")"
    local held=0
    release() {
        if (( held > 0 )); then tao_release "$held"; held=0; fi
    }
    trap release EXIT
    tao_acquire "$NP"
    held=$NP
    (
        cd "$case"
        exec nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
            laserWireDEDFoam -parallel > "$case/log.laserWireDEDFoam" 2>&1
    ) &
    local pid=$!
    echo "PID f${feed_mm} p${ppm} $pid"
    local scored="" gated=0
    while kill -0 "$pid" 2>/dev/null; do
        sleep 20
        if grep -q "FOAM FATAL" "$case/log.laserWireDEDFoam" 2>/dev/null; then
            echo "KILL f${feed_mm}p${ppm} foam fatal"
            kill -TERM "$pid" 2>/dev/null || true
            break
        fi
        local latest=""
        latest="$(latest_time "$case")" || latest=""
        if [[ -z "$latest" || "$latest" == "$scored" ]]; then
            grep -E 'ContactLine:|deltaT = ' "$case/log.laserWireDEDFoam" | tail -1 || true
            continue
        fi
        echo "SCORE f${feed_mm}p${ppm} t=$latest"
        "$PY" "$DIR/score_film.py" "$case" "$latest" || true
        local rc=0
        "$PY" "$DIR/neck_state.py" "$case" "$latest" --calm-max 15 || rc=$?
        if (( rc == 3 )); then
            echo "KILL f${feed_mm}p${ppm} violent neck at t=$latest"
            kill -TERM "$pid" 2>/dev/null || true
            break
        fi
        local dt=""
        dt="$(grep '^deltaT = ' "$case/log.laserWireDEDFoam" | tail -1 | awk '{print $3}' || true)"
        if [[ -n "$dt" ]]; then
            python3 - "$dt" "$latest" "$TGATE" <<'PY' || {
import sys
try:
    dt = float(sys.argv[1])
except ValueError:
    raise SystemExit(0)
t = float(sys.argv[2]); gate = float(sys.argv[3])
if t + 1e-9 >= gate and dt < 1.5e-7:
    raise SystemExit(1)
raise SystemExit(0)
PY
                echo "KILL f${feed_mm}p${ppm} timestep collapse dt=$dt at t=$latest"
                kill -TERM "$pid" 2>/dev/null || true
                break
            }
        fi
        if (( gated == 0 )); then
            local gate_rc=0
            python3 - "$latest" "$TGATE" <<'PY' || gate_rc=$?
import sys
raise SystemExit(0 if float(sys.argv[1]) + 1e-9 >= float(sys.argv[2]) else 1)
PY
            if (( gate_rc == 0 )); then
                gated=1
                echo "GATE f${feed_mm}p${ppm} 2 ms passed t=$latest dt=$dt"
            fi
        fi
        if python3 - "$latest" "$TGATE" <<'PY'
import sys
raise SystemExit(0 if float(sys.argv[1]) <= float(sys.argv[2]) + 1e-9 else 1)
PY
        then
            if "$PY" "$DIR/score_film.py" "$case" "$latest" | grep -q "width 0.1[5-9]\|width 0.[2-9]\|width [1-9]"; then
                echo "KILL f${feed_mm}p${ppm} wide gas column at t=$latest"
                kill -TERM "$pid" 2>/dev/null || true
                break
            fi
        fi
        scored="$latest"
        grep "zWire" "$case/log.laserWireDEDFoam" | tail -1 || true
    done
    wait "$pid" || true
    release
    echo "CL_DONE f${feed_mm}p${ppm}"
}

main() {
    local f p
    for f in "${FEEDS[@]}"; do
        for p in "${PPMS[@]}"; do
            prepare_one "$f" "$p"
        done
    done
    tao_source_foam
    tao_build
    # 4 ranks x 8 jobs = 32. The ninth waits for a free slot inside tao_acquire,
    # so all nine can be launched; the acquire loop blocks the last one.
    for f in "${FEEDS[@]}"; do
        for p in "${PPMS[@]}"; do
            run_one "$f" "$p" > "$(log_of "$f" "$p")" 2>&1 &
        done
    done
    wait || true
    echo "CLSWEEP_DONE"
}

main "$@"
