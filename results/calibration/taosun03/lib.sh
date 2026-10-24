# Shared helpers for TaoSun-03 calibration launches.
# Source from a bash script. Do not execute directly.
#
# CPU cap: half of the 64 physical cores. Another simulation already uses
# the other half. MPI ranks across every job, and wmake -j, stay at or under 32.
# Solvers are started with nice -n 10 by the launch scripts.

TAO_MAX_CORES=32
TAO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
TAO_OUT="$TAO_ROOT/results/calibration/taosun03"
TAO_PY="${TAO_PY:-/home/asb6102/lwded-viz/bin/python}"
TAO_SLOT_FILE="${TAO_SLOT_FILE:-/tmp/taosun03-lwded-slots}"
TAO_SLOT_LOCK="${TAO_SLOT_LOCK:-/tmp/taosun03-lwded-slots.lock}"
TAO_BUILD_LOCK="${TAO_BUILD_LOCK:-/tmp/taosun03-lwded-build.lock}"

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
