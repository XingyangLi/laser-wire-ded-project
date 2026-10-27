#!/bin/bash
# What opens the bare neck: beam, Marangoni, or recoil.
#
# Restart ox100b at 0.702 s, when the painted groove is already metal and
# the beam ramp is just starting. Feed stays off. Three copies, 4 ranks each.
#
#   colBeam   beams on, Marangoni off, recoil off
#   colMara   beams on, Marangoni on,  recoil off
#   colRecoil beams on, Marangoni off, recoil on
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"

SRC="$TAO_ROOT/cases/wire_cavity_ox100b"
PY="$TAO_PY"
NP=4

patch_one() {
    local dest="$1" mara="$2" recoil="$3"
    python3 - "$dest" "$mara" "$recoil" <<'PY'
from pathlib import Path
import re, sys
dest, mara, recoil = sys.argv[1:]
p = Path(dest) / "constant" / "meltProperties"
t = p.read_text()
t = re.sub(r"marangoni\s+(true|false);", f"marangoni           {mara};", t, count=1)
t = re.sub(r"recoil\s+(true|false);", f"recoil      {recoil};", t, count=1)
t = re.sub(r"tFeedStart\s+[0-9.eE+-]+;", "tFeedStart      9;", t, count=1)
p.write_text(t)
c = Path(dest) / "system" / "controlDict"
ct = c.read_text()
ct = re.sub(r"endTime\s+[0-9.eE+-]+;", "endTime         0.706;", ct, count=1)
c.write_text(ct)
print(f"DICT {dest} marangoni {mara} recoil {recoil} feed off end 0.706")
PY
}

copy_one() {
    local tag="$1"
    local dest="$TAO_ROOT/cases/wire_cavity_$tag"
    rm -rf "$dest"
    mkdir -p "$dest"
    cp -a "$SRC/constant" "$SRC/system" "$dest/"
    local i
    for i in 0 1 2 3; do
        mkdir -p "$dest/processor$i"
        cp -a "$SRC/processor$i/constant" "$dest/processor$i/"
        cp -a "$SRC/processor$i/0.702" "$dest/processor$i/"
    done
}

cmd_prepare() {
    copy_one colBeam
    copy_one colMara
    copy_one colRecoil
    patch_one "$TAO_ROOT/cases/wire_cavity_colBeam" false false
    patch_one "$TAO_ROOT/cases/wire_cavity_colMara" true false
    patch_one "$TAO_ROOT/cases/wire_cavity_colRecoil" false true
    echo "PREPARE_OK column split"
}

run_one() {
    local tag="$1"
    local dest="$TAO_ROOT/cases/wire_cavity_$tag"
    tao_acquire "$NP" >&2
    # Detach stdout so a caller can read the pid without waiting for mpirun.
    (
        trap 'tao_release '"$NP" EXIT
        cd "$dest"
        nice -n 10 mpirun --use-hwthread-cpus -np "$NP" \
            laserWireDEDFoam -parallel > log.column 2>&1
    ) >/dev/null 2>&1 &
    echo "$!"
}

cmd_run() {
    if [[ ! -d "$TAO_ROOT/cases/wire_cavity_colBeam/processor0/0.702" ]]; then
        cmd_prepare
    fi
    tao_source_foam
    local tags=(colBeam colMara colRecoil)
    local pids=()
    local tag pid
    for tag in "${tags[@]}"; do
        pid="$(run_one "$tag")"
        pids+=("$pid")
        echo "START $tag pid $pid"
    done
    local i
    for i in "${!pids[@]}"; do
        wait "${pids[$i]}" || true
        echo "DONE ${tags[$i]}"
    done
    local tag
    for tag in "${tags[@]}"; do
        echo "======== $tag"
        "$PY" "$DIR/neck_state.py" "$TAO_ROOT/cases/wire_cavity_$tag" --latest || true
    done
}

main() {
    case "${1:-run}" in
        prepare) cmd_prepare ;;
        run) cmd_run ;;
        *) echo "usage: $0 prepare|run" >&2; exit 1 ;;
    esac
}
main "$@"
