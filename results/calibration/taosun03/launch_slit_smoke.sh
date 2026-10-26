#!/bin/bash
# Cheap neck smokes for the trailing-face gas slit.
#
# Small half-domain (a few mm around the wire), 19 um neck, start from the
# cal117 fused dome at 0.7 s mapped onto that mesh, then 50 ms. Plate window
# stays 10/40. The sweep is oxygen, feed, wire preheat, and the trailing
# pin window. Ranks are split in x only so the film and its melt neighbour
# stay on one rank (the slit metric does not see a neighbour across a
# processor face). nice 10. Cap 32 ranks, enforced by tao_acquire.
#
#   ./launch_slit_smoke.sh mesh [tag]     generate, mesh, map
#   ./launch_slit_smoke.sh probe TAG NP   ~40 steps, then restore the map
#   ./launch_slit_smoke.sh run NP         0.70 -> 0.75 s for every smoke
#
# Do not call tao_run: Allrun would remesh and wipe the mapped time.
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"

SRC="$TAO_ROOT/cases/wire_cavity_cal117"
MAP_TIME="0.7"
END_TIME="0.73"
PROBE_END="0.7002"

# tag ppm feed wire_preheat mode trailR trailA
# mode "table": --oxygen-wire-angles (trail window follows ppm).
# mode "scalar": --oxygen-sigma-only and the trail window below.
SMOKES=(
    "smokeA 100 0.024 1100 table 30 100"
    "smokeB 300 0.024 1100 table 30 100"
    "smokeC 100 0.018 1100 table 30 100"
    "smokeD 100 0.024 1100 scalar 50 120"
    "smokeE 100 0.024 1100 scalar 70 150"
    "smokeF 100 0.024 1600 table 30 100"
)

spec_for() {
    local want="$1"
    local spec
    for spec in "${SMOKES[@]}"; do
        set -- $spec
        if [[ "$1" == "$want" ]]; then
            echo "$spec"
            return 0
        fi
    done
    echo "unknown smoke $want" >&2
    exit 1
}

case_of() {
    echo "$TAO_ROOT/cases/wire_cavity_$1"
}

generate_one() {
    local tag="$1" ppm="$2" feed="$3" wpre="$4" mode="$5" tr="$6" ta="$7"
    local case
    case="$(case_of "$tag")"
    local angles=()
    if [[ "$mode" == "table" ]]; then
        angles=(--oxygen-wire-angles)
    elif [[ "$mode" == "scalar" ]]; then
        angles=(--oxygen-sigma-only)
    else
        echo "bad angle mode $mode" >&2
        exit 1
    fi
    echo "GENERATE $tag ppm=$ppm feed=$feed wirePreheat=$wpre mode=$mode trail=${tr}/${ta}"
    tao_cal08_case "$case" \
        --scan-speed 0.003 --wire-feed-speed "$feed" \
        --beam-powers 100,100,700 \
        --absorptivity-substrate 0.65 \
        --preheat 300 --wire-preheat "$wpre" \
        --upstream 2e-3 --downstream 3.5e-3 --half-width 1.6e-3 \
        --substrate-thickness 0.8e-3 \
        --gas-height 2.2e-3 --gas-uniform-height 2.2e-3 \
        --end-time "$END_TIME" --write-interval 0.005 --np 1 \
        --neck-refine 3 --capillary-dt-factor 3 \
        --theta-receding 10 --theta-advancing 40 \
        --theta-receding-wire 25 --theta-advancing-wire 70 \
        --wire-sector \
        --theta-receding-wire-trail "$tr" --theta-advancing-wire-trail "$ta" \
        --wire-sector-half-angle 90 --wire-sector-blend 30 \
        --oxygen-ppm "$ppm" \
        "${angles[@]}"
    if ! grep -q "limited corrected 0.5" "$case/system/fvSchemes"; then
        echo "$tag: neck schemes were not written" >&2
        exit 1
    fi
}

mesh_map_one() {
    local tag="$1"
    local case
    if [[ -n "${CASE_OVERRIDE:-}" ]]; then
        case="$CASE_OVERRIDE"
    else
        case="$(case_of "$tag")"
    fi
    echo "MESH $tag $(date --iso-8601=seconds)"
    tao_source_foam
    (
        cd "$case"
        MESH_ONLY=1 ./Allrun 1
    )
    if ! grep -q "Mesh OK" "$case/log.checkMesh"; then
        echo "$tag: checkMesh did not report Mesh OK" >&2
        tail -30 "$case/log.checkMesh" >&2
        exit 1
    fi
    grep -E "cells:|Max aspect ratio|Mesh OK" "$case/log.checkMesh" | head -20
    echo "MAP $tag from cal117 time $MAP_TIME"
    # Target is a box inside cal117. Only the symmetry plane coincides.
    # The other faces cut through the source cells.
    cat > "$case/system/mapFieldsDict" <<'EOF'
FoamFile
{
    version     2.0;
    format      ascii;
    class       dictionary;
    object      mapFieldsDict;
}
patchMap
(
    symmetry symmetry
);
cuttingPatches
(
    inletSubstrate
    inletGas
    outlet
    bottom
    top
    side
    wireInlet
);
EOF
    tao_source_foam
    mapFields -case "$case" -sourceTime "$MAP_TIME" \
        -mapMethod interpolate "$SRC" > "$case/log.mapFields" 2>&1 \
        || { tail -50 "$case/log.mapFields" >&2; exit 1; }
    # mapFields writes into the target's current time (0), and it replaces
    # boundary values. Keep the mapped internal field, put the case boundary
    # conditions back (wire feed table, wire-preheat inlet), and name the
    # directory 0.7 so the solver continues the fused dome.
    python3 - "$case" "$MAP_TIME" <<'PY'
import struct, sys
from pathlib import Path
case, tname = Path(sys.argv[1]), sys.argv[2]
src = case / "0"
if not src.is_dir():
    sys.exit(f"mapFields did not leave a time directory in {case}")
templates = {
    "U": "U.orig",
    "alpha.metal": "alpha.metal.orig",
    "cWire": "cWire.orig",
    "T": "T",
    "liquidFraction": "liquidFraction",
    "meltHistory": "meltHistory",
    "p_rgh": "p_rgh",
}
orig = case / "0.orig"
for name, tmpl in templates.items():
    mapped = (src / name).read_bytes()
    key = b"boundaryField"
    i = mapped.rfind(key)
    if i < 0:
        sys.exit(f"{name}: no boundaryField after map")
    body = (orig / tmpl).read_text()
    j = body.rfind("boundaryField")
    if j < 0:
        sys.exit(f"{tmpl}: no boundaryField")
    out = mapped[:i] + body[j:].encode()
    out = out.replace(b'location    "0";', f'location    "{tname}";'.encode(), 1)
    (src / name).write_bytes(out)

def scalar_minmax(path):
    data = path.read_bytes()
    key = b"internalField   nonuniform List<scalar>"
    i = data.find(key)
    if i < 0:
        sys.exit(f"{path.name}: expected a nonuniform scalar field")
    rest = data[i + len(key):].lstrip()
    n_str, _, rest = rest.partition(b"\n")
    n = int(n_str.strip())
    if rest.startswith(b"\n"):
        rest = rest[1:]
    if not rest.startswith(b"("):
        sys.exit(f"{path.name}: scalar list is not binary")
    blob = rest[1:1 + n * 8]
    if len(blob) != n * 8:
        sys.exit(f"{path.name}: short scalar list")
    lo = hi = struct.unpack_from("<d", blob)[0]
    for k in range(0, len(blob), 8 * 64):
        chunk = blob[k:k + 8 * 64]
        vals = struct.unpack("<" + "d" * (len(chunk) // 8), chunk)
        lo = min(lo, min(vals))
        hi = max(hi, max(vals))
    return lo, hi

t_lo, t_hi = scalar_minmax(src / "T")
a_lo, a_hi = scalar_minmax(src / "alpha.metal")
c_lo, c_hi = scalar_minmax(src / "cWire")
print(f"MAPPED T {t_lo:.0f}..{t_hi:.0f} K  alpha {a_lo:.3f}..{a_hi:.3f}  cWire {c_lo:.3f}..{c_hi:.3f}")
if t_hi < 1500 or a_hi < 0.9 or c_hi < 0.9:
    sys.exit("mapped dome is missing metal, wire, or a hot pool")
dest = case / tname
if dest.exists():
    import shutil
    shutil.rmtree(dest)
src.rename(dest)
PY
    local f
    for f in U p_rgh alpha.metal T liquidFraction meltHistory cWire; do
        if [[ ! -f "$case/$MAP_TIME/$f" ]]; then
            echo "$tag: mapped time is missing $f" >&2
            ls "$case/$MAP_TIME" >&2 || true
            exit 1
        fi
    done
    # The wire must still be fed. mapFields had stripped this table.
    if ! grep -q "uniformValue table" "$case/$MAP_TIME/U"; then
        echo "$tag: wire inlet feed table was not restored" >&2
        exit 1
    fi
    rm -rf "$case/${MAP_TIME}.mapbak"
    cp -a "$case/$MAP_TIME" "$case/${MAP_TIME}.mapbak"
    echo "MAP_OK $tag"
}

restore_map() {
    local case="$1"
    python3 - "$case" "$MAP_TIME" <<'PY'
import shutil, sys
from pathlib import Path
case, keep = Path(sys.argv[1]), float(sys.argv[2])
bak = case / f"{sys.argv[2]}.mapbak"
if not bak.is_dir():
    sys.exit(f"missing map backup {bak}")
live = case / sys.argv[2]
if live.exists():
    shutil.rmtree(live)
shutil.copytree(bak, live)
for d in list(case.iterdir()):
    if not d.is_dir():
        continue
    if d.name.startswith("processor"):
        shutil.rmtree(d)
        continue
    try:
        t = float(d.name)
    except ValueError:
        continue
    if abs(t - keep) < 1e-8 or abs(t) < 1e-12:
        continue
    shutil.rmtree(d)
PY
}

set_end() {
    local case="$1" tend="$2"
    tao_source_foam
    ( cd "$case" && foamDictionary -entry endTime -set "$tend" system/controlDict >/dev/null )
}

decompose_x() {
    local case="$1" np="$2"
    tao_source_foam
    (
        cd "$case"
        if (( np <= 1 )); then
            rm -rf processor*
            return 0
        fi
        foamDictionary -entry numberOfSubdomains -set "$np" system/decomposeParDict >/dev/null
        foamDictionary -entry method -set simple system/decomposeParDict >/dev/null
        foamDictionary -entry coeffs.n -set "($np 1 1)" system/decomposeParDict >/dev/null
        decomposePar -force > log.decomposePar 2>&1
    )
}

run_solver() {
    local case="$1" np="$2" log="$3"
    tao_source_foam
    (
        cd "$case"
        if (( np <= 1 )); then
            nice -n 10 laserWireDEDFoam > "$log" 2>&1
        else
            nice -n 10 mpirun --use-hwthread-cpus -np "$np" laserWireDEDFoam -parallel > "$log" 2>&1
        fi
    )
}

cmd_mesh() {
    local only="${1:-}"
    local spec tag
    for spec in "${SMOKES[@]}"; do
        set -- $spec
        tag="$1"
        if [[ -n "$only" && "$tag" != "$only" ]]; then
            continue
        fi
        generate_one "$@"
        mesh_map_one "$tag"
    done
}

stop_case_solvers() {
    local case="$1"
    local pid cwd
    for pid in $(pgrep -x laserWireDEDFoam || true); do
        cwd="$(readlink "/proc/$pid/cwd" 2>/dev/null || true)"
        if [[ "$cwd" == "$case" ]]; then
            kill -TERM "$pid" 2>/dev/null || true
        fi
    done
}

cmd_probe() {
    local tag="$1" np="$2"
    local case log rc=0
    case="$(case_of "$tag")"
    log="$DIR/${tag}_probe_np${np}.log"
    echo "PROBE $tag np=$np $(date --iso-8601=seconds)"
    tao_acquire "$np"
    trap 'tao_release '"$np" EXIT
    restore_map "$case"
    set_end "$case" "$PROBE_END"
    decompose_x "$case" "$np"
    tao_source_foam
    set +e
    (
        cd "$case"
        if (( np <= 1 )); then
            timeout --signal=TERM 180 nice -n 10 laserWireDEDFoam > "$log" 2>&1
        else
            timeout --signal=TERM 180 nice -n 10 mpirun --use-hwthread-cpus -np "$np" \
                laserWireDEDFoam -parallel > "$log" 2>&1
        fi
    )
    rc=$?
    set -e
    stop_case_solvers "$case"
    echo "PROBE_RC $rc"
    grep -E "deltaT =|Courant Number|FOAM FATAL|WireSlit:" "$log" | tail -40 || true
    restore_map "$case"
    set_end "$case" "$END_TIME"
    echo "PROBE_DONE $tag np=$np log=$log"
}

cmd_run() {
    local np="$1"
    local n=${#SMOKES[@]}
    if (( n * np > TAO_MAX_CORES )); then
        echo "refusing ${n} x ${np} ranks (cap ${TAO_MAX_CORES})" >&2
        exit 1
    fi
    local spec tag case
    for spec in "${SMOKES[@]}"; do
        set -- $spec
        tag="$1"
        case="$(case_of "$tag")"
        if [[ ! -d "$case/${MAP_TIME}.mapbak" ]]; then
            echo "$tag has no mapped backup; run mesh first" >&2
            exit 1
        fi
        restore_map "$case"
        set_end "$case" "$END_TIME"
        decompose_x "$case" "$np"
    done
    for spec in "${SMOKES[@]}"; do
        set -- $spec
        tag="$1"
        (
            exec > >(tee -a "$DIR/${tag}_driver.out") 2>&1
            set -euo pipefail
            echo "LAUNCH $tag np=$np $(date --iso-8601=seconds)"
            tao_acquire "$np"
            trap 'tao_release '"$np" EXIT
            run_solver "$(case_of "$tag")" "$np" "$(case_of "$tag")/log.laserWireDEDFoam"
            echo "${tag}_DONE $(date --iso-8601=seconds)"
        ) &
    done
    wait || true
    echo "ALL_SMOKES_DONE $(date --iso-8601=seconds)"
}

usage() {
    echo "usage: $0 mesh [tag] | probe TAG NP | run NP | prepare-full TAG | run-full" >&2
    exit 1
}

cmd_prepare_full() {
    local tag="$1"
    local spec case
    spec="$(spec_for "$tag")"
    set -- $spec
    case="$TAO_ROOT/cases/wire_cavity_slitfull"
    echo "FULL from $tag -> $case"
    printf '%s\n' "$tag" > "$DIR/slitfull_source.txt"
    local angles=()
    if [[ "$5" == "table" ]]; then
        angles=(--oxygen-wire-angles)
    else
        angles=(--oxygen-sigma-only)
    fi
    tao_cal08_case "$case" \
        --scan-speed 0.003 --wire-feed-speed "$3" \
        --beam-powers 100,100,700 \
        --absorptivity-substrate 0.65 \
        --preheat 300 --wire-preheat "$4" \
        --upstream 4e-3 --downstream 7e-3 --half-width 3.5e-3 \
        --substrate-thickness 2e-3 --gas-height 3.5e-3 --gas-uniform-height 2.6e-3 \
        --end-time 0.80 --write-interval 0.005 --np 32 \
        --neck-refine 3 --capillary-dt-factor 3 \
        --theta-receding 10 --theta-advancing 40 \
        --theta-receding-wire 25 --theta-advancing-wire 70 \
        --wire-sector \
        --theta-receding-wire-trail "$6" --theta-advancing-wire-trail "$7" \
        --wire-sector-half-angle 90 --wire-sector-blend 30 \
        --oxygen-ppm "$2" \
        "${angles[@]}"
    CASE_OVERRIDE="$case" mesh_map_one "$tag"
    echo "FULL_READY $tag"
}

cmd_run_full() {
    local np=32
    local case="$TAO_ROOT/cases/wire_cavity_slitfull"
    if [[ ! -d "$case/${MAP_TIME}.mapbak" ]]; then
        echo "slitfull has no mapped backup; prepare-full first" >&2
        exit 1
    fi
    tao_acquire "$np"
    trap 'tao_release '"$np" EXIT
    restore_map "$case"
    set_end "$case" 0.80
    decompose_x "$case" "$np"
    echo "LAUNCH slitfull np=$np $(date --iso-8601=seconds)"
    run_solver "$case" "$np" "$case/log.laserWireDEDFoam"
    echo "SLITFULL_DONE $(date --iso-8601=seconds)"
}

main() {
    local cmd="${1:-}"
    case "$cmd" in
        mesh) shift; cmd_mesh "${1:-}" ;;
        probe)
            [[ $# -eq 3 ]] || usage
            cmd_probe "$2" "$3"
            ;;
        run)
            [[ $# -eq 2 ]] || usage
            cmd_run "$2"
            ;;
        prepare-full)
            [[ $# -eq 2 ]] || usage
            cmd_prepare_full "$2"
            ;;
        run-full)
            cmd_run_full
            ;;
        *) usage ;;
    esac
}

main "$@"
