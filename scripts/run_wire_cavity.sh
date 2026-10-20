#!/bin/bash
# Three-laser vertical-wire case: source OpenFOAM.com, build, generate, run, summarise.
#
#   ./scripts/run_wire_cavity.sh                  # full track, one rank per core (nproc)
#   ./scripts/run_wire_cavity.sh --np 16
#   ./scripts/run_wire_cavity.sh --generate-only  # write the case and stop
#   ./scripts/run_wire_cavity.sh --smoke          # coarse 3D case, 8 ms, planted wake
#
# The full track is a melt-pool run (hours on a workstation). This script is what
# to launch on taosun01. It does not pick a reduced mesh unless --smoke is passed.
#
# OpenFOAM.com v2406 or v2412 is required (wmake). If neither is installed, the
# script prints Ubuntu install commands and exits.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NP="${NP:-}"
MODE="full"
GEN_ONLY=0

usage() {
    sed -n '2,12p' "$0" | sed 's/^# \{0,1\}//'
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --np) NP="${2:?--np needs a core count}"; shift 2 ;;
        --smoke) MODE="smoke"; shift ;;
        --generate-only) GEN_ONLY=1; shift ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Unknown argument: $1" >&2; usage >&2; exit 1 ;;
    esac
done
if [[ -z "$NP" ]]; then
    NP="$(nproc)"
fi
if ! [[ "$NP" =~ ^[1-9][0-9]*$ ]]; then
    echo "--np must be a positive integer, got: $NP" >&2
    exit 1
fi

# OpenFOAM's bashrc consumes "$@". Drop the arguments before sourcing.
set --
if [[ -z "${WM_PROJECT_DIR:-}" ]]; then
    found=""
    for f in \
        /usr/lib/openfoam/openfoam2412/etc/bashrc \
        /usr/lib/openfoam/openfoam2406/etc/bashrc \
        /opt/openfoam2412/etc/bashrc \
        /opt/openfoam2406/etc/bashrc \
        "$HOME/OpenFOAM/OpenFOAM-v2412/etc/bashrc" \
        "$HOME/OpenFOAM/OpenFOAM-v2406/etc/bashrc"
    do
        if [[ -f "$f" ]]; then
            found="$f"
            break
        fi
    done
    if [[ -z "$found" ]]; then
        cat <<'EOF' >&2
OpenFOAM.com v2406 or v2412 was not found.

This solver is built with wmake against OpenFOAM.com (www.openfoam.com), not
the OpenFOAM Foundation packages. On Ubuntu or Debian:

  sudo apt-get update
  sudo apt-get install -y ca-certificates curl build-essential
  curl -s https://dl.openfoam.com/add-debian-repo.sh | sudo bash
  sudo apt-get update
  sudo apt-get install -y openfoam2406-dev
  # or: sudo apt-get install -y openfoam2412-dev

Then:
  source /usr/lib/openfoam/openfoam2406/etc/bashrc

The -dev package is required: the runtime-only package does not ship the
headers wmake needs. Re-run this script after sourcing, or just re-run it
and it will source the bashrc itself.
EOF
        exit 1
    fi
    # shellcheck disable=SC1090
    source "$found"
    echo "Sourced $found"
else
    echo "Using OpenFOAM already on the environment: ${WM_PROJECT_DIR}"
fi

if ! command -v wmake >/dev/null 2>&1; then
    echo "wmake is not on PATH after sourcing OpenFOAM. Install openfoam2406-dev or openfoam2412-dev." >&2
    exit 1
fi

cd "$ROOT/solver"
./Allwmake
export PATH="${FOAM_USER_APPBIN}:$PATH"
hash -r
if ! command -v laserWireDEDFoam >/dev/null 2>&1; then
    echo "laserWireDEDFoam was not installed. Check solver/Allwmake output." >&2
    exit 1
fi
echo "Solver: $(command -v laserWireDEDFoam)"

cd "$ROOT"
if [[ "$MODE" == "smoke" ]]; then
    SMOKE_NP="$NP"
    if (( SMOKE_NP > 4 )); then
        SMOKE_NP=2
    fi
    echo "Smoke case: coarse 3D, end time 8 ms, ${SMOKE_NP} rank(s). Not the production track."
    python3 generate_case.py --case cases/wire_cavity_smoke --laser-config triple \
        --wire-type solid --material 316L --dim 3d --dx 4e-4 \
        --upstream 2.5e-3 --downstream 2.5e-3 --half-width 1.6e-3 \
        --substrate-thickness 1.2e-3 --gas-height 2.4e-3 \
        --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.2e-3 --feed-start 0 \
        --scan-speed 0.006 --wire-feed-speed 0.03 \
        --end-time 0.008 --write-interval 0.004 --max-co 0.5 --np "$SMOKE_NP" \
        --laser-ramp 1e-4 \
        --contact-pinning --pin-wire --porosity --wire-cavity --wire-cavity-seed \
        --rigid-substrate 100
    CASE="$ROOT/cases/wire_cavity_smoke"
    RUN_NP="$SMOKE_NP"
else
    echo "Full case: cases/wire_cavity, ${NP} rank(s)."
    python3 generate_case.py --case cases/wire_cavity --laser-config triple \
        --wire-type solid --material 316L --resolution coarse --domain-y half \
        --upstream 5e-3 --downstream 5e-3 --half-width 3.5e-3 \
        --substrate-thickness 2e-3 --gas-height 3.5e-3 --gas-uniform-height 2.6e-3 \
        --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.15e-3 --feed-start 0.01 \
        --scan-speed 0.006 --wire-feed-speed 0.030 --track-length 4e-3 \
        --write-interval 0.02 --np "$NP" --laser-ramp 2e-3 \
        --contact-pinning --pin-wire --porosity --wire-cavity \
        --theta-receding 20 --theta-advancing 90 \
        --theta-receding-wire 25 --theta-advancing-wire 70 \
        --wire-pin-frame head \
        --rigid-substrate 100
    CASE="$ROOT/cases/wire_cavity"
    RUN_NP="$NP"
fi

if [[ "$GEN_ONLY" == 1 ]]; then
    echo "Generated $CASE. Solver was built. Not running the case."
    exit 0
fi

echo "Log (once the solve starts): tail -f $CASE/log.laserWireDEDFoam"
echo "Progress lines: grep -E 'Time =|ContactLine:|WireCavity:|Porosity:|End' $CASE/log.laserWireDEDFoam"
cd "$CASE"
./Allclean >/dev/null 2>&1 || true
./Allrun "$RUN_NP"
if [[ "$MODE" == "smoke" ]]; then
    python3 "$ROOT/scripts/quantify_pores.py" --case "$CASE" --expect-wire-smoke
else
    python3 "$ROOT/scripts/quantify_pores.py" --case "$CASE"
fi
echo "ParaView: open $CASE/case.foam as a Decomposed Case if NP>1."
echo "Colour contactState (5-8 = wire line), contactSupport, cavityMarker (1 open, 2 closed)."
