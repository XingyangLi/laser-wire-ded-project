#!/bin/bash
# Gap-study queue (PC, WSL): waits for val3mm_fe_ni_v2 (solver + its post-run renders), benchmarks
# sequential 8-rank vs 3 concurrent 5-rank runs once, then runs gap_study_1mm/2mm/3mm, renders each
# into C:\Users\dukyo\laser_wire_ded\viz\gap_study_<n>mm and writes the comparison into viz\gap_study_compare.
# Restart-safe: re-launching continues every unfinished case from its latest time (decision kept in ./mode).
# Launch hidden + keep-awake from Windows (see START_HERE.md / Gap_Study_Status.bat):
#   Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File',
#     'C:\Users\dukyo\laser_wire_ded_project\scripts\pc\launch_wsl_job.ps1','-Script',
#     '/home/dukyong/laser_wire_ded_stranded/gap_study_queue/gap_study_queue.sh'
source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1
export PATH=$HOME/lwded_bin_gap:$PATH
REPO=/mnt/c/Users/dukyo/laser_wire_ded_project
ROOT=$HOME/laser_wire_ded_stranded
Q=$ROOT/gap_study_queue
VIZ=/mnt/c/Users/dukyo/laser_wire_ded/viz
V2=$ROOT/val3mm_fe_ni_v2
GAPS="1 2 3"
QS=$Q/queue.status
mkdir -p $Q
log() { echo "$(date '+%a %b %d %H:%M:%S') $*" >> $QS; }
if [ -f $Q/queue.pid ] && kill -0 "$(cat $Q/queue.pid)" 2>/dev/null && [ "$(cat $Q/queue.pid)" != "$$" ]; then
    echo "queue already running (pid $(cat $Q/queue.pid))"; exit 0
fi
echo $$ > $Q/queue.pid
log "QUEUE START pid $$ binary $(which laserWireDEDFoam)"

# a running solver = a process whose argv has the word laserWireDEDFoam (not log.laserWireDEDFoam, tail, grep ...)
solver_running() { pgrep -f -- '(^|[/ ])laserWireDEDFoam( |$)' > /dev/null; }

# ---- 1. wait for val3mm_fe_ni_v2 (solver + renders) -------------------------------------------------------------
idle=0
while true; do
    if grep -q "ALL DONE" $V2/run.status 2>/dev/null; then log "val3mm_fe_ni_v2 ALL DONE (solver + renders)"; break; fi
    if pgrep -f 'run_v2\.sh' > /dev/null || solver_running || pgrep -f 'python.*visualize' > /dev/null; then
        idle=0
    else
        idle=$((idle + 1))
        # v2 runner gone without ALL DONE (crash / reboot): 15 idle minutes -> go on
        if [ $idle -ge 15 ]; then log "no solver/viz process for 15 min and no ALL DONE in v2 run.status: continuing"; break; fi
    fi
    [ $((SECONDS % 1800)) -lt 60 ] && log "waiting for val3mm_fe_ni_v2 ($(grep '^Time =' $V2/log.laserWireDEDFoam 2>/dev/null | tail -1))"
    sleep 60
done
# any other solver still running (e.g. a GUI job)? wait for it, max 6 h
for i in $(seq 1 360); do
    solver_running || break
    [ $i -eq 1 ] && log "another laserWireDEDFoam is running: waiting (max 6 h)"
    sleep 60
done

# ---- 2. mesh all cases (no-op if done) --------------------------------------------------------------------------
for g in $GAPS; do
    C=$ROOT/gap_study_${g}mm
    if [ ! -f $C/constant/polyMesh/owner ] || [ ! -d $C/0 ]; then
        log "meshing gap_study_${g}mm"
        ( cd $C && MESH_ONLY=1 ./Allrun 8 > log.Allrun 2>&1 ) || log "MESH FAILED gap_study_${g}mm"
    fi
done

# ---- 3. one-off benchmark: 1 x 8 ranks vs 3 x 5 ranks (same case, 5 min each) ------------------------------------
started() { ls -d $ROOT/gap_study_*mm/processor0/0.0[0-9]* $ROOT/gap_study_*mm/processor0/[1-9]* 2>/dev/null | head -1; }
if [ ! -s $Q/mode ]; then
    if [ -n "$(started)" ]; then
        echo seq > $Q/mode; log "runs already started: mode seq"
    else
        B=$Q/bench; rm -rf $B; mkdir -p $B
        SRC=$ROOT/gap_study_2mm
        mk() {  # dir np   (copy of the meshed case, decomposed for np, no writes / sampling)
            (
                mkdir -p $1 && cp -r $SRC/0 $SRC/constant $SRC/system $1/ && cd $1 && touch case.foam
                foamDictionary -entry numberOfSubdomains -set $2 system/decomposeParDict > /dev/null
                if [ $2 -ge 4 ] && [ $(($2 % 2)) -eq 0 ]; then N="($(($2/2)) 2 1)"; else N="($2 1 1)"; fi
                foamDictionary -entry coeffs.n -set "$N" system/decomposeParDict > /dev/null
                foamDictionary -entry functions -remove system/controlDict > /dev/null 2>&1
                foamDictionary -entry writeInterval -set 10 system/controlDict > /dev/null
                decomposePar -force > log.decomposePar 2>&1
            )
        }
        mk $B/s8 8; for k in 1 2 3; do mk $B/c5_$k 5; done
        TB=${BENCH_SECONDS:-300}
        log "benchmark: 1 x 8 ranks for $TB s (gap_study_2mm from t=0)"
        ( cd $B/s8 && timeout $TB mpirun -np 8 --bind-to none laserWireDEDFoam -parallel > log 2>&1 )
        log "benchmark: 3 x 5 ranks concurrently for $TB s"
        for k in 1 2 3; do ( cd $B/c5_$k && timeout $TB mpirun -np 5 --bind-to none laserWireDEDFoam -parallel > log 2>&1 ) & done
        wait
        python3 - $B > $Q/benchmark.txt <<'PY'
import sys, re, os
B = sys.argv[1]
def rate(log):
    ts, cs = [], []
    t = None
    for line in open(log, errors="ignore"):
        if line.startswith("Time = "): t = float(line.split()[2])
        m = re.search(r"ClockTime = ([0-9.eE+-]+)", line)
        if m and t is not None: ts.append(t); cs.append(float(m.group(1)))
    if len(cs) < 10: return 0.0, 0.0
    i0 = next(i for i, c in enumerate(cs) if c >= cs[-1] * 0.3)       # skip start-up
    n = len(cs) - 1 - i0
    dc = cs[-1] - cs[i0]
    return n / max(dc, 1e-9), (ts[-1] - ts[i0]) / max(dc, 1e-9)      # steps/s, sim-s per wall-s
s8, s8t = rate(os.path.join(B, "s8", "log"))
c = [rate(os.path.join(B, f"c5_{k}", "log")) for k in (1, 2, 3)]
c5 = sum(x[0] for x in c); c5t = sum(x[1] for x in c)
print(f"seq_8ranks_steps_per_s {s8:.4f} simtime_per_wall {s8t:.3e}")
print(f"conc_3x5ranks_total_steps_per_s {c5:.4f} simtime_per_wall {c5t:.3e} (each: " + ", ".join(f"{x[0]:.4f}" for x in c) + ")")
gain = c5 / s8 if s8 > 0 else 0
print(f"throughput_gain_concurrent {gain:.3f}")
print("mode", "conc" if gain > 1.10 else "seq")
PY
        MODE=$(awk '/^mode/{print $2}' $Q/benchmark.txt); MODE=${MODE:-seq}
        echo $MODE > $Q/mode
        log "benchmark: $(tr '\n' ';' < $Q/benchmark.txt) -> mode $MODE"
        rm -rf $B/s8/processor* $B/c5_*/processor*
    fi
fi
MODE=$(cat $Q/mode)

# ---- 4. runs --------------------------------------------------------------------------------------------------
# the runner is a copy installed next to this script (never edited while the queue runs)
RUN=$Q/run_gap_case.sh
if [ "$MODE" = "conc" ]; then
    log "mode conc: 3 cases x 5 ranks concurrently"
    for g in $GAPS; do
        bash $RUN $ROOT/gap_study_${g}mm 5 $VIZ/gap_study_${g}mm all >> $Q/run_${g}mm.out 2>&1 &
    done
    wait
else
    log "mode seq: one case at a time on 8 ranks (renders overlap with the next run)"
    for g in $GAPS; do
        log "gap_study_${g}mm: solver start"
        bash $RUN $ROOT/gap_study_${g}mm 8 $VIZ/gap_study_${g}mm solve >> $Q/run_${g}mm.out 2>&1
        log "gap_study_${g}mm: solver end ($(tail -1 $ROOT/gap_study_${g}mm/run.status))"
        bash $RUN $ROOT/gap_study_${g}mm 8 $VIZ/gap_study_${g}mm render >> $Q/run_${g}mm.out 2>&1 &
    done
    wait
fi
for g in $GAPS; do log "gap_study_${g}mm: $(tail -1 $ROOT/gap_study_${g}mm/run.status)"; done

# ---- 5. comparison --------------------------------------------------------------------------------------------
~/vizenv/bin/python $REPO/scripts/pc/compare_gap_study.py --root $ROOT --gaps "$GAPS" \
    --out $VIZ/gap_study_compare > $Q/compare.log 2>&1
log "compare rc=$? -> $VIZ/gap_study_compare"
log "QUEUE ALL DONE"
rm -f $Q/queue.pid
