#!/bin/bash
# Smoke test of the stubbing model (coarse 200/100 um, ~20k cells, serial, laser ~off: 1 W).
# Wire tip 0.3 mm above the plate, fed at 18.2 mm/s -> reaches the cold plate at ~18 ms.
#   A_0.3mm  --stubbing             : stub detected, feed + wireInlet stall (no penetration, no pile-up)
#   B_0.3mm  --wire-transfer-stats  : same detection, diagnostics only (feed keeps running)
#   C_0.3mm  no stubbing dict       : old behaviour; proves nothing breaks with the model off
# Usage: bash smoke_stubbing.sh [endTime]      results in ~/lwded_gap/smoke/<X>_0.3mm
source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1
export PATH=$HOME/lwded_bin_gap:$PATH
REPO=/mnt/c/Users/dukyo/laser_wire_ded_project
ROOT=$HOME/lwded_gap/smoke
END=${1:-0.035}
mkdir -p $ROOT
COMMON="--dx=0.0002 --upstream=0.002 --downstream=0.003 --half-width=0.0018 --substrate-thickness=0.001
 --gas-height=0.0015 --record-x=0.0015 --power=1 --end-time=$END --np=1"
gen() {  # name "wrapper flags" "extra generator flags"
    python3 $REPO/scripts/pc/gap_study_generate.py --gaps 0.3 --root $ROOT --prefix "$1_" --no-repo-copy \
        --write-interval 0.005 $2 -- $COMMON $3 > $ROOT/gen_$1.log 2>&1 || echo "gen $1 FAILED" >> $ROOT/smoke.log
}
gen A "" ""
gen B "--no-stubbing" "--wire-transfer-stats"
gen C "--no-stubbing" ""
for c in A B C; do
    d=$ROOT/${c}_0.3mm
    ( cd $d && echo "$(date) start $c" && nice -n 10 ./Allrun 1 ; echo "$(date) end $c rc=$?" ) >> $ROOT/smoke.log 2>&1 &
done
wait
echo "$(date) ALL SMOKE DONE" >> $ROOT/smoke.log
