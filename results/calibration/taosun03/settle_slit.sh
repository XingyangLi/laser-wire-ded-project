#!/bin/bash
# Stabilise the neck before any full-domain run.
#
# smokeA's clip moved because mapFields -interpolate painted the 150 um dome
# onto the 19 um neck as a mush (most neck cells had alpha between 0.05 and
# 0.95). One millisecond of compression then drove the neck to about 100 m/s.
# This case maps with mapNearest, smooths alpha over 80 um, sets it back to
# 0/1, and zeros the internal velocity. Beams, feed, Marangoni and recoil stay
# off for 5 ms. If the neck stays under a few m/s, they ramp on and the film
# is judged over the next 15 ms.
#
#   ./settle_slit.sh prepare
#   ./settle_slit.sh run
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"

SRC="$TAO_ROOT/cases/wire_cavity_cal117"
BASE="$TAO_ROOT/cases/wire_cavity_smokeA"
CASE="$TAO_ROOT/cases/wire_cavity_smokeS"
MAP_TIME="0.7"
PY="$TAO_PY"
NP=4

prepare_case() {
    echo "PREPARE smokeS $(date --iso-8601=seconds)"
    rm -rf "$CASE"
    mkdir -p "$CASE/0"
    cp -a "$BASE/constant" "$BASE/system" "$BASE/0.orig" "$CASE/"
    cp -a "$CASE/0.orig/T" "$CASE/0/T"
    cp -a "$CASE/0.orig/U.orig" "$CASE/0/U"
    cp -a "$CASE/0.orig/alpha.metal.orig" "$CASE/0/alpha.metal"
    cp -a "$CASE/0.orig/cWire.orig" "$CASE/0/cWire"
    cp -a "$CASE/0.orig/liquidFraction" "$CASE/0/liquidFraction"
    cp -a "$CASE/0.orig/meltHistory" "$CASE/0/meltHistory"
    cp -a "$CASE/0.orig/p_rgh" "$CASE/0/p_rgh"
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
    tao_source_foam
    mapFields -case "$CASE" -sourceTime "$MAP_TIME" \
        -mapMethod mapNearest "$SRC" > "$CASE/log.mapFields" 2>&1 \
        || { tail -40 "$CASE/log.mapFields" >&2; exit 1; }
    "$PY" - "$CASE" <<'PY'
import sys
from pathlib import Path
import numpy as np

case = Path(sys.argv[1])
sys.path.insert(0, str(Path(__file__).resolve().parent) if False else "")
# readers live next to this launch; import by path
import importlib.util
root = Path("/home/asb6102/laser-wire-ded-project/results/calibration/taosun03")
spec = importlib.util.spec_from_file_location("neck_state", root / "neck_state.py")
ns = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ns)

def patch_internal(path, kind, values):
    data = path.read_bytes()
    key = f"internalField   nonuniform List<{kind}>".encode()
    i = data.find(key)
    if i < 0:
        sys.exit(f"{path.name}: no binary internalField")
    rest = data[i + len(key):].lstrip()
    n_str, sep, tail = rest.partition(b"\n")
    n = int(n_str.strip())
    head_end = i + len(key) + (len(data[i + len(key):]) - len(rest)) + len(n_str) + len(sep)
    if not tail.startswith(b"("):
        sys.exit(f"{path.name}: internal list is not binary")
    width = 8 if kind == "scalar" else 24
    blob_at = head_end + 1
    if kind == "scalar":
        raw = np.ascontiguousarray(values, dtype="<f8").tobytes()
    else:
        raw = np.ascontiguousarray(values, dtype="<f8").tobytes()
    if len(raw) != n * width:
        sys.exit(f"{path.name}: replacement has {len(raw)} bytes, field has {n}")
    path.write_bytes(data[:blob_at] + raw + data[blob_at + n * width:])

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
    key = b"boundaryField"
    i = mapped.rfind(key)
    if i < 0:
        sys.exit(f"{name}: no boundaryField after map")
    body = (orig / tmpl).read_text()
    j = body.rfind("boundaryField")
    if j < 0:
        sys.exit(f"{tmpl}: no boundaryField")
    out = mapped[:i] + body[j:].encode()
    out = out.replace(b'location    "0";', b'location    "0.7";', 1)
    (src / name).write_bytes(out)

cc = ns.cell_centres(case / "constant" / "polyMesh")
alpha = ns.read_internal(src / "alpha.metal", "scalar")
if alpha is None or len(alpha) != len(cc):
    sys.exit("mapped alpha is missing")
# 80 um ball: removes the 150 um stair. Applied once, to the initial field.
from scipy.spatial import cKDTree
ball = cKDTree(cc).query_ball_point(cc, 80e-6, workers=4)
sharp = np.empty(len(alpha), dtype="<f8")
for i, js in enumerate(ball):
    sharp[i] = 1.0 if alpha[js].mean() >= 0.5 else 0.0
patch_internal(src / "alpha.metal", "scalar", sharp)
vel = ns.read_internal(src / "U", "vector")
if vel is None:
    sys.exit("mapped U is missing")
patch_internal(src / "U", "vector", np.zeros_like(vel))
u = (src / "U").read_bytes()
old = b"uniformValue table ((0 (0 0 0)) (0.05 (0 0 0)) (0.052 (-0 -0 -0.024)) (1e3 (-0 -0 -0.024)));"
new = b"uniformValue table ((0 (0 0 0)) (0.706 (0 0 0)) (0.708 (-0 -0 -0.024)) (1e3 (-0 -0 -0.024)));"
if old not in u:
    sys.exit("wire inlet feed table was not the smokeA table")
(src / "U").write_bytes(u.replace(old, new, 1))
n_flip = int((sharp != np.where(alpha >= 0.5, 1.0, 0.0)).sum())
print(f"SHARP cells {len(sharp)} flipped_from_nearest_threshold {n_flip} alpha {sharp.min():.0f}..{sharp.max():.0f}")
dest = case / "0.7"
if dest.exists():
    import shutil
    shutil.rmtree(dest)
src.rename(dest)
PY
    # Beams and feed stay off until 0.706 s. Recoil and Marangoni stay off
    # for the settle; run_settle turns them back on only if the neck is calm.
    python3 - "$CASE/constant/meltProperties" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
t = p.read_text()
repls = [
    ("    marangoni           true;", "    marangoni           false;"),
    ("    capillaryDtFactor   3;", "    capillaryDtFactor   1;"),
    ("    recoil      true;", "    recoil      false;"),
    ("    tFeedStart      0.05;", "    tFeedStart      0.706;"),
    ("    tStart          0;", "    tStart          0.706;"),
    ("    forceFactor     6;", "    forceFactor     1;"),
]
for a, b in repls:
    if a not in t:
        sys.exit(f"missing dictionary line: {a}")
    t = t.replace(a, b, 1)
p.write_text(t)
print("DICT meltProperties settle")
PY
    python3 - "$CASE/system/controlDict" "$CASE/system/fvSolution" <<'PY'
from pathlib import Path
import sys
c = Path(sys.argv[1])
t = c.read_text()
t = t.replace("endTime         0.73;", "endTime         0.705;", 1)
t = t.replace("maxCo           0.4;", "maxCo           0.2;", 1)
t = t.replace("maxAlphaCo      0.4;", "maxAlphaCo      0.2;", 1)
t = t.replace("maxDeltaT       8.87644e-06;", "maxDeltaT       2.5e-06;", 1)
if "endTime         0.705;" not in t:
    sys.exit("controlDict endTime was not updated")
c.write_text(t)
f = Path(sys.argv[2])
ft = f.read_text().replace("        cAlpha          1;", "        cAlpha          2;", 1)
if "cAlpha          2;" not in ft:
    sys.exit("cAlpha was not updated")
f.write_text(ft)
print("DICT control cAlpha=2 maxCo=0.2")
PY
    "$PY" "$DIR/neck_state.py" "$CASE" 0.7
    echo "PREPARE_OK"
}

decompose_and_run() {
    local tend="$1" log="$2"
    tao_source_foam
    (
        cd "$CASE"
        foamDictionary -entry endTime -set "$tend" system/controlDict >/dev/null
        foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict >/dev/null
        foamDictionary -entry method -set simple system/decomposeParDict >/dev/null
        foamDictionary -entry coeffs.n -set "($NP 1 1)" system/decomposeParDict >/dev/null
        if [[ ! -d processor0 ]]; then
            decomposePar -force > log.decomposePar 2>&1
        fi
    )
    tao_acquire "$NP"
    set +e
    (
        cd "$CASE"
        nice -n 10 mpirun --use-hwthread-cpus -np "$NP" laserWireDEDFoam -parallel > "$log" 2>&1
    ) &
    local pid=$!
    local violent=0
    while kill -0 "$pid" 2>/dev/null; do
        sleep 20
        if [[ -f "$log" ]]; then
            # Co=0.2 and dx=19 um: dt under 5e-8 s means the neck is above ~80 m/s.
            if tail -30 "$log" | grep -E "deltaT = [0-9.e+-]*" | tail -5 | grep -qE "deltaT = [0-4]\.[0-9]*e-0[8-9]|deltaT = [0-9.e+-]*e-[1-9][0-9]"; then
                echo "KILL tiny deltaT in $log"
                violent=1
                pkill -TERM -P "$pid" || true
                kill -TERM "$pid" 2>/dev/null || true
                break
            fi
        fi
        local latest
        latest="$("$PY" - "$CASE" <<'PY'
import sys
from pathlib import Path
root = Path("/home/asb6102/laser-wire-ded-project/results/calibration/taosun03")
import importlib.util
spec = importlib.util.spec_from_file_location("neck_state", root / "neck_state.py")
ns = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ns)
names = ns.time_dirs(sys.argv[1])
print(names[-1] if names else "")
PY
)"
        if [[ -n "$latest" && "$latest" != "0.7" ]]; then
            # Exit 3 is a violent neck. A half-written field is not.
            rc=0
            "$PY" "$DIR/neck_state.py" "$CASE" "$latest" --calm-max 15 || rc=$?
            if (( rc == 3 )); then
                echo "KILL violent neck at t=$latest"
                violent=1
                pkill -TERM -P "$pid" || true
                kill -TERM "$pid" 2>/dev/null || true
                break
            fi
        fi
    done
    wait "$pid" || true
    tao_release "$NP"
    if (( violent )); then
        echo "RUN_VIOLENT $tend"
        return 3
    fi
    if grep -q "FOAM FATAL" "$log"; then
        echo "RUN_FATAL $tend"
        tail -30 "$log"
        return 4
    fi
    echo "RUN_OK $tend"
    return 0
}

enable_physics() {
    python3 - "$CASE/constant/meltProperties" <<'PY'
from pathlib import Path
import sys
p = Path(sys.argv[1])
t = p.read_text()
t = t.replace("    marangoni           false;", "    marangoni           true;", 1)
t = t.replace("    recoil      false;", "    recoil      true;", 1)
p.write_text(t)
print("DICT physics on (beams and feed ramp at 0.706)")
PY
}

cmd_run() {
    prepare_case
    echo "SETTLE 0.700 -> 0.705 beams/feed/recoil/Marangoni off"
    if ! decompose_and_run 0.705 "$CASE/log.settle"; then
        echo "SETTLE_FAILED"
        exit 1
    fi
    "$PY" "$DIR/neck_state.py" "$CASE" --latest --calm-max 8 || {
        echo "SETTLE_NOT_CALM"
        exit 1
    }
    enable_physics
    # Drop the decomposed copy of the dictionary so the restart reads recoil on.
    rm -rf "$CASE"/processor*/constant/meltProperties
    # decomposePar stores fields only; the dict is read from the case constant/.
    echo "PHYSICS 0.705 -> 0.720"
    if ! decompose_and_run 0.720 "$CASE/log.physics"; then
        echo "PHYSICS_FAILED"
        exit 1
    fi
    "$PY" "$DIR/neck_state.py" "$CASE" --latest
    echo "SETTLE_DONE"
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
