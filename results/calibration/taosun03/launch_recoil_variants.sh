#!/bin/bash
# Full-domain, full beams and Marangoni, 20 ms, two recoil treatments that
# kept the slit on the slab. Same 19 um mesh and 4 ranks as skinfull.
#   skinShell   recoil off inside the oxide shell, cap still 2e5 Pa
#   skinCap5e4  recoil cap 5e4 Pa everywhere
#
# Volume every 0.1 ms (201 frames, 10 s at 20 fps).
set -euo pipefail
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"

SRC="$TAO_ROOT/cases/wire_cavity_skinfull"
PY="$TAO_PY"
NP=4
HELD=0

hold_slots() { tao_acquire "$1"; HELD=$1; }
drop_slots() {
    if (( HELD > 0 )); then tao_release "$HELD"; HELD=0; fi
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
    local dest="$1" cap="$2" in_shell="$3"
    python3 - "$dest" "$cap" "$in_shell" <<'PY'
import re, sys
from pathlib import Path
dest, cap, in_shell = Path(sys.argv[1]), sys.argv[2], sys.argv[3]
mp = dest / "constant/meltProperties"
t = mp.read_text()
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
mp.write_text(t)
cd = (dest / "system/controlDict").read_text()
cd2, n = re.subn(r"(?m)^endTime\s+[0-9.eE+-]+;", "endTime         0.022;", cd, count=1)
if n != 1:
    raise SystemExit("endTime missing")
cd2, n = re.subn(
    r"(writeControl    adjustable;\n\nwriteInterval\s+)[0-9.eE+-]+;",
    r"\g<1>0.0001;",
    cd2, count=1,
)
if n != 1:
    raise SystemExit("writeInterval missing")
(dest / "system/controlDict").write_text(cd2)
print(f"PATCH {dest.name} cap {cap} inShell {in_shell}")
PY
}

latest_time() {
    "$PY" - "$1" <<'PY'
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
}

main() {
    local shell="$TAO_ROOT/cases/wire_cavity_skinShell"
    local cap="$TAO_ROOT/cases/wire_cavity_skinCap5e4"
    copy_case "$shell"
    copy_case "$cap"
    patch_case "$shell" "2e5" false
    patch_case "$cap" "5e4" true
    grep -q "recoilInShell false;" "$shell/constant/meltProperties"
    grep -q "recoilMax   5e4;" "$cap/constant/meltProperties"
    grep -q "tStart          0;" "$shell/constant/meltProperties"
    "$PY" "$DIR/score_film.py" "$shell" 0
    "$PY" "$DIR/score_film.py" "$cap" 0
    tao_source_foam
    hold_slots 8
    (
        cd "$shell"
        exec nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
            laserWireDEDFoam -parallel > "$shell/log.laserWireDEDFoam" 2>&1
    ) &
    local ps=$!
    (
        cd "$cap"
        exec nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" \
            laserWireDEDFoam -parallel > "$cap/log.laserWireDEDFoam" 2>&1
    ) &
    local pc=$!
    echo "PIDS shell $ps cap $pc"
    local ss="" sc=""
    while kill -0 "$ps" 2>/dev/null || kill -0 "$pc" 2>/dev/null; do
        sleep 30
        for pair in "shell|$ps|$shell" "cap|$pc|$cap"; do
            IFS='|' read -r name pid case <<<"$pair"
            kill -0 "$pid" 2>/dev/null || continue
            local log="$case/log.laserWireDEDFoam"
            if [[ -f "$log" ]] && grep -q "FOAM FATAL" "$log"; then
                echo "KILL $name"
                kill -TERM "$pid" 2>/dev/null || true
                continue
            fi
            local latest=""
            latest="$(latest_time "$case")" || latest=""
            local prev=""
            if [[ "$name" == shell ]]; then prev="$ss"; else prev="$sc"; fi
            if [[ -n "$latest" && "$latest" != "0" && "$latest" != "$prev" ]]; then
                echo "SCORE $name t=$latest"
                "$PY" "$DIR/score_film.py" "$case" "$latest" || true
                if [[ "$name" == shell ]]; then ss="$latest"; else sc="$latest"; fi
            fi
            grep -E '^Time = |OxideSkin: cells|Recoil: off|laser: incident' "$log" | tail -1 || true
        done
    done
    wait "$ps" || true
    wait "$pc" || true
    drop_slots
    echo "RECOIL_VARIANTS_DONE"
}

main "$@"
