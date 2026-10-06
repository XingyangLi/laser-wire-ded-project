#!/bin/bash
# progress of the stranded Transitional-R run; prints sim time, speed and ETA
W=$HOME/laser_wire_ded_stranded; C=$W/${CASE:-full_transitional_r_stranded_contact}; L=$C/log.laserWireDEDFoam
date; cat $W/$(basename $C).status 2>/dev/null
pgrep -f laserWireDEDFoam >/dev/null && echo "solver processes: $(pgrep -fc "laserWireDEDFoam -parallel")" || echo "solver not running"
[ -f $L ] || exit 0
END=$(foamDictionary -entry endTime -value $C/system/controlDict 2>/dev/null || grep -m1 '^endTime' $C/system/controlDict | awk '{print $2}' | tr -d ';')
python3 - "$L" "$END" <<'PY'
import re, sys
L, end = sys.argv[1], float(sys.argv[2])
t = []; c = []
cur = None
for line in open(L, errors="replace"):
    if line.startswith("Time = "): cur = float(line.split()[2])
    elif line.startswith("ExecutionTime") and cur is not None:
        t.append(cur); c.append(float(re.search(r"ClockTime = ([0-9.]+)", line).group(1)))
if len(t) < 2: print("not enough steps yet"); sys.exit()
i0 = max(0, len(t) - 400)   # recent speed (last 400 steps)
rate = (t[-1] - t[i0]) / max(c[-1] - c[i0], 1e-9)
eta = (end - t[-1]) / max(rate, 1e-12)
print(f"sim time {t[-1]*1e3:.1f} / {end*1e3:.0f} ms, wall {c[-1]/3600:.2f} h, steps {len(t)}, "
      f"speed {rate*3600*1e3:.1f} ms of sim per hour, ETA {eta/3600:.1f} h")
PY
tail -n 1 $C/postProcessing/meltPool/meltPool.dat 2>/dev/null | awk '{printf "t=%s pool L=%.2f W=%.2f mm Tmax=%.0f K bead h=%.3f w=%.3f mm pen=%.3f mm dil=%.2f/%.2f\n",$1,$2*1e3,$3*1e3,$6,$13*1e3,$14*1e3,$19*1e3,$20,$21}'
grep -iE "FOAM FATAL|FOAM exiting|Segmentation|nan" $L | grep -v continuity | head -3
grep "Solving for p_rgh" $L | tail -1 | cut -c1-110
grep -m1 -n "Re-reading" $L
