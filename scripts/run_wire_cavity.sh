#!/bin/bash
# Three-laser vertical-wire case: source OpenFOAM.com, build, generate, run, summarise.
#
#   ./scripts/run_wire_cavity.sh                       # full track, one rank per core (nproc)
#   ./scripts/run_wire_cavity.sh --np 16
#   ./scripts/run_wire_cavity.sh --generate-only       # write the case and stop
#   ./scripts/run_wire_cavity.sh --smoke               # coarse 3D case, 8 ms, planted wake
#   ./scripts/run_wire_cavity.sh --oxygen-ppm 100      # Sahoo-Belton sigma and oxygen angles
#   ./scripts/run_wire_cavity.sh --smoke --oxygen-ppm 10
#   ./scripts/run_wire_cavity.sh --wire-refine 3 --wire-refine-z   # ~19 um box around the wire
#   ./scripts/run_wire_cavity.sh --wire-sector                     # wider pin on the trailing wire
#
# --oxygen-ppm writes cases/wire_cavity_ox<ppm> (or cases/wire_cavity_smoke_ox<ppm>).
# Without it the case is cases/wire_cavity and the linear sigma(T) model is unchanged.
# A sweep over 10, 100, 500 and 1000 ppm is scripts/sweep_wire_cavity_oxygen.sh.
#
# The full track is a melt-pool run (hours on a workstation). This script is what
# to launch on TaoSun-01. It does not pick a reduced mesh unless --smoke is passed.
# --wire-refine 3 --wire-refine-z is the optional 10-20 um neck mesh. It is much
# slower than the 0.15 mm track; see README. Do not start it unless you mean to.
#
# OpenFOAM.com v2406 or v2412 is required (wmake). If neither is installed, the
# script prints Ubuntu install commands and exits.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
NP="${NP:-}"
MODE="full"
GEN_ONLY=0
OXYGEN=""
WIRE_REFINE=""
REFINE_Z=0
REFINE_HALF=""
WIRE_SECTOR=0
TRAIL_R=""
TRAIL_A=""
SECTOR_HALF=""
SECTOR_BLEND=""
CASE_DIR=""
END_TIME=""
WRITE_IV="0.02"

usage() {
    cat <<'EOF'
Three-laser vertical-wire case: source OpenFOAM.com, build, generate, run, summarise.

  ./scripts/run_wire_cavity.sh                       # full track, nproc ranks
  ./scripts/run_wire_cavity.sh --np 16
  ./scripts/run_wire_cavity.sh --generate-only
  ./scripts/run_wire_cavity.sh --smoke
  ./scripts/run_wire_cavity.sh --oxygen-ppm 100
  ./scripts/run_wire_cavity.sh --wire-refine 3 --wire-refine-z
  ./scripts/run_wire_cavity.sh --case cases/my_ox --oxygen-ppm 500

--oxygen-ppm N   uniform melt oxygen [ppm by weight]; separate case directory
--wire-refine N  halve the wire box N times (x,y). 3 levels on 150 um ~ 19 um
--wire-refine-z  also halve z (isotropic neck). Needs --wire-refine
--refine-halfwidth M   half-width of that box [m] (default wire radius + 0.3 mm)
--wire-sector    wider hysteresis on the trailing (+x) side of the wire
--theta-receding-wire-trail DEG    trailing receding angle (default 60)
--theta-advancing-wire-trail DEG   trailing advancing angle (default 140)
--wire-sector-half-angle DEG       half-angle about +x (default 90)
--wire-sector-blend DEG            cosine blend width (default 30)
--case DIR       write this case instead of the default directory
--end-time S     stop at this time [s] instead of track-length/scan-speed
--write-interval S   field and side-plane write interval [s] (default 0.02)
--np N           MPI ranks (default nproc; smoke is capped at 2)
--smoke          coarse 3D, 8 ms, planted wake
--generate-only  build the solver, write the case, do not solve
EOF
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --np) NP="${2:?--np needs a core count}"; shift 2 ;;
        --oxygen-ppm) OXYGEN="${2:?--oxygen-ppm needs a number}"; shift 2 ;;
        --wire-refine) WIRE_REFINE="${2:?--wire-refine needs a level count}"; shift 2 ;;
        --wire-refine-z) REFINE_Z=1; shift ;;
        --refine-halfwidth) REFINE_HALF="${2:?--refine-halfwidth needs a length in metres}"; shift 2 ;;
        --wire-sector) WIRE_SECTOR=1; shift ;;
        --theta-receding-wire-trail) TRAIL_R="${2:?--theta-receding-wire-trail needs degrees}"; WIRE_SECTOR=1; shift 2 ;;
        --theta-advancing-wire-trail) TRAIL_A="${2:?--theta-advancing-wire-trail needs degrees}"; WIRE_SECTOR=1; shift 2 ;;
        --wire-sector-half-angle) SECTOR_HALF="${2:?--wire-sector-half-angle needs degrees}"; WIRE_SECTOR=1; shift 2 ;;
        --wire-sector-blend) SECTOR_BLEND="${2:?--wire-sector-blend needs degrees}"; WIRE_SECTOR=1; shift 2 ;;
        --case) CASE_DIR="${2:?--case needs a directory}"; shift 2 ;;
        --end-time) END_TIME="${2:?--end-time needs a time in seconds}"; shift 2 ;;
        --write-interval) WRITE_IV="${2:?--write-interval needs a time in seconds}"; shift 2 ;;
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
if [[ -n "$OXYGEN" ]] && ! [[ "$OXYGEN" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    echo "--oxygen-ppm must be a non-negative number, got: $OXYGEN" >&2
    exit 1
fi
if [[ -n "$WIRE_REFINE" ]] && ! [[ "$WIRE_REFINE" =~ ^[0-9]+$ ]]; then
    echo "--wire-refine must be a non-negative integer, got: $WIRE_REFINE" >&2
    exit 1
fi
if [[ -n "$END_TIME" ]] && ! [[ "$END_TIME" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    echo "--end-time must be a non-negative number of seconds, got: $END_TIME" >&2
    exit 1
fi
if ! [[ "$WRITE_IV" =~ ^[0-9]+([.][0-9]+)?$ ]]; then
    echo "--write-interval must be a non-negative number of seconds, got: $WRITE_IV" >&2
    exit 1
fi

EXTRA=()
if [[ -n "$OXYGEN" ]]; then
    EXTRA+=(--oxygen-ppm "$OXYGEN")
fi
if [[ -n "$WIRE_REFINE" ]]; then
    EXTRA+=(--wire-refine "$WIRE_REFINE")
fi
if [[ "$REFINE_Z" == 1 ]]; then
    EXTRA+=(--wire-refine-z)
fi
if [[ -n "$REFINE_HALF" ]]; then
    EXTRA+=(--refine-halfwidth "$REFINE_HALF")
fi
num_ok() { [[ "$1" =~ ^[0-9]+([.][0-9]+)?$ ]]; }
if [[ "$WIRE_SECTOR" == 1 ]]; then
    TRAIL_R="${TRAIL_R:-60}"
    TRAIL_A="${TRAIL_A:-140}"
    SECTOR_HALF="${SECTOR_HALF:-90}"
    SECTOR_BLEND="${SECTOR_BLEND:-30}"
    if ! num_ok "$TRAIL_R" || ! num_ok "$TRAIL_A" || ! num_ok "$SECTOR_HALF" || ! num_ok "$SECTOR_BLEND"; then
        echo "--wire-sector angles must be non-negative numbers" >&2
        exit 1
    fi
    EXTRA+=(
        --wire-sector
        --theta-receding-wire-trail "$TRAIL_R"
        --theta-advancing-wire-trail "$TRAIL_A"
        --wire-sector-half-angle "$SECTOR_HALF"
        --wire-sector-blend "$SECTOR_BLEND"
    )
fi
if [[ -n "$END_TIME" ]]; then
    EXTRA+=(--end-time "$END_TIME")
fi

OX_TAG=""
if [[ -n "$OXYGEN" ]]; then
    OX_TAG="_ox${OXYGEN//./p}"
fi
if [[ -n "$CASE_DIR" ]]; then
    if [[ "$CASE_DIR" = /* ]]; then
        CASE="$CASE_DIR"
    else
        CASE="$ROOT/$CASE_DIR"
    fi
elif [[ "$MODE" == "smoke" ]]; then
    CASE="$ROOT/cases/wire_cavity_smoke${OX_TAG}"
else
    CASE="$ROOT/cases/wire_cavity${OX_TAG}"
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
    # OpenFOAM's bashrc reads unset variables and returns non-zero from
    # optional third-party probes. Nounset and errexit must be off while
    # it is sourced.
    set +euo pipefail
    # shellcheck disable=SC1090
    source "$found"
    set -euo pipefail
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
    if [[ -n "$OXYGEN" ]]; then
        echo "Oxygen model: ${OXYGEN} ppm by weight -> ${CASE}"
    fi
    python3 generate_case.py --case "$CASE" --laser-config triple \
        --wire-type solid --material 316L --dim 3d --dx 4e-4 \
        --upstream 2.5e-3 --downstream 2.5e-3 --half-width 1.6e-3 \
        --substrate-thickness 1.2e-3 --gas-height 2.4e-3 \
        --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.2e-3 --feed-start 0 \
        --scan-speed 0.006 --wire-feed-speed 0.03 \
        --end-time 0.008 --write-interval 0.004 --max-co 0.5 --np "$SMOKE_NP" \
        --laser-ramp 1e-4 \
        --contact-pinning --pin-wire --porosity --wire-cavity --wire-cavity-seed \
        --rigid-substrate 100 \
        "${EXTRA[@]}"
    RUN_NP="$SMOKE_NP"
else
    echo "Full case: ${CASE}, ${NP} rank(s)."
    if [[ -n "$OXYGEN" ]]; then
        echo "Oxygen model: ${OXYGEN} ppm by weight."
    fi
    if [[ "$REFINE_Z" == 1 ]]; then
        echo "Wire-box refinement: ${WIRE_REFINE} level(s) in x, y and z."
    elif [[ -n "$WIRE_REFINE" && "$WIRE_REFINE" != 0 ]]; then
        echo "Wire-box refinement: ${WIRE_REFINE} level(s) in x and y (z stays at the core spacing)."
    fi
    python3 generate_case.py --case "$CASE" --laser-config triple \
        --wire-type solid --material 316L --resolution coarse --domain-y half \
        --upstream 5e-3 --downstream 5e-3 --half-width 3.5e-3 \
        --substrate-thickness 2e-3 --gas-height 3.5e-3 --gas-uniform-height 2.6e-3 \
        --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.15e-3 --feed-start 0.01 \
        --scan-speed 0.006 --wire-feed-speed 0.030 --track-length 4e-3 \
        --write-interval "$WRITE_IV" --np "$NP" --laser-ramp 2e-3 \
        --contact-pinning --pin-wire --porosity --wire-cavity \
        --theta-receding 20 --theta-advancing 90 \
        --theta-receding-wire 25 --theta-advancing-wire 70 \
        --wire-pin-frame head \
        --rigid-substrate 100 \
        "${EXTRA[@]}"
    RUN_NP="$NP"
fi

if [[ "$GEN_ONLY" == 1 ]]; then
    echo "Generated $CASE. Solver was built. Not running the case."
    exit 0
fi

echo "Log (once the solve starts): tail -f $CASE/log.laserWireDEDFoam"
echo "Progress lines: grep -E 'Time =|ContactLine:|WireCavity:|Porosity:|PinchOff:|CavityClosure:|OxygenSigma:|End' $CASE/log.laserWireDEDFoam"
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
