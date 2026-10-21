#!/bin/bash
# Oxygen sweep for the three-laser wire-cavity case.
#
#   ./scripts/sweep_wire_cavity_oxygen.sh --smoke
#   ./scripts/sweep_wire_cavity_oxygen.sh --smoke 10 1000
#   ./scripts/sweep_wire_cavity_oxygen.sh --np 24
#   ./scripts/sweep_wire_cavity_oxygen.sh --np 24 --wire-refine 3 --wire-refine-z
#   ./scripts/sweep_wire_cavity_oxygen.sh --generate-only
#
# Default levels: 10, 100, 500, 1000 ppm by weight (uniform melt oxygen).
# Each level is a separate case:
#   cases/wire_cavity_ox<ppm>            full track
#   cases/wire_cavity_smoke_ox<ppm>      --smoke
#
# The full track is hours per level on TaoSun-01. --wire-refine 3 --wire-refine-z
# (about 19 um in the wire box) is much longer. This script does not start a
# sweep unless you run it. Pass --generate-only to write the cases and stop.
#
# After the runs, scripts/compare_oxygen_sweep.py plots cavity volume and
# bubble count (porosity entrapment) against time.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SMOKE=0
GEN_ONLY=0
NP="${NP:-}"
WIRE_REFINE=""
REFINE_Z=0
LEVELS=()

usage() {
    sed -n '2,20p' "$0" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --smoke) SMOKE=1; shift ;;
        --generate-only) GEN_ONLY=1; shift ;;
        --np) NP="${2:?--np needs a core count}"; shift 2 ;;
        --wire-refine) WIRE_REFINE="${2:?--wire-refine needs a level count}"; shift 2 ;;
        --wire-refine-z) REFINE_Z=1; shift ;;
        -h|--help) usage; exit 0 ;;
        --) shift; break ;;
        *) LEVELS+=("$1"); shift ;;
    esac
done
if [[ $# -gt 0 ]]; then
    LEVELS+=("$@")
fi
if [[ ${#LEVELS[@]} -eq 0 ]]; then
    LEVELS=(10 100 500 1000)
fi

cd "$ROOT"
ARGS=()
if [[ -n "$NP" ]]; then
    ARGS+=(--np "$NP")
fi
if [[ "$SMOKE" == 1 ]]; then
    ARGS+=(--smoke)
fi
if [[ "$GEN_ONLY" == 1 ]]; then
    ARGS+=(--generate-only)
fi
if [[ -n "$WIRE_REFINE" ]]; then
    ARGS+=(--wire-refine "$WIRE_REFINE")
fi
if [[ "$REFINE_Z" == 1 ]]; then
    ARGS+=(--wire-refine-z)
fi

echo "Oxygen sweep levels: ${LEVELS[*]}"
if [[ "$SMOKE" == 1 ]]; then
    echo "Mode: smoke (8 ms). Not a bead prediction."
elif [[ "$GEN_ONLY" == 1 ]]; then
    echo "Mode: generate only. Not solving."
else
    echo "Mode: FULL wire-cavity track. Hours per level on TaoSun-01."
    echo "Stop now if that is not what you meant. Ctrl-C in the next 5 seconds."
    sleep 5
fi

for ppm in "${LEVELS[@]}"; do
    echo "======== oxygen ${ppm} ppm ========"
    ./scripts/run_wire_cavity.sh "${ARGS[@]}" --oxygen-ppm "$ppm"
done

if [[ "$GEN_ONLY" == 1 ]]; then
    echo "Cases written. Not comparing (no time series yet)."
    exit 0
fi

if [[ "$SMOKE" == 1 ]]; then
    GLOB=(cases/wire_cavity_smoke_ox*)
else
    GLOB=(cases/wire_cavity_ox*)
fi
python3 "$ROOT/scripts/compare_oxygen_sweep.py" --cases "${GLOB[@]}" \
    --out "$ROOT/results/oxygen_sweep"
echo "Comparison: $ROOT/results/oxygen_sweep"
