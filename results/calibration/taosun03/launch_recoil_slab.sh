#!/bin/bash
# Slab tests of a weaker recoil, beams on from t = 0.
#
# The full track lost the film between 4 and 8 ms with recoilMax 2e5 Pa.
# These four copies of the 19 um slab run 6 ms with the oxide skin on:
#   skinR2e5    recoil cap 2e5 Pa, recoil everywhere (the control)
#   skinR5e4    recoil cap 5e4 Pa
#   skinR1e4    recoil cap 1e4 Pa
#   skinRshell  cap 2e5 Pa, recoil forced off inside the oxide shell
#
#   bash launch_recoil_slab.sh
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"

SRC="$TAO_ROOT/cases/wire_cavity_skin56"
PY="$TAO_PY"
NP=4
HELD=0

hold_slots() {
    tao_acquire "$1"
    HELD=$1
}

drop_slots() {
    if (( HELD > 0 )); then
        tao_release "$HELD"
        HELD=0
    fi
}

trap drop_slots EXIT

copy_case() {
    local dest="$1"
    if [[ -d "$dest/processor0/constant" && -d "$dest/processor0/0" ]]; then
        echo "CASE exists $dest"
        return 0
    fi
    echo "COPY $dest"
    rm -rf "$dest"
    mkdir -p "$dest"
    rsync -a \
        --exclude 'processor*' \
        --exclude 'log.*' \
        --exclude 'postProcessing' \
        --exclude 'dynamicCode' \
        "$SRC/" "$dest/"
    find "$dest" -mindepth 1 -maxdepth 1 -type d -regextype posix-extended \
        -regex '.*/[0-9].*' ! -name '0' -exec rm -rf {} +
    local p name
    for p in "$SRC"/processor*; do
        name="$(basename "$p")"
        mkdir -p "$dest/$name"
        rsync -a "$p/constant" "$dest/$name/"
        rsync -a "$p/0" "$dest/$name/"
    done
}

patch_case() {
    local dest="$1"
    local cap="$2"
    local in_shell="$3"
    python3 - "$dest" "$cap" "$in_shell" <<'PY'
import re, sys
from pathlib import Path
dest, cap, in_shell = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
mp = dest / "constant/meltProperties"
t = mp.read_text()
t = t.replace("    marangoni           false;", "    marangoni           true;", 1)
t = t.replace("    recoil      false;", "    recoil      true;", 1)
t, n = re.subn(r"(?m)^(\s*)recoilMax\s+[0-9.eE+-]+;", rf"\1recoilMax   {cap};", t, count=1)
if n != 1:
    raise SystemExit("recoilMax missing")
if re.search(r"(?m)^\s*recoilInShell\s+", t):
    t = re.sub(r"(?m)^(\s*)recoilInShell\s+\w+;", rf"\1recoilInShell {in_shell};", t, count=1)
else:
    t = t.replace(
        f"    recoilMax   {cap};",
        f"    recoilMax   {cap};\n    recoilInShell {in_shell};",
        1,
    )
t, n = re.subn(r"(?m)^(\s*)tStart\s+[0-9.eE+-]+;", r"\1tStart          0;", t, count=1)
if n != 1:
    raise SystemExit("tStart missing")
mp.write_text(t)
cd = dest / "system/controlDict"
c = cd.read_text()
c, n = re.subn(r"(?m)^endTime\s+[0-9.eE+-]+;", "endTime         0.006;", c, count=1)
if n != 1:
    raise SystemExit("endTime missing")
c, n = re.subn(r"(?m)^writeInterval\s+[0-9.eE+-]+;", "writeInterval   0.002;", c, count=1)
if n != 1:
    raise SystemExit("writeInterval missing")
cd.write_text(c)
print(f"PATCH {dest.name} recoilMax {cap} recoilInShell {in_shell} beams on")
PY
    grep -q "tStart          0;" "$dest/constant/meltProperties"
    grep -q "recoil      true;" "$dest/constant/meltProperties"
    grep -q "recoilMax   ${cap};" "$dest/constant/meltProperties"
    grep -q "recoilInShell ${in_shell};" "$dest/constant/meltProperties"
    grep -q "marangoni           true;" "$dest/constant/meltProperties"
}

main() {
    local -a tags=(skinR2e5 skinR5e4 skinR1e4 skinRshell)
    local -a caps=(2e5 5e4 1e4 2e5)
    local -a shells=(true true true false)
    local i
    for i in 0 1 2 3; do
        local dest="$TAO_ROOT/cases/wire_cavity_${tags[$i]}"
        copy_case "$dest"
        patch_case "$dest" "${caps[$i]}" "${shells[$i]}"
        "$PY" "$DIR/score_film.py" "$dest" 0
    done
    tao_source_foam
    hold_slots $((NP * 4))
    local -a pids=()
    for i in 0 1 2 3; do
        local dest="$TAO_ROOT/cases/wire_cavity_${tags[$i]}"
        (
            cd "$dest"
            exec nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
                laserWireDEDFoam -parallel > "$dest/log.laserWireDEDFoam" 2>&1
        ) &
        pids+=("$!")
        echo "PID ${tags[$i]} ${pids[-1]}"
    done
    local alive=1
    while (( alive )); do
        sleep 20
        alive=0
        for i in 0 1 2 3; do
            if kill -0 "${pids[$i]}" 2>/dev/null; then
                alive=1
                local log="$TAO_ROOT/cases/wire_cavity_${tags[$i]}/log.laserWireDEDFoam"
                if [[ -f "$log" ]] && grep -q "FOAM FATAL" "$log"; then
                    echo "KILL ${tags[$i]} foam fatal"
                    kill -TERM "${pids[$i]}" 2>/dev/null || true
                fi
            fi
        done
    done
    for i in 0 1 2 3; do
        wait "${pids[$i]}" || true
    done
    drop_slots
    echo "SLAB_RECOIL_SCORES"
    for i in 0 1 2 3; do
        local dest="$TAO_ROOT/cases/wire_cavity_${tags[$i]}"
        echo "==== ${tags[$i]} ===="
        "$PY" "$DIR/score_film.py" "$dest" --window 0.002 0.006 || true
        grep 'Recoil: off inside' "$dest/log.laserWireDEDFoam" | head -1 || true
        grep 'laser: incident' "$dest/log.laserWireDEDFoam" | tail -1 || true
    done
    echo "SLAB_RECOIL_DONE"
}

main "$@"
