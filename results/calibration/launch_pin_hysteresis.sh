#!/bin/bash
# True-wall wire from the cal109 mesh (cal95b bead, ~19 um crest band).
# No imposed gas shell. The contact line is pinned by hysteresis on the
# wall and the feed drags it. The gap, if any, is generated.
#
# The ppm row comes from wire_hysteresis.cfg (a model assumption).
#
#   HYST_TAG   case tag (default cal114)
#   HYST_PPM   50, 100 or 300 (default 300)
#   HYST_FEED  m/s (default 0.024)
#   HYST_END   s (default 0.014)
#   HYST_NP    ranks (default 12)
#   HYST_PARALLEL / HYST_SKIP_BUILD
set -euo pipefail
ROOT=/home/xingyang/laser-wire-ded-project
SRC=${HYST_SRC:-$ROOT/cases/wire_cavity_cal109}
TAG=${HYST_TAG:-cal114}
PPM=${HYST_PPM:-300}
FEED=${HYST_FEED:-0.024}
END=${HYST_END:-0.014}
NP=${HYST_NP:-12}
CFG=$ROOT/results/calibration/wire_hysteresis.cfg
exec > >(tee -a "$ROOT/results/calibration/pin_hyst_${TAG}.log") 2>&1
if [ "${HYST_PARALLEL:-0}" != 1 ] && ps -u xingyang -o cmd | grep -q '[l]aserWireDEDFoam'; then
    echo "a solver is already running" >&2
    exit 1
fi
set +e
set +u
set +o pipefail
# shellcheck disable=SC1091
source /usr/lib/openfoam/openfoam2406/etc/bashrc
set -e
set -u
set -o pipefail
export PATH="${FOAM_USER_APPBIN}:$PATH"
hash -r
if [ "${HYST_SKIP_BUILD:-0}" != 1 ]; then
    (cd "$ROOT/solver" && ./Allwmake)
fi

read -r THETAR THETAA KPIN < <(python3 - "$CFG" "$PPM" << 'PY'
import sys
cfg, ppm = sys.argv[1], float(sys.argv[2])
rows = []
for line in open(cfg):
    line = line.split("#", 1)[0].strip()
    if not line:
        continue
    p, tr, ta, k = line.split()
    rows.append((float(p), float(tr), float(ta), float(k)))
hit = [r for r in rows if abs(r[0] - ppm) < 1e-6]
if len(hit) != 1:
    raise SystemExit(f"ppm {ppm} is not a row of {cfg}")
print(hit[0][1], hit[0][2], hit[0][3])
PY
)

case="$ROOT/cases/wire_cavity_${TAG}"
echo "=== hysteresis ${TAG}: ${PPM} ppm, thetaR ${THETAR} thetaA ${THETAA}, K ${KPIN}, feed ${FEED}, np ${NP} ==="
echo "=== no linePin shell; gap is generated. sigma 1.75. table is a model assumption ==="
rm -rf "$case"
mkdir -p "$case"
cp -a "$SRC/constant" "$SRC/system" "$SRC/0" "$case/"
rm -rf "$case/processor"*
python3 - "$case" "$PPM" "$FEED" "$THETAR" "$THETAA" "$KPIN" << 'PY'
import re
import sys
from pathlib import Path
case, ppm, feed, theta_r, theta_a, kpin = sys.argv[1:]
ppm, feed, theta_r, theta_a, kpin = map(float, (ppm, feed, theta_r, theta_a, kpin))
root = Path(case)
props = (root / "constant/meltProperties").read_text()
# The shell must not paint a gap.
props2 = props.replace(
    "linePin\n{\n    enabled         true;",
    "linePin\n{\n    enabled         false;",
    1,
)
if props2 == props:
    raise SystemExit("could not turn linePin off")
# Drop a previous wireDrag block, then record the active row.
start = props2.find("\nwireDrag\n")
if start >= 0:
    end = props2.find("\nlinePin\n", start)
    if end < 0:
        raise SystemExit("wireDrag block is not followed by linePin")
    props2 = props2[:start] + props2[end:]
note = f"""
wireDrag
{{
    enabled         true;
    // MODEL ASSUMPTION from results/calibration/wire_hysteresis.cfg.
    // Active row: {ppm:.0f} ppm. The shell is off. The gap is not painted.
    ppm             {ppm:.0f};
    thetaReceding   {theta_r:.8g};
    thetaAdvancing  {theta_a:.8g};
    Kpin            {kpin:.8g};
    slipFar         0.001;
    slipNear        5e-5;
    gradMin         0.25;
}}
"""
props2 = props2.replace("\nlinePin\n", note + "\nlinePin\n", 1)
feed_v = f"(0 0 -{abs(feed):.8g})"
props2 = props2.replace(
    "feedVelocity   ( 0 0 -0.024 );",
    f"feedVelocity   {feed_v};",
)
if f"feedVelocity   {feed_v};" not in props2 and abs(feed - 0.024) > 1e-9:
    # cal109 may write the vector without the extra spaces the pin script used.
    import re
    props3, n = re.subn(
        r"feedVelocity\s+\([^)]*\)\s*;",
        f"feedVelocity    {feed_v};",
        props2,
        count=1,
    )
    if n != 1:
        raise SystemExit("feedVelocity was not updated")
    props2 = props3
(root / "constant/meltProperties").write_text(props2)

def patch_ascii_tail(path, needle, pattern, repl, what):
    """Edit an ascii boundary block. The internal field may be binary."""
    raw = path.read_bytes()
    i = raw.find(needle)
    if i < 0:
        raise SystemExit(f"{path.name}: no {needle!r}")
    head, tail = raw[:i], raw[i:]
    # The wireWall block is ascii and short.
    tail_txt = tail[:800].decode("ascii")
    new_txt, n = re.subn(pattern, repl, tail_txt, count=1)
    if n != 1:
        raise SystemExit(f"{path.name}: could not set {what}")
    path.write_bytes(head + new_txt.encode("ascii") + tail[len(tail_txt):])

patch_ascii_tail(
    root / "0/alpha.metal",
    b"wireWall",
    r"(thetaA\s+)[0-9.eE+-]+;",
    rf"\g<1>{theta_a:.8g};",
    "thetaA",
)
patch_ascii_tail(
    root / "0/alpha.metal",
    b"wireWall",
    r"(thetaR\s+)[0-9.eE+-]+;",
    rf"\g<1>{theta_r:.8g};",
    "thetaR",
)
patch_ascii_tail(
    root / "0/U",
    b"wireWall",
    r"refValue\s+uniform\s+\([^)]*\)\s*;",
    f"refValue        uniform (0 0 -{abs(feed):.8g});",
    "feed",
)
print(f"hysteresis {ppm:.0f} ppm  thetaR {theta_r:.8g}  thetaA {theta_a:.8g}  K {kpin:.8g}  feed {feed}")
PY
cd "$case"
foamDictionary system/controlDict -entry endTime -set "$END" > /dev/null
foamDictionary system/decomposeParDict -entry numberOfSubdomains -set "$NP" > /dev/null
if [ "$NP" -ge 4 ] && [ $((NP % 2)) -eq 0 ]; then
    N="($((NP / 2)) 2 1)"
else
    N="($NP 1 1)"
fi
foamDictionary system/decomposeParDict -entry coeffs.n -set "$N" > /dev/null
foamDictionary constant/meltProperties -entry linePin/enabled > log.linePinEnabled
decomposePar -force > log.decomposePar 2>&1
touch case.foam
nice -n 10 stdbuf -oL -eL mpirun --use-hwthread-cpus -np "$NP" laserWireDEDFoam -parallel \
    > log.laserWireDEDFoam 2>&1
echo "HYST_PIN_DONE ${TAG}"
