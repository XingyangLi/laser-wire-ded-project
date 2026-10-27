#!/bin/bash
# 9 um neck on a 3 mm slab, settled cal117 field, 0.06 mm groove, trail 105/135.
#
# One more halving of the smoke neck (150 um / 16). The domain is a slab
# around the wire so 16 ranks can carry it. Beams, feed, Marangoni and
# recoil stay off for 5 ms, then come on for 5 ms.
#
#   ./launch_neck9.sh prepare
#   ./launch_neck9.sh run
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"

CASE="$TAO_ROOT/cases/wire_cavity_neck9"
SRC="$TAO_ROOT/cases/wire_cavity_smokeS"
PY="$TAO_PY"
NP=16

prepare_case() {
    echo "GENERATE neck9 $(date --iso-8601=seconds)"
    tao_cal08_case "$CASE" \
        --scan-speed 0.003 --wire-feed-speed 0.024 \
        --beam-powers 100,100,700 \
        --absorptivity-substrate 0.65 \
        --preheat 300 --wire-preheat 1100 \
        --upstream 1.0e-3 --downstream 2.0e-3 --half-width 1.2e-3 \
        --substrate-thickness 0.6e-3 \
        --gas-height 2.0e-3 --gas-uniform-height 1.8e-3 \
        --end-time 0.705 --write-interval 0.001 --np "$NP" \
        --max-co 0.2 --capillary-dt-factor 1 \
        --neck-refine 4 \
        --gas-viscosity-factor 140 \
        --contact-force-factor 1 \
        --no-recoil \
        --theta-receding 10 --theta-advancing 40 \
        --theta-receding-wire 25 --theta-advancing-wire 70 \
        --wire-sector \
        --theta-receding-wire-trail 105 --theta-advancing-wire-trail 135 \
        --wire-sector-half-angle 90 --wire-sector-blend 30 \
        --oxygen-ppm 100 --oxygen-wire-angles
    python3 - "$CASE" <<'PY'
from pathlib import Path
import sys
root = Path(sys.argv[1])
mp = (root / "constant" / "meltProperties").read_text()
start = mp.find("    oxygenAngleTable\n")
end = mp.find("    );", start)
if start < 0 or end < 0:
    sys.exit("oxygenAngleTable missing")
table = (
    "    oxygenAngleTable\n"
    "    (\n"
    "        (100 10 40 25 70 105 135)\n"
    "    );"
)
mp = mp[:start] + table + mp[end + len("    );"):]
mp = mp.replace("    marangoni           true;", "    marangoni           false;", 1)
old = "    liquidOnly          true;"
new = "    liquidOnly          true;\n    densityScaled       true;"
if old not in mp:
    sys.exit("liquidOnly missing")
mp = mp.replace(old, new, 1)
if "    tFeedStart" not in mp or "    tStart" not in mp:
    sys.exit("feed or laser start missing")
# Keep both off through the first 5 ms. run_case turns them on at 0.705.
import re
mp = re.sub(r"(?m)^(\s*)tFeedStart\s+[0-9.eE+-]+;", r"\1tFeedStart      9;", mp, count=1)
mp = re.sub(r"(?m)^(\s*)tStart\s+[0-9.eE+-]+;", r"\1tStart          9;", mp, count=1)
(root / "constant" / "meltProperties").write_text(mp)
fv = (root / "system" / "fvSolution").read_text()
if "cAlpha" not in fv:
    sys.exit("cAlpha missing")
fv = fv.replace("cAlpha          1;", "cAlpha          0.5;", 1)
(root / "system" / "fvSolution").write_text(fv)
print("DICT neck9 angles 105/135, CSF scaled, beams off")
PY
    echo "MESH neck9 $(date --iso-8601=seconds)"
    tao_source_foam
    (
        cd "$CASE"
        MESH_ONLY=1 ./Allrun 1
    )
    if ! grep -q "Mesh OK" "$CASE/log.checkMesh"; then
        echo "checkMesh failed" >&2
        tail -30 "$CASE/log.checkMesh" >&2
        exit 1
    fi
    grep -E "cells:|Max aspect ratio|Mesh OK|bounding box" "$CASE/log.checkMesh" | head -30
    cat > "$CASE/system/mapFieldsDict" <<'EOF'
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
    echo "MAP neck9 from smokeS 0.7"
    mapFields -case "$CASE" -sourceTime 0.7 -mapMethod interpolate "$SRC" \
        > "$CASE/log.mapFields" 2>&1 || { tail -40 "$CASE/log.mapFields" >&2; exit 1; }
    "$PY" - "$CASE" <<'PY'
import sys
from pathlib import Path
case = Path(sys.argv[1])
src = case / "0"
orig = case / "0.orig"
templates = {
    "U": "U.orig",
    "alpha.metal": "alpha.metal.orig",
    "cWire": "cWire.orig",
    "T": "T",
    "liquidFraction": "liquidFraction",
    "meltHistory": "meltHistory",
    "p_rgh": "p_rgh",
}
for name, tmpl in templates.items():
    mapped = (src / name).read_bytes()
    i = mapped.rfind(b"boundaryField")
    body = (orig / tmpl).read_text()
    j = body.rfind("boundaryField")
    if i < 0 or j < 0:
        sys.exit(f"{name}: boundaryField missing")
    out = mapped[:i] + body[j:].encode()
    out = out.replace(b'location    "0";', b'location    "0.7";', 1)
    (src / name).write_bytes(out)
src.rename(case / "0.7")
print("MAP boundaries restored at 0.7")
PY
    "$PY" "$DIR/paint_neck_groove.py" "$CASE" 0.7 --width-mm 0.06
    # Feed stays off until the beam ramp. The generated table starts at 0.05 s.
    python3 - "$CASE/0.7/U" <<'PY'
from pathlib import Path
import re, sys
p = Path(sys.argv[1])
raw = p.read_bytes()
new = b"uniformValue table ((0 (0 0 0)) (0.705 (0 0 0)) (0.707 (0 0 -0.024)) (1e3 (0 0 -0.024)));"
raw2, n = re.subn(br"uniformValue table \([^;]*\);", new, raw, count=1)
if n != 1:
    sys.exit("wire inlet table was not replaced")
p.write_bytes(raw2)
print("FEED delayed to 0.705")
PY
    tao_source_foam
    (
        cd "$CASE"
        foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict >/dev/null
        foamDictionary -entry method -set scotch system/decomposeParDict >/dev/null
        decomposePar -force > log.decomposePar 2>&1
    )
    echo "PREPARE_OK neck9"
}

run_case() {
    local tend="$1" log="$2"
    tao_source_foam
    (
        cd "$CASE"
        foamDictionary -entry endTime -set "$tend" system/controlDict >/dev/null
    )
    tao_acquire "$NP"
    set +e
    (
        cd "$CASE"
        nice -n 10 mpirun --use-hwthread-cpus -np "$NP" \
            laserWireDEDFoam -parallel > "$log" 2>&1
    ) &
    local pid=$!
    local violent=0
    while kill -0 "$pid" 2>/dev/null; do
        sleep 30
        local latest rc=0
        latest="$("$PY" - "$CASE" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, "/home/asb6102/laser-wire-ded-project/results/calibration/taosun03")
import neck_state as ns
names = ns.time_dirs(sys.argv[1])
print(names[-1] if names else "")
PY
)"
        if [[ -n "$latest" && "$latest" != "0.7" ]]; then
            "$PY" "$DIR/neck_state.py" "$CASE" "$latest" --calm-max 20 --smear-max 0.9 || rc=$?
            if (( rc == 3 )); then
                echo "KILL neck9 violent at t=$latest"
                violent=1
                pkill -TERM -P "$pid" || true
                kill -TERM "$pid" 2>/dev/null || true
                break
            fi
        fi
        if [[ -f "$log" ]] && grep -q "FOAM FATAL" "$log"; then
            echo "KILL neck9 foam fatal"
            pkill -TERM -P "$pid" || true
            kill -TERM "$pid" 2>/dev/null || true
            violent=1
            break
        fi
    done
    wait "$pid" || true
    tao_release "$NP"
    if (( violent )); then
        return 3
    fi
    return 0
}

enable_physics() {
    python3 - "$CASE/constant/meltProperties" <<'PY'
from pathlib import Path
import re, sys
p = Path(sys.argv[1])
t = p.read_text()
t = t.replace("    marangoni           false;", "    marangoni           true;", 1)
t = t.replace("    recoil      false;", "    recoil      true;", 1)
t = re.sub(r"(?m)^(\s*)tFeedStart\s+[0-9.eE+-]+;", r"\1tFeedStart      0.705;", t, count=1)
t = re.sub(r"(?m)^(\s*)tStart\s+[0-9.eE+-]+;", r"\1tStart          0.705;", t, count=1)
p.write_text(t)
print("DICT beams, feed, Marangoni, recoil on at 0.705")
PY
}

cmd_run() {
    if [[ ! -d "$CASE/processor0" ]]; then
        prepare_case
    fi
    echo "BEAMS OFF 0.700 -> 0.705"
    run_case 0.705 "$CASE/log.beamsOff" || echo "BEAMS_OFF_STOPPED"
    "$PY" "$DIR/neck_state.py" "$CASE" --latest || true
    enable_physics
    echo "BEAMS ON 0.705 -> 0.710"
    run_case 0.710 "$CASE/log.beamsOn" || echo "BEAMS_ON_STOPPED"
    "$PY" "$DIR/neck_state.py" "$CASE" --latest || true
    echo "NECK9_DONE"
}

main() {
    local cmd="${1:-run}"
    case "$cmd" in
        prepare) prepare_case ;;
        run) cmd_run ;;
        *) echo "usage: $0 prepare|run" >&2; exit 1 ;;
    esac
}
main "$@"
