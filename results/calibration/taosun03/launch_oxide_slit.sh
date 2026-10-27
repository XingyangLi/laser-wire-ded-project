#!/bin/bash
# Non-wetting trailing-face test on the settled cal117 neck (smokeS).
#
# A wetting window fills a painted groove. These copies keep that mesh,
# the density-scaled CSF and the raised gas viscosity, and replace only
# the trailing-wire angles and the painted gap.
#
#   oxwet   100 ppm  trail 30/90   groove 0.06 mm  beams off   (should fill)
#   ox100a  100 ppm  trail 105/135 groove 0.06 mm  beams off
#   ox100b  100 ppm  trail 105/135 groove 0.06 mm  beams on after 2 ms
#   ox100w  100 ppm  trail 105/135 groove 0.15 mm  beams on after 2 ms
#   ox50     50 ppm  trail 90/120  groove 0.06 mm  beams on after 2 ms
#   ox300   300 ppm  trail 120/150 groove 0.06 mm  beams on after 2 ms
#
#   ./launch_oxide_slit.sh prepare
#   ./launch_oxide_slit.sh run
#   ./launch_oxide_slit.sh score
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"

BASE="$TAO_ROOT/cases/wire_cavity_smokeS"
PY="$TAO_PY"
NP=4

# tag ppm width_mm physics endTime
CASES=(
    "oxwet  100 0.06 off 0.710"
    "ox100a 100 0.06 off 0.710"
    "ox100b 100 0.06 on  0.714"
    "ox100w 100 0.15 on  0.714"
    "ox50    50 0.06 on  0.714"
    "ox300  300 0.06 on  0.714"
)

case_dir() {
    echo "$TAO_ROOT/cases/wire_cavity_$1"
}

patch_case() {
    local dest="$1" ppm="$2" physics="$3" tend="$4"
    "$PY" - "$dest" "$ppm" "$physics" "$tend" <<'PY'
import sys
from pathlib import Path

dest, ppm, physics, tend = sys.argv[1:]
ppm = int(ppm)
root = Path(dest)
mp = (root / "constant" / "meltProperties").read_text()
start = mp.find("    oxygenAngleTable\n")
end = mp.find("    );", start)
if start < 0 or end < 0:
    sys.exit("oxygenAngleTable missing")
if ppm == 100 and physics == "off" and "oxwet" in dest:
    rows = "        (100 10 40 25 70 30 90)\n"
else:
    rows = (
        "        (50 10 40 25 70 90 120)\n"
        "        (100 10 40 25 70 105 135)\n"
        "        (300 10 40 25 70 120 150)\n"
    )
table = "    oxygenAngleTable\n    (\n" + rows + "    );"
mp = mp[:start] + table + mp[end + len("    );"):]
mp = mp.replace(f"    chamberOxygenPpm {100};", f"    chamberOxygenPpm {ppm};", 1)
if physics == "on":
    mp = mp.replace("    marangoni           false;", "    marangoni           true;", 1)
    mp = mp.replace("    marangoni           true;", "    marangoni           true;", 1)
    mp = mp.replace("    recoil      false;", "    recoil      true;", 1)
    mp = mp.replace("    tFeedStart      0.706;", "    tFeedStart      0.702;", 1)
    mp = mp.replace("    tStart          0.706;", "    tStart          0.702;", 1)
else:
    mp = mp.replace("    marangoni           true;", "    marangoni           false;", 1)
    mp = mp.replace("    recoil      true;", "    recoil      false;", 1)
    mp = mp.replace("    recoil      false;", "    recoil      false;", 1)
    mp = mp.replace("    tFeedStart      0.706;", "    tFeedStart      9;", 1)
    mp = mp.replace("    tStart          0.706;", "    tStart          9;", 1)
if "chamberOxygenPpm " + str(ppm) not in mp:
    sys.exit("ppm was not written")
(root / "constant" / "meltProperties").write_text(mp)

fv = (root / "system" / "fvSolution").read_text()
if "cAlpha          1;" not in fv and "cAlpha          0.5;" not in fv:
    sys.exit("cAlpha missing")
fv = fv.replace("        cAlpha          1;", "        cAlpha          0.5;", 1)
(root / "system" / "fvSolution").write_text(fv)

cd = (root / "system" / "controlDict").read_text()
cd = cd.replace("endTime         0.712;", f"endTime         {tend};", 1)
if f"endTime         {tend};" not in cd:
    sys.exit("endTime was not written")
(root / "system" / "controlDict").write_text(cd)

u = root / "0.7" / "U"
raw = u.read_bytes()
old = b"((0 (0 0 0)) (0.706 (0 0 0)) (0.708 (-0 -0 -0.024)) (1e3 (-0 -0 -0.024)))"
if physics == "on":
    new = b"((0 (0 0 0)) (0.702 (0 0 0)) (0.704 (-0 -0 -0.024)) (1e3 (-0 -0 -0.024)))"
else:
    new = b"((0 (0 0 0)) (9 (0 0 0)) (9.002 (-0 -0 -0.024)) (1e3 (-0 -0 -0.024)))"
if old not in raw:
    sys.exit("wire inlet feed table was not the smokeS table")
u.write_bytes(raw.replace(old, new, 1))
print(f"DICT {dest} ppm={ppm} physics={physics} end={tend}")
PY
}

prepare_one() {
    local tag="$1" ppm="$2" width="$3" physics="$4" tend="$5"
    local dest
    dest="$(case_dir "$tag")"
    echo "PREPARE $tag $(date --iso-8601=seconds)"
    rm -rf "$dest"
    mkdir -p "$dest"
    cp -a "$BASE/constant" "$BASE/system" "$BASE/0.orig" "$dest/"
    cp -a "$BASE/0.7" "$dest/0.7"
    "$PY" "$DIR/paint_neck_groove.py" "$dest" 0.7 --width-mm "$width"
    patch_case "$dest" "$ppm" "$physics" "$tend"
    # The wet control is detected by the directory name inside patch_case.
    tao_source_foam
    (
        cd "$dest"
        foamDictionary -entry numberOfSubdomains -set "$NP" system/decomposeParDict >/dev/null
        foamDictionary -entry method -set simple system/decomposeParDict >/dev/null
        foamDictionary -entry coeffs.n -set "($NP 1 1)" system/decomposeParDict >/dev/null
        decomposePar -force > log.decomposePar 2>&1
    )
    echo "PREPARE_OK $tag"
}

cmd_prepare() {
    local spec tag ppm width physics tend
    for spec in "${CASES[@]}"; do
        # shellcheck disable=SC2086
        set -- $spec
        tag="$1"; ppm="$2"; width="$3"; physics="$4"; tend="$5"
        prepare_one "$tag" "$ppm" "$width" "$physics" "$tend"
    done
}

cmd_run() {
    local spec tag dest pid
    local -a tags=() pids=()
    for spec in "${CASES[@]}"; do
        # shellcheck disable=SC2086
        set -- $spec
        tag="$1"
        dest="$(case_dir "$tag")"
        if [[ ! -d "$dest/processor0" ]]; then
            echo "$tag is not prepared" >&2
            exit 1
        fi
        tags+=("$tag")
    done
    tao_source_foam
    for tag in "${tags[@]}"; do
        dest="$(case_dir "$tag")"
        tao_acquire "$NP"
        (
            trap 'tao_release '"$NP" EXIT
            cd "$dest"
            nice -n 10 mpirun --use-hwthread-cpus -np "$NP" \
                laserWireDEDFoam -parallel > log.oxide 2>&1
        ) &
        pids+=("$!")
        echo "START $tag pid ${pids[-1]}"
    done

    local alive=1 violent
    while (( alive )); do
        sleep 30
        alive=0
        local i
        for i in "${!pids[@]}"; do
            if kill -0 "${pids[$i]}" 2>/dev/null; then
                alive=1
                tag="${tags[$i]}"
                dest="$(case_dir "$tag")"
                local latest rc=0
                latest="$("$PY" - "$dest" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, "/home/asb6102/laser-wire-ded-project/results/calibration/taosun03")
import neck_state as ns
names = ns.time_dirs(sys.argv[1])
print(names[-1] if names else "")
PY
)"
                if [[ -n "$latest" && "$latest" != "0.7" ]]; then
                    "$PY" "$DIR/neck_state.py" "$dest" "$latest" --calm-max 15 || rc=$?
                    if (( rc == 3 )); then
                        echo "KILL $tag violent at t=$latest"
                        pkill -TERM -P "${pids[$i]}" || true
                        kill -TERM "${pids[$i]}" 2>/dev/null || true
                    fi
                fi
                if [[ -f "$dest/log.oxide" ]] && grep -q "FOAM FATAL" "$dest/log.oxide"; then
                    echo "KILL $tag foam fatal"
                    pkill -TERM -P "${pids[$i]}" || true
                    kill -TERM "${pids[$i]}" 2>/dev/null || true
                fi
            fi
        done
    done
    local i
    for i in "${!pids[@]}"; do
        wait "${pids[$i]}" || true
        echo "DONE ${tags[$i]}"
    done
    cmd_score
}

cmd_score() {
    "$PY" - "$TAO_ROOT" <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, "/home/asb6102/laser-wire-ded-project/results/calibration/taosun03")
import neck_state as ns

root = Path(sys.argv[1])
tags = ["oxwet", "ox100a", "ox100b", "ox100w", "ox50", "ox300"]

def depth_of(rows, lo, hi):
    chosen = [(z, w) for z, _x, w, ok in rows if ok and w is not None and lo <= w <= hi]
    depth = 0.0
    prev = None
    run0 = None
    for z, _w in chosen:
        if prev is not None and z - prev <= 0.05e-3:
            depth = max(depth, z - run0)
        else:
            run0 = z
        prev = z
    return depth, len(chosen)

print("tag        t        |U|max  smear  thin_mm  wide_mm  n_thin  width_mm")
best = {}
for tag in tags:
    case = root / "cases" / f"wire_cavity_{tag}"
    names = [n for n in ns.time_dirs(case) if n != "0.7"]
    samples = []
    if not names:
        print(f"{tag:8s}  no frames")
        best[tag] = False
        continue
    for name in names:
        try:
            s = ns.summarise(case, name)
        except Exception as exc:
            print(f"{tag:8s}  {name}  read error: {exc}")
            continue
        rows = s["rows"]
        thin_d, n_thin = depth_of(rows, 0.03e-3, 0.08e-3)
        wide_d, _n = depth_of(rows, 0.03e-3, 0.20e-3)
        wmed = s["width_mm"]
        print(
            f"{tag:8s}  {float(name):8.4f}  {s['umax']:6.2f}  {s['smear']:.3f}"
            f"  {thin_d*1e3:6.3f}  {wide_d*1e3:6.3f}  {n_thin:5d}  {wmed}"
        )
        samples.append((float(name), thin_d, s["umax"]))
    # Pass: every frame in some span of at least 4 ms has thin depth
    # >= 0.25 mm, and that depth moves by at most 0.08 mm.
    hold = False
    for i in range(len(samples)):
        for j in range(i + 1, len(samples)):
            chunk = samples[i:j + 1]
            span = chunk[-1][0] - chunk[0][0]
            if span > 0.006:
                break
            if span + 1e-9 < 0.004:
                continue
            depths = [d for _t, d, _u in chunk]
            if min(depths) >= 0.25e-3 and max(depths) - min(depths) <= 0.08e-3:
                hold = True
    best[tag] = hold
    print(f"  stability: {'HOLDS' if hold else 'no steady film'}")
print("PASS " + " ".join(t for t, ok in best.items() if ok) if any(best.values()) else "PASS none")
PY
}

main() {
    local cmd="${1:-run}"
    case "$cmd" in
        prepare) cmd_prepare ;;
        run) cmd_run ;;
        score) cmd_score ;;
        *) echo "usage: $0 prepare|run|score" >&2; exit 1 ;;
    esac
}
main "$@"
