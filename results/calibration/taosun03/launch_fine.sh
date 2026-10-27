#!/bin/bash
# Finer full-domain mesh: 13 um over a wider wire-and-pool band, columns
# kept whole and packed so 16-24 ranks each own a similar cell count.
# Physics is the shell treatment (recoil off inside the oxide shell) so the
# slit is the one the slab kept. Beams, Marangoni, skin and feed stay on.
#
#   bash launch_fine.sh            # mesh, benchmark, then the 22 ms run
#   bash launch_fine.sh run 16     # skip the mesh and the benchmark
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"

CASE="$TAO_ROOT/cases/wire_cavity_skinfine"
PY="$TAO_PY"
HELD=0

hold_slots() { tao_acquire "$1"; HELD=$1; }
drop_slots() {
    if (( HELD > 0 )); then tao_release "$HELD"; HELD=0; fi
}
trap drop_slots EXIT

prepare_mesh() {
    if [[ -f "$CASE/constant/polyMesh/owner" && -d "$CASE/0" ]]; then
        echo "MESH exists"
        return 0
    fi
    echo "GENERATE skinfine $(date --iso-8601=seconds)"
    tao_source_foam
    tao_build
    rm -rf "$CASE"
    python3 "$TAO_ROOT/generate_case.py" --case "$CASE" \
        --laser-config triple \
        --wire-type solid --material 316L --dx 1.04e-4 --domain-y half \
        --upstream 4e-3 --downstream 7e-3 --half-width 3.5e-3 \
        --substrate-thickness 2e-3 --gas-height 3.5e-3 --gas-uniform-height 2.6e-3 \
        --wire-diameter 1e-3 --feed-angle 90 --wire-gap 0.08e-3 --feed-start 0 \
        --scan-speed 0.004 --wire-feed-speed 0.020 \
        --beam-azimuths 30,-30,180 \
        --beam-inclinations=-26,-26,-38 \
        --beam-powers 160,160,420 \
        --beam-radii-each 0.26e-3,0.26e-3,0.26e-3 \
        --beam-aim-radii 0.60e-3,0.60e-3,0.24e-3 \
        --beam-aim-heights 0.08e-3,0.08e-3,0.55e-3 \
        --end-time 0.022 --write-interval 0.0001 --np 1 --laser-ramp 1e-4 \
        --max-co 0.4 --capillary-dt-factor 1 \
        --neck-refine 3 \
        --neck-x0=-0.20e-3 --neck-x1 1.40e-3 --neck-y-out 0.55e-3 \
        --neck-z0 0.30e-3 --neck-z1 1.70e-3 \
        --c-alpha-neck 4 \
        --oxygen-ppm 300 --oxygen-sigma-only \
        --oxide-skin --oxide-skin-mu 20 --oxide-skin-k 1e14 \
        --oxide-skin-gap 0.20e-3 --oxide-skin-ppm-ref 300 \
        --contact-pinning --pin-wire --porosity --wire-cavity \
        --theta-receding 10 --theta-advancing 40 \
        --theta-receding-wire 25 --theta-advancing-wire 70 \
        --wire-sector \
        --theta-receding-wire-trail 140 --theta-advancing-wire-trail 140 \
        --wire-sector-half-angle 90 --wire-sector-blend 0 \
        --contact-force-factor 6 \
        --wire-pin-frame head \
        --rigid-substrate 100
    tao_source_foam
    (
        cd "$CASE"
        MESH_ONLY=1 ./Allrun 1
    )
    "$PY" "$TAO_ROOT/results/calibration/paint_slit_meniscus.py" \
        --case "$CASE" --wire-t 300 --film-mm 0.05
    python3 - "$CASE/constant/meltProperties" <<'PY'
import re, sys
from pathlib import Path
p = Path(sys.argv[1])
t = p.read_text()
if "recoilInShell" not in t:
    t = t.replace(
        "    recoilMax   2e5;",
        "    recoilMax   2e5;\n    recoilInShell false;",
        1,
    )
else:
    t = re.sub(r"(?m)^(\s*)recoilInShell\s+\w+;", r"\1recoilInShell false;", t, count=1)
p.write_text(t)
print("recoil off inside the shell")
PY
    "$PY" "$DIR/score_film.py" "$CASE" 0
    local cells
    cells="$(grep -m1 'cells:' "$CASE/log.checkMesh" | awk '{print $2}' || true)"
    echo "CELLS ${cells:-unknown}"
}

decomp() {
    local np="$1"
    tao_source_foam
    "$PY" "$DIR/column_decomp.py" "$CASE" "$np"
    python3 - "$CASE/system/decomposeParDict" "$np" <<'PY'
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
        decomposePar -force > "log.decomposePar.$np" 2>&1
        if grep -q "Number of cells = 0" "log.decomposePar.$np"; then
            echo "empty rank" >&2
            exit 1
        fi
        if grep -q "FOAM FATAL" "log.decomposePar.$np"; then
            echo "decompose failed" >&2
            exit 1
        fi
    )
}

bench() {
    local np="$1"
    decomp "$np"
    tao_source_foam
    (
        cd "$CASE"
        foamDictionary -entry endTime -set 8e-6 system/controlDict >/dev/null
    )
    hold_slots "$np"
    local t0 rc
    t0="$(date +%s)"
    set +e
    (
        cd "$CASE"
        nice -n 10 mpirun --use-hwthread-cpus -np "$np" \
            laserWireDEDFoam -parallel > "log.bench.$np" 2>&1
    )
    rc=$?
    set -e
    drop_slots
    local t1 dt
    t1="$(date +%s)"
    dt=$((t1 - t0))
    local steps
    steps="$(grep -c '^Time = ' "$CASE/log.bench.$np" || true)"
    echo "BENCH np=$np wall_s=$dt steps=$steps rc=$rc"
    rm -rf "$CASE"/processor*
    (
        cd "$CASE"
        foamDictionary -entry endTime -set 0.022 system/controlDict >/dev/null
    )
}

run_long() {
    local np="$1"
    decomp "$np"
    tao_source_foam
    (
        cd "$CASE"
        foamDictionary -entry endTime -set 0.022 system/controlDict >/dev/null
        python3 - <<'PY'
from pathlib import Path
import re
p = Path("system/controlDict")
t = p.read_text()
t2, n = re.subn(
    r"(writeControl    adjustable;\n\nwriteInterval\s+)[0-9.eE+-]+;",
    r"\g<1>0.0001;",
    t, count=1,
)
if n != 1:
    raise SystemExit("writeInterval not set")
p.write_text(t2)
PY
    )
    hold_slots "$np"
    (
        cd "$CASE"
        exec nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$np" \
            laserWireDEDFoam -parallel > "$CASE/log.laserWireDEDFoam" 2>&1
    ) &
    local pid=$!
    echo "PID fine $pid np $np"
    local scored=""
    while kill -0 "$pid" 2>/dev/null; do
        sleep 30
        if grep -q "FOAM FATAL" "$CASE/log.laserWireDEDFoam"; then
            echo "KILL fine foam fatal"
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
)" || latest=""
        if [[ -n "$latest" && "$latest" != "0" && "$latest" != "$scored" ]]; then
            echo "SCORE fine t=$latest"
            "$PY" "$DIR/score_film.py" "$CASE" "$latest" || true
            scored="$latest"
        fi
        grep -E '^Time = |OxideSkin: cells|Recoil: off|laser: incident' \
            "$CASE/log.laserWireDEDFoam" | tail -1 || true
    done
    wait "$pid" || true
    drop_slots
    echo "FINE_DONE"
}

main() {
    if [[ "${1:-}" == "run" ]]; then
        run_long "${2:-16}"
        return
    fi
    prepare_mesh
    # Short step-time samples. 8 is the reference. Use 16 or 24 when that
    # rate is at least as fast as 8, otherwise keep the fastest count.
    bench 8
    bench 16
    bench 24
    local best
    best="$("$PY" - "$CASE" <<'PY'
import sys
from pathlib import Path
case = Path(sys.argv[1])
rates = {}
for np in (8, 16, 24):
    text = (case / f"log.bench.{np}").read_text(errors="replace")
    times = [float(line.split()[2]) for line in text.splitlines() if line.startswith("ExecutionTime")]
    steps = sum(1 for line in text.splitlines() if line.startswith("Time = "))
    if len(times) < 5 or steps < 5:
        print(f"skip {np} steps={steps} times={len(times)}", file=sys.stderr)
        continue
    per = (times[-1] - times[4]) / max(steps - 5, 1)
    rates[np] = per
    print(f"{np} {per:.4f} s/step", file=sys.stderr)
if not rates:
    raise SystemExit("no bench produced a step time")
ref = rates.get(8)
wide = {np: per for np, per in rates.items() if np >= 16}
pick = min(rates, key=rates.get)
if ref is not None and wide:
    best_wide = min(wide, key=wide.get)
    if wide[best_wide] <= ref * 1.05:
        pick = best_wide
print(pick)
PY
)"
    echo "PICK np=$best"
    run_long "$best"
}

main "$@"
