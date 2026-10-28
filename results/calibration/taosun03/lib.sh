# Shared helpers for TaoSun-03 calibration launches.
# Source from a bash script. Do not execute directly.
#
# CPU cap: half of the 64 physical cores. Another simulation already uses
# the other half. MPI ranks across every job, and wmake -j, stay at or under 32.
# Solvers are started with nice -n 10 by the launch scripts.
# Matrix cases are separate mpiruns of 4-6 ranks. Each job is pinned to its
# own physical cores in 0-31. OpenMPI otherwise starts every mpirun on core 0,
# so several jobs share the first cores and run like one job.

TAO_MAX_CORES=32
TAO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TAO_OUT="$TAO_ROOT/results/calibration/taosun03"
TAO_PY="${TAO_PY:-/home/asb6102/lwded-viz/bin/python}"
TAO_SLOT_FILE="${TAO_SLOT_FILE:-/tmp/taosun03-lwded-slots}"
TAO_SLOT_LOCK="${TAO_SLOT_LOCK:-/tmp/taosun03-lwded-slots.lock}"
TAO_BUILD_LOCK="${TAO_BUILD_LOCK:-/tmp/taosun03-lwded-build.lock}"
# Physical core indices currently held, one per line. The pool is 0..31.
TAO_CPU_FILE="${TAO_CPU_FILE:-/tmp/taosun03-lwded-cpus}"
TAO_PHYS_CORES=32

export WM_NCOMPPROCS="$TAO_MAX_CORES"
export OMP_NUM_THREADS=1
unset MAKEFLAGS || true

tao_source_foam() {
    set +euo pipefail
    # shellcheck disable=SC1091
    source /usr/lib/openfoam/openfoam2406/etc/bashrc
    set -euo pipefail
    export WM_NCOMPPROCS="$TAO_MAX_CORES"
    export OMP_NUM_THREADS=1
    unset MAKEFLAGS || true
    export PATH="${FOAM_USER_APPBIN}:$PATH"
    hash -r
}

# One build at a time, on at most TAO_MAX_CORES cores.
tao_build() {
    (
        flock 9
        cd "$TAO_ROOT/solver"
        tao_source_foam
        ./Allwmake
    ) 9>"$TAO_BUILD_LOCK"
}

tao_acquire() {
    local n="$1"
    if (( n < 1 || n > TAO_MAX_CORES )); then
        echo "refusing ${n} ranks; cap is ${TAO_MAX_CORES} physical cores" >&2
        exit 1
    fi
    while true; do
        local rc=0
        (
            flock -w 120 9 || exit 1
            local used=0
            if [[ -f "$TAO_SLOT_FILE" ]]; then
                used="$(cat "$TAO_SLOT_FILE")"
            fi
            if (( used + n <= TAO_MAX_CORES )); then
                echo $((used + n)) > "$TAO_SLOT_FILE"
                exit 0
            fi
            echo "slots in use: ${used}; waiting for ${n} (cap ${TAO_MAX_CORES})" >&2
            exit 2
        ) 9>"$TAO_SLOT_LOCK" || rc=$?
        if (( rc == 0 )); then
            echo "acquired ${n} MPI slots (cap ${TAO_MAX_CORES})"
            return 0
        fi
        if (( rc != 2 )); then
            echo "MPI slot lock failed (rc ${rc})" >&2
            exit 1
        fi
        sleep 20
    done
}

tao_release() {
    local n="$1"
    (
        flock -w 120 9 || exit 1
        local used=0
        if [[ -f "$TAO_SLOT_FILE" ]]; then
            used="$(cat "$TAO_SLOT_FILE")"
        fi
        local left=$((used - n))
        if (( left < 0 )); then
            left=0
        fi
        echo "$left" > "$TAO_SLOT_FILE"
        echo "released ${n} MPI slots; ${left} still held" >&2
    ) 9>"$TAO_SLOT_LOCK"
}

# Take n physical cores from 0..31. Prints a comma list on stdout.
# Blocks while fewer than n are free. n is 4, 5 or 6: one small job.
tao_acquire_cores() {
    local n="$1"
    if (( n < 4 || n > 6 )); then
        echo "refusing ${n} ranks; a matrix job is 4-6" >&2
        exit 1
    fi
    while true; do
        local out="" rc=0 outf
        outf="$(mktemp)"
        (
            flock -w 120 9 || exit 1
            python3 - "$n" "$TAO_CPU_FILE" "$TAO_SLOT_FILE" "$TAO_PHYS_CORES" <<'PY'
import sys
from pathlib import Path
n = int(sys.argv[1])
cpu = Path(sys.argv[2])
slot = Path(sys.argv[3])
cap = int(sys.argv[4])
held = []
if cpu.is_file():
    held = [int(x) for x in cpu.read_text().split() if x.strip()]
used = 0
if slot.is_file() and slot.read_text().strip():
    used = int(slot.read_text().strip())
occupancy = max(used, len(held))
free = [i for i in range(cap) if i not in set(held)]
if occupancy + n > cap or len(free) < n:
    print(
        f"slots in use: {occupancy}; waiting for {n} (cap {cap})",
        file=sys.stderr,
    )
    sys.exit(2)
take = free[:n]
cpu.write_text("".join(f"{c}\n" for c in held + take))
slot.write_text(str(occupancy + n) + "\n")
print(",".join(str(c) for c in take))
PY
        ) 9>"$TAO_SLOT_LOCK" >"$outf" || rc=$?
        out="$(cat "$outf")"
        rm -f "$outf"
        if (( rc == 0 )); then
            echo "acquired ${n} cores: ${out}" >&2
            echo "$out"
            return 0
        fi
        if (( rc != 2 )); then
            echo "core lock failed (rc ${rc})" >&2
            exit 1
        fi
        sleep 15
    done
}

# Return cores taken by tao_acquire_cores. Argument is the comma list.
tao_release_cores() {
    local csv="$1"
    (
        flock -w 120 9 || exit 1
        python3 - "$csv" "$TAO_CPU_FILE" "$TAO_SLOT_FILE" <<'PY'
import sys
from pathlib import Path
drop = {int(x) for x in sys.argv[1].split(",") if x.strip()}
cpu = Path(sys.argv[2])
slot = Path(sys.argv[3])
held = []
if cpu.is_file():
    held = [int(x) for x in cpu.read_text().split() if x.strip()]
left = [c for c in held if c not in drop]
cpu.write_text("".join(f"{c}\n" for c in left))
slot.write_text(str(len(left)) + "\n")
print(f"released cores {sys.argv[1]}; {len(left)} still held", file=sys.stderr)
PY
    ) 9>"$TAO_SLOT_LOCK"
}

# Rankfile that pins one rank to each physical core in the comma list.
tao_write_rankfile() {
    local csv="$1" dest="$2" host rank=0 c
    host="$(hostname)"
    : > "$dest"
    IFS=',' read -ra cores <<< "$csv"
    for c in "${cores[@]}"; do
        printf 'rank %s=%s slot=%s\n' "$rank" "$host" "$c" >> "$dest"
        rank=$((rank + 1))
    done
}

# Empty stdout if the log is healthy. Otherwise one line: why to stop.
# A width of 0 is not a reason. Fatal, alpha above 1.05, and a collapsed
# step are. The step check uses 1e-7 only after t0 + 1 ms.
tao_log_stop_reason() {
    local log="$1" t0="$2"
    [[ -f "$log" ]] || return 0
    python3 - "$log" "$t0" <<'PY'
import re, sys
from pathlib import Path
text = Path(sys.argv[1]).read_text(errors="replace")
t0 = float(sys.argv[2])
fatal = ""
alpha = ""
last_t = t0
last_dt = None
last_dt_t = t0
for line in text.splitlines():
    if "trapFpe" in line:
        continue
    if line.startswith("Time ="):
        try:
            last_t = float(line.split()[2])
        except (IndexError, ValueError):
            pass
        continue
    if "FOAM FATAL" in line or "Signal: Floating point exception" in line:
        fatal = "solver fatal"
        continue
    if "Max(alpha.metal)" in line:
        m = re.search(r"Max\(alpha\.metal\) = ([0-9.eE+-]+)", line)
        if m and float(m.group(1)) > 1.05:
            alpha = "alpha " + m.group(1)
        continue
    if line.startswith("deltaT ="):
        try:
            last_dt = float(line.split()[2])
            last_dt_t = last_t
        except (IndexError, ValueError):
            pass
reason = fatal or alpha
if not reason and last_dt is not None:
    if last_dt < 1e-8 or (last_dt_t >= t0 + 0.001 and last_dt < 1e-7):
        reason = f"timestep {last_dt}"
if reason:
    print(reason)
PY
}

# Watch one solver. Stop only that pid. Width 0 is kept.
# Prints STOP, DONE or FAIL. Returns 2, 0 or 1.
tao_watch_case() {
    local pid="$1" case_dir="$2" log="$3" t0="$4" tag="$5"
    local py="$6" score="$7" neck="$8"
    local scored="" reason="" latest="" line="" rc=0
    while kill -0 "$pid" 2>/dev/null; do
        sleep 10
        reason="$(tao_log_stop_reason "$log" "$t0" || true)"
        if [[ -n "$reason" ]]; then
            echo "STOP $tag $reason"
            kill -TERM "$pid" 2>/dev/null || true
            return 2
        fi
        latest=""
        if [[ -d "$case_dir/processor0" ]]; then
            latest="$(
                python3 - "$case_dir" <<'PY'
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
            )" || latest=""
        fi
        if [[ -z "$latest" || "$latest" == "$scored" ]]; then
            continue
        fi
        if python3 - "$latest" "$t0" <<'PY'
import sys
sys.exit(0 if float(sys.argv[1]) + 1e-12 >= float(sys.argv[2]) + 0.001 else 1)
PY
        then
            if [[ -n "$neck" && -f "$neck" ]]; then
                rc=0
                "$py" "$neck" "$case_dir" "$latest" --calm-max 15 || rc=$?
                if (( rc == 3 )); then
                    echo "STOP $tag violent neck at $latest"
                    kill -TERM "$pid" 2>/dev/null || true
                    return 2
                fi
            fi
            if [[ -n "$score" && -f "$score" ]]; then
                line="$("$py" "$score" "$case_dir" "$latest" 2>/dev/null | head -1 || true)"
                echo "CHECK $tag t=$latest $line"
                if echo "$line" | grep -q "width 0.1[5-9]\|width 0.[2-9]\|width [1-9]"; then
                    echo "STOP $tag wide column at $latest"
                    kill -TERM "$pid" 2>/dev/null || true
                    return 2
                fi
            fi
        fi
        scored="$latest"
    done
    if [[ -f "$log" ]] && grep -q '^End$' "$log"; then
        echo "DONE $tag"
        return 0
    fi
    echo "FAIL $tag exited before End"
    return 1
}

# cal08 domain, beams and pinning switches. Callers override speeds, powers and angles.
tao_cal08_case() {
    local case_dir="$1"
    shift
    python3 "$TAO_ROOT/generate_case.py" --case "$case_dir" \
        --laser-config triple \
        --wire-type solid --material 316L --resolution coarse --domain-y half \
        --upstream 4e-3 --downstream 7e-3 --half-width 3.5e-3 \
        --substrate-thickness 2e-3 --gas-height 3.5e-3 --gas-uniform-height 2.6e-3 \
        --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.08e-3 --feed-start 0.05 \
        --scan-speed 0.004 --wire-feed-speed 0.020 \
        --beam-azimuths 30,-30,180 \
        --beam-inclinations=-26,-26,-38 \
        --beam-powers 160,160,420 \
        --beam-radii-each 0.26e-3,0.26e-3,0.26e-3 \
        --beam-aim-radii 0.60e-3,0.60e-3,0.24e-3 \
        --beam-aim-heights 0.08e-3,0.08e-3,0.55e-3 \
        --laser-ramp 2e-3 \
        --contact-pinning --pin-wire --porosity --wire-cavity \
        --theta-receding 110 --theta-advancing 150 \
        --theta-receding-wire 30 --theta-advancing-wire 90 \
        --contact-force-factor 6 \
        --no-marangoni \
        --wire-pin-frame head \
        --rigid-substrate 100 \
        "$@"
}

tao_run() {
    local np="$1"
    local case_dir="$2"
    tao_assert_np "$np"
    tao_source_foam
    cd "$case_dir"
    ./Allclean >/dev/null 2>&1 || true
    nice -n 10 ./Allrun "$np"
}

tao_assert_np() {
    local np="$1"
    if (( np < 1 || np > TAO_MAX_CORES )); then
        echo "refusing Allrun ${np}; cap is ${TAO_MAX_CORES}" >&2
        exit 1
    fi
}

# Side view, projection, iso-surface, pore summary, radiograph panel.
tao_post() {
    local tag="$1"
    local case_dir="$2"
    mkdir -p "$TAO_OUT"
    if [[ -d "$case_dir/processor0" ]]; then
        tao_source_foam
        ( cd "$case_dir" && nice -n 10 reconstructPar -latestTime ) || true
    fi
    local py="$TAO_PY"
    if [[ ! -x "$py" ]]; then
        py="python3"
    fi
    "$py" "$TAO_ROOT/scripts/plot_calibration.py" \
        --case "$case_dir" --out "$TAO_OUT" --tag "$tag" --iso || true
    "$py" "$TAO_ROOT/scripts/project_alpha.py" \
        --case "$case_dir" --out "$TAO_OUT" --tag "$tag" || true
    "$py" "$TAO_ROOT/scripts/quantify_pores.py" --case "$case_dir" || true
    "$py" "$TAO_ROOT/results/calibration/make_comparison.py" "$tag" "$TAO_OUT" || true
}
