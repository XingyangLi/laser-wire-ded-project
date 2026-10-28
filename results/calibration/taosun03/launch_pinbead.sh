#!/bin/bash
# Full-domain hard pin on the cal117 bead.
# Three beams at 0/120/-120 deg, equal aim radius so the spots sit around
# the wire and the triangle is centred on the axis. Full mesh so the
# -120 deg beam is not folded onto +120 by the symmetry plane.
# Unpainted. Feed 24 mm/s. Laser on. Stop at 2 ms if the neck runs away
# or the bead collapses back into a drop on the wire.
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"

CASE="$TAO_ROOT/cases/wire_cavity_pin24"
SRC="$TAO_ROOT/cases/wire_cavity_cal117"
T0="0.7"
NP=6
PY="$TAO_PY"
# 8 ms is enough to see whether the pin drags a slit on the real bead.
# The 2 ms gate below still aborts a runaway.
TEND="0.708"

prepare() {
    if [[ -f "$CASE/constant/meltProperties" ]] \
        && grep -q "beam1_az0 " "$CASE/constant/meltProperties" \
        && grep -q "symmetryY       false" "$CASE/constant/meltProperties" \
        && grep -q "wireDragK       1e9;" "$CASE/constant/meltProperties" \
        && [[ -d "$CASE/processor0/$T0" ]]; then
        echo "CASE pin24 exists"
        return 0
    fi
    echo "GENERATE pin24 full domain, beams 0/120/-120 on the wire axis"
    rm -rf "$CASE"
    tao_source_foam
    python3 "$TAO_ROOT/generate_case.py" --case "$CASE" \
        --laser-config triple \
        --wire-type solid --material 316L --resolution coarse --domain-y full \
        --upstream 4e-3 --downstream 7e-3 --half-width 3.5e-3 \
        --substrate-thickness 2e-3 --gas-height 3.5e-3 --gas-uniform-height 2.6e-3 \
        --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.08e-3 --feed-start 0.05 \
        --scan-speed 0.003 --wire-feed-speed 0.024 \
        --beam-azimuths 0,120,-120 \
        --beam-inclinations=-32,-32,-32 \
        --beam-powers 100,400,400 \
        --beam-radii-each 0.50e-3,0.50e-3,0.50e-3 \
        --beam-aim-radii 0.9e-3,0.9e-3,0.9e-3 \
        --beam-aim-heights 0.25e-3,0.25e-3,0.25e-3 \
        --laser-ramp 2e-3 \
        --absorptivity-substrate 0.65 \
        --contact-pinning --pin-wire --porosity --wire-cavity \
        --theta-receding 10 --theta-advancing 40 \
        --theta-receding-wire 25 --theta-advancing-wire 70 \
        --contact-force-factor 6 \
        --wire-sector \
        --theta-receding-wire-trail 30 --theta-advancing-wire-trail 100 \
        --wire-sector-half-angle 90 --wire-sector-blend 30 \
        --marangoni --oxygen-sigma-only --oxygen-ppm 100 \
        --wire-pin-frame wire \
        --rigid-substrate 100 \
        --end-time "$TEND" --write-interval 0.001 --np "$NP"
    (
        cd "$CASE"
        blockMesh > log.blockMesh 2>&1
        topoSet > log.topoSet 2>&1
        createPatch -overwrite > log.createPatch 2>&1
        checkMesh > log.checkMesh 2>&1 || true
    )
    "$PY" "$DIR/map_mirror_restart.py" "$SRC" "$T0" "$CASE" "$T0"
    python3 - "$CASE" "$T0" "$TEND" <<'PY'
import re, sys
from pathlib import Path
case, t0, tend = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
mp = case / "constant/meltProperties"
t = mp.read_text()
if "symmetryY       false" not in t:
    raise SystemExit("expected a full-domain case (symmetryY false)")
old = "    wireVelocity    wire;   // head: kink fixed in the lab frame; wire: stuck to the feed"
new = old + "\n    wireBand        0.0003;\n    wireDragK       1e9;"
if old not in t:
    raise SystemExit("wireVelocity line missing")
t = t.replace(old, new, 1)
if "feedVelocity    (-0 -0 -0.024);" not in t:
    raise SystemExit("feed 24 mm/s missing")
# Three real beams, axes on the wire (aim radius 0), 120 deg apart.
for name in ("beam1_az0 ", "beam2_az120 ", "beam3_az-120 "):
    if name not in t:
        raise SystemExit(f"missing {name}")
mp.write_text(t)
cd = case / "system/controlDict"
c = cd.read_text()
c, n = re.subn(r"(?m)^startFrom\s+\w+;", "startFrom       startTime;", c, count=1)
if n != 1:
    raise SystemExit("startFrom missing")
c, n = re.subn(r"(?m)^startTime\s+[0-9.eE+-]+;", f"startTime       {t0};", c, count=1)
if n != 1:
    raise SystemExit("startTime missing")
c, n = re.subn(r"(?m)^endTime\s+[0-9.eE+-]+;", f"endTime         {tend};", c, count=1)
if n != 1:
    raise SystemExit("endTime missing")
cd.write_text(c)
print("patched wire drag, start", t0, "end", tend)
PY
    "$PY" "$DIR/column_decomp.py" "$CASE" "$NP"
    python3 - "$CASE/system/decomposeParDict" "$NP" <<'PY'
import re, sys
from pathlib import Path
p, np = Path(sys.argv[1]), sys.argv[2]
t = p.read_text()
t, n = re.subn(r"(?m)^numberOfSubdomains\s+\d+;", f"numberOfSubdomains {np};", t, count=1)
if n != 1:
    raise SystemExit("numberOfSubdomains missing")
t, n = re.subn(r"(?m)^method\s+\w+;", "method          manual;", t, count=1)
if n != 1:
    raise SystemExit("method missing")
if "manualCoeffs" not in t:
    t = t.replace(
        "method          manual;",
        "method          manual;\n\nmanualCoeffs\n{\n    dataFile    cellDist;\n}",
        1,
    )
p.write_text(t)
PY
    (
        cd "$CASE"
        rm -rf processor*
        decomposePar -force > log.decomposePar 2>&1
    )
    echo "PREPARED $(grep -m1 'cells:' "$CASE/log.checkMesh" || true)"
}

run_solver() {
    local held=0
    release() {
        if (( held > 0 )); then tao_release "$held"; held=0; fi
    }
    trap release EXIT
    tao_acquire "$NP"
    held=$NP
    tao_source_foam
    (
        cd "$CASE"
        exec nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
            laserWireDEDFoam -parallel > "$CASE/log.laserWireDEDFoam" 2>&1
    ) &
    local pid=$!
    echo "PID pin24 $pid"
    local gate=0
    local tgate
    tgate="$(python3 -c 'print(0.7 + 0.002)')"
    while kill -0 "$pid" 2>/dev/null; do
        sleep 15
        if grep -q "FOAM FATAL" "$CASE/log.laserWireDEDFoam" 2>/dev/null; then
            echo "KILL pin24 foam fatal"
            kill -TERM "$pid" 2>/dev/null || true
            break
        fi
        local latest=""
        latest="$("$PY" - "$CASE" <<'PY'
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
)"
        if [[ -z "$latest" ]]; then
            grep -E 'Laser beam|wire drag|deltaT = ' "$CASE/log.laserWireDEDFoam" | tail -2 || true
            continue
        fi
        echo "SCORE pin24 t=$latest"
        # The mapped 0.7 s field is a coarse interface. Do not treat that
        # smear as a blow-up. After the first millisecond, |U| above 15 m/s
        # is the runaway signal.
        if python3 - "$latest" <<'PY'
import sys
raise SystemExit(0 if float(sys.argv[1]) > 0.701 else 1)
PY
        then
            local rc=0
            "$PY" "$DIR/neck_state.py" "$CASE" "$latest" --calm-max 15 --smear-max 0.85 || rc=$?
            if (( rc == 3 )); then
                echo "KILL pin24 violent neck at t=$latest"
                kill -TERM "$pid" 2>/dev/null || true
                break
            fi
        fi
        # A bead that shrinks to a blob on the wire is the rejected picture.
        if ! "$PY" - "$CASE" "$latest" <<'PY'
import sys
sys.path.insert(0, "/home/asb6102/laser-wire-ded-project/results/calibration/taosun03")
import numpy as np
import neck_state as ns
case, tname = sys.argv[1], sys.argv[2]
cc, alpha, _vel = ns.load(case, tname)
x, y, z = cc[:, 0], cc[:, 1], cc[:, 2]
r = np.sqrt(x * x + y * y)
bead = (alpha > 0.5) & (z > 0.05e-3) & (z < 1.6e-3) & (r > 0.6e-3)
if not bead.any():
    raise SystemExit(1)
span = float(x[bead].max() - x[bead].min())
print(f"bead span {span*1e3:.2f} mm")
raise SystemExit(0 if span > 1.5e-3 else 1)
PY
        then
            echo "KILL pin24 bead collapsed at t=$latest"
            kill -TERM "$pid" 2>/dev/null || true
            break
        fi
        if (( gate == 0 )); then
            local gate_rc=0
            python3 - "$latest" "$tgate" <<'PY' || gate_rc=$?
import sys
raise SystemExit(0 if float(sys.argv[1]) + 1e-9 >= float(sys.argv[2]) else 1)
PY
            if (( gate_rc == 0 )); then
                gate=1
                echo "GATE pin24 2 ms passed t=$latest"
            fi
        fi
        grep "zWire" "$CASE/log.laserWireDEDFoam" | tail -1 || true
    done
    wait "$pid" || true
    release
    trap - EXIT
    echo "PIN24_DONE"
}

prepare
run_solver
