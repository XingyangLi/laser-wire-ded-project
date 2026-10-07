#!/bin/bash
# Smoke test of the wire-buckling response of the stubbing model (coarse 200/100 um, serial, laser ~off: 1 W).
# Wire tip 0.3 mm above the cold plate, fed at 18.2 mm/s -> stub contact at ~18 ms; the gas layer is 3.5 mm
# (as the gap cases) so the free solid column stub -> wireInlet is ~3.4 mm long.
#   on_0.3mm   --stubbing --wire-buckling : stall, then (stalled feed > Euler S_cr ~0.33 mm, t ~ 36 ms) the
#                                           column bows sideways (+y, normal to the scan), amplitude grows
#   off_0.3mm  --stubbing                 : stall only (same diagnostics, bow stays ~0)
# Usage: bash smoke_buckling.sh [endTime]     results in ~/lwded_gap/smoke_buckle/<on|off>_0.3mm
#        summary table (stall, compression, commanded + measured bow vs time): summary.txt
source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1
export PATH=$HOME/lwded_bin_gap_buckle:$PATH
REPO=/mnt/c/Users/dukyo/laser_wire_ded_project
ROOT=$HOME/lwded_gap/smoke_buckle
END=${1:-0.07}
mkdir -p $ROOT
COMMON="--dx=0.0002 --upstream=0.002 --downstream=0.003 --half-width=0.0025 --substrate-thickness=0.001
 --gas-height=0.0035 --record-x=0.0015 --power=1 --end-time=$END --np=1"
gen() {  # name "wrapper flags"
    python3 $REPO/scripts/pc/gap_study_generate.py --gaps 0.3 --root $ROOT --prefix "$1_" --no-repo-copy \
        --write-interval 0.005 $2 -- $COMMON > $ROOT/gen_$1.log 2>&1 || echo "gen $1 FAILED" >> $ROOT/smoke.log
}
gen on ""
gen off "--no-buckling"
echo "$(date) binary $(which laserWireDEDFoam)" >> $ROOT/smoke.log
for c in on off; do
    d=$ROOT/${c}_0.3mm
    ( cd $d && echo "$(date) start $c" && nice -n 10 ./Allrun 1 ; echo "$(date) end $c rc=$?" ) >> $ROOT/smoke.log 2>&1 &
done
wait
python3 - $ROOT > $ROOT/summary.txt <<'PY'
import sys, os
root = sys.argv[1]
def load(fn):
    hdr, rows = None, []
    for line in open(fn):
        if line.startswith("#"):
            hdr = [h.split("[")[0] for h in line[1:].split()]; continue
        p = line.split()
        if hdr and len(p) == len(hdr): rows.append(dict(zip(hdr, map(float, p))))
    return rows
for c in ("on", "off"):
    fn = os.path.join(root, f"{c}_0.3mm", "postProcessing", "wireTransfer", "wireTransfer.dat")
    if not os.path.isfile(fn): print(c, "no wireTransfer.dat"); continue
    R = load(fn)
    print(f"== {c}: {len(R)} rows")
    print("  t[ms] stub stall S[mm] Scr[mm] L[mm] buckled A_cmd[mm] bow_meas[mm] at_xi tipOff_b/t[mm] tipZ[mm]")
    last = -1
    for r in R:
        if r["time"]*1e3 >= last + 2.5 or r is R[-1]:
            last = r["time"]*1e3
            print(f"  {r['time']*1e3:6.1f} {int(r['stubbed'])} {r['stallFactor']:.2f} {r['bkStall']*1e3:6.3f} "
                  f"{r['bkCritical']*1e3:6.3f} {r['bkLength']*1e3:5.2f} {int(r['buckled'])} {r['bkAmp']*1e3:6.3f} "
                  f"{r['bkBow']*1e3:7.3f} {r['bkBowXi']:5.2f} {r['bkTipOffB']*1e3:6.3f}/{r['bkTipOffT']*1e3:6.3f} "
                  f"{r['tipZ']*1e3:6.3f}")
PY
echo "$(date) ALL SMOKE DONE" >> $ROOT/smoke.log
