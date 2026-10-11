#!/bin/bash
# 10 mm Fe+Ni track with a side-to-side triangular zigzag of the laser and the wire.
# The plate runs 3.5 mm ahead of the laser and 14 mm behind it, so the whole 10 mm
# of travel stays on the substrate (the usual coax plate only reaches 6.5 mm behind).
# WIGGLE_MM is the full width of the wiggle (peak to peak), 0.5 or 1.0.
# One zigzag is 4 widths long, so both sizes have the same leg angle (~27 degrees):
#   0.5 mm wiggle -> 2 mm repeat -> 5 zigzags in 10 mm
#   1.0 mm wiggle -> 4 mm repeat -> 2.5 zigzags in 10 mm
# Does not touch track10mm_fe_ni or the 3 mm validation cases.
# Uses the working-tree generator (the weave flags are not required to be committed)
# and the solver in ~/lwded_bin_wiggle.
source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1
export PATH=$HOME/lwded_bin_wiggle:$PATH
MM=${WIGGLE_MM:?set WIGGLE_MM to 0.5 or 1.0}
# 0.5 -> 05, 1.0 -> 10
TAG=$(python3 -c "m=float('$MM'); print(f'{int(round(m*10)):02d}')")
CASE_NAME=wiggle${TAG}mm_10mm
WIDTH=$(python3 -c "print(float('$MM')/1000.0)")
WAVELEN=$(python3 -c "print(4.0*float('$MM')/1000.0)")
REPO=/mnt/c/Users/dukyo/laser_wire_ded_project
C=$HOME/laser_wire_ded_stranded/$CASE_NAME
OUT=/mnt/c/Users/dukyo/laser_wire_ded/viz/$CASE_NAME
ST=$C/run.status
mkdir -p "$OUT" "$(dirname "$C")"
if [ ! -x "$HOME/lwded_bin_wiggle/laserWireDEDFoam" ]; then
    echo "MISSING $HOME/lwded_bin_wiggle/laserWireDEDFoam — build it first (Build_Wiggle_Solver.bat)"
    exit 1
fi
if [ ! -f "$C/Allrun" ]; then
    python3 "$REPO/generate_case.py" \
        --case "$C" \
        --laser-config transitional_r \
        --power 600 \
        --scan-speed 0.002667 \
        --wire-feed-speed 0.0101 \
        --focus-height=-0.0015 \
        --rayleigh-length 0.0012 \
        --beam-radius 0.0005 \
        --spot-radius 0.0012 \
        --beam-angle 25 \
        --beam-direction - \
        --absorptivity-substrate 0.35 \
        --absorptivity-wire 0.25 \
        --alpha-hit 0.25 \
        --strand-k-factor 0.4 \
        --unmelted-k-factor 0.3 \
        --liquidus-unmixed-threshold 0.85 \
        --wire-type stranded \
        --strands 5 \
        --strand-layout ring \
        --strand-diameter 0.0003 \
        --strand-gap 8e-05 \
        --strand-materials Fe,Ni,Fe,Ni,Fe \
        --strand-feed-basis metal \
        --substrate-material Invar36 \
        --feed-angle 90 \
        --feed-side front \
        --wire-gap 0 \
        --feed-start 0 \
        --upstream 0.0035 \
        --downstream 0.014 \
        --track-length 0.010 \
        --end-time 3.75 \
        --write-interval 0.05 \
        --dx 0.00012 \
        --resolution medium \
        --domain-y full \
        --wire-refine 1 \
        --refine-downstream 0.0042 \
        --refine-halfwidth-y 0.0013 \
        --uniform-downstream 0.006 \
        --record-x 0.0036,0.0040,0.0044,0.0048 \
        --np 8 \
        --feed-scale 1.0 \
        --rigid-substrate 100 \
        --stub-floor \
        --conservative-tracers \
        --wire-transfer-stats \
        --weave-width "$WIDTH" \
        --weave-wavelength "$WAVELEN" \
        > "$OUT/gen.log" 2>&1 || { echo "GENERATE FAILED"; cat "$OUT/gen.log"; exit 1; }
fi
cd "$C" || exit 1
echo "$(date) START wiggle ${MM} mm case=$CASE_NAME binary=$(which laserWireDEDFoam)" >> "$ST"
if [ ! -d processor0 ]; then
    ./Allrun 8; rc=$?
else
    echo "$(date) restart from latest time" >> "$ST"
    mpirun -np 8 laserWireDEDFoam -parallel >> log.laserWireDEDFoam 2>&1; rc=$?
fi
echo "$(date) SOLVER_EXIT rc=$rc" >> "$ST"
END=$(foamDictionary -entry endTime -value system/controlDict 2>/dev/null)
LAST=$(ls -d processor0/[0-9]* 2>/dev/null | xargs -n1 basename | sort -g | tail -1)
if [ "$rc" != 0 ] || ! python3 -c "import sys; sys.exit(0 if float('${LAST:-0}') >= float('${END:-0}') - 1e-3 else 1)"; then
    echo "$(date) solver stopped before the end time (latest ${LAST:-none} of $END)" >> "$ST"
    exit $rc
fi
reconstructPar -newTimes > log.reconstructPar 2>&1
cp case_params.json postProcessing/meltPool/*.dat "$OUT/" 2>/dev/null
cp postProcessing/wireTransfer/wireTransfer.dat "$OUT/" 2>/dev/null
~/vizenv/bin/python "$REPO/visualize_multicomp.py" --case . --out "$OUT" > log.viz 2>&1
echo "$(date) viz multicomp rc=$?" >> "$ST"
~/vizenv/bin/python "$REPO/visualize.py" --case . --out "$OUT/standard" --only-latest >> log.viz 2>&1
echo "$(date) viz standard rc=$?" >> "$ST"
echo "$(date) ALL DONE" >> "$ST"
