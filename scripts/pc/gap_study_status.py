#!/usr/bin/env python3
"""Status of the wire-gap case study (queue + gap_study_1mm/2mm/3mm) with ETAs in CT.
Run in WSL:  python3 /mnt/c/Users/dukyo/laser_wire_ded_project/scripts/pc/gap_study_status.py
(Windows: double-click Gap_Study_Status.bat in the project folder)."""
import datetime as dt
import json
import os
import re
import subprocess
import sys
import time

HOME = os.path.expanduser("~")
ROOT = os.path.join(HOME, "laser_wire_ded_stranded")
Q = os.path.join(ROOT, "gap_study_queue")
V2 = os.path.join(ROOT, "val3mm_fe_ni_v2")
GAPS = [1, 2, 3]
REF_RATE = 11.13 * 3600 / 165822      # wall-s per sim-s per cell on 8 ranks (val3mm_fe_ni_v2 average)


def tail(fn, n=5):
    try:
        with open(fn, errors="ignore") as fh:
            return fh.read().splitlines()[-n:]
    except OSError:
        return []


def end_time(case):
    try:
        for line in open(os.path.join(case, "system", "controlDict")):
            if line.startswith("endTime"):
                return float(line.split()[1].rstrip(";"))
    except OSError:
        pass
    return 1.1249


def log_progress(case):
    """(t, wall, recent wall-s per sim-s, log age, last WireTransfer line)."""
    log = os.path.join(case, "log.laserWireDEDFoam")
    ts, cs, wt = [], [], None
    t = None
    off, last_c = 0.0, 0.0          # restarts reset ClockTime: accumulate
    try:
        with open(log, errors="ignore") as fh:
            for line in fh:
                if line.startswith("Time = "):
                    t = float(line.split()[2])
                elif line.startswith("ExecutionTime") and t is not None:
                    m = re.search(r"ClockTime = ([0-9.]+)", line)
                    c = float(m.group(1)) if m else float(line.split()[2])
                    if c < last_c:
                        off += last_c
                    last_c = c
                    ts.append(t); cs.append(c + off)
                elif line.startswith("WireTransfer:"):
                    wt = line.strip()
    except OSError:
        return None
    if len(ts) < 3:
        return dict(t=ts[-1] if ts else 0.0, wall=cs[-1] if cs else 0.0, rate=None,
                    age=time.time() - os.path.getmtime(log), wt=wt)
    t1, c1 = ts[-1], cs[-1]
    j = max(0, next((i for i in range(len(cs)) if cs[i] >= 0.9 * c1), 0) - 1)
    rate = (c1 - cs[j]) / max(t1 - ts[j], 1e-12) if t1 > ts[j] else c1 / max(t1, 1e-12)
    return dict(t=t1, wall=c1, rate=rate, age=time.time() - os.path.getmtime(log), wt=wt)


def cells(case):
    try:
        return json.load(open(os.path.join(case, "case_params.json")))["cells"]
    except Exception:
        return None


def running(pattern):
    try:
        return subprocess.run(["pgrep", "-fa", pattern], capture_output=True, text=True).stdout.strip()
    except Exception:
        return ""


def fmt(ts):
    return ts.strftime("%a %b %d %H:%M") + " CT"


def main():
    now = dt.datetime.now()
    print(f"=== Wire-substrate gap study  ({fmt(now)})")
    # queue
    pid = None
    try:
        pid = int(open(os.path.join(Q, "queue.pid")).read().strip())
        os.kill(pid, 0)
        qalive = True
    except Exception:
        qalive = False
    mode = (open(os.path.join(Q, "mode")).read().strip() if os.path.isfile(os.path.join(Q, "mode")) else "not decided yet")
    print(f"queue: {'RUNNING (pid %d)' % pid if qalive else 'not running'}   mode: {mode}")
    for l in tail(os.path.join(Q, "queue.status"), 6):
        print("   " + l)
    bt = tail(os.path.join(Q, "benchmark.txt"), 4)
    if bt:
        print("benchmark: " + " | ".join(bt))
    nsolv = len([l for l in running("laserWireDEDFoam -parallel").splitlines() if l])
    print(f"solver processes running: {nsolv}")

    # baseline
    t_start = now
    v2 = log_progress(V2)
    v2done = any("ALL DONE" in l for l in tail(os.path.join(V2, "run.status"), 3))
    if v2 is not None and not v2done:
        endv = end_time(V2)
        rem = (endv - v2["t"]) * (v2["rate"] or 0) - v2["age"]
        t_start = now + dt.timedelta(seconds=max(rem, 0) + 1800 + 900)   # + renders + benchmark
        print(f"\nval3mm_fe_ni_v2 (must finish first): t = {v2['t']:.4f}/{endv} s, ETA solver "
              f"{fmt(now + dt.timedelta(seconds=max(rem, 0)))}; gap study starts ~{fmt(t_start)} (after renders + benchmark)")
    elif v2done:
        print("\nval3mm_fe_ni_v2: ALL DONE")

    # cases
    rem_list = []
    ref = None
    infos = []
    for g in GAPS:
        c = os.path.join(ROOT, f"gap_study_{g}mm")
        p = log_progress(c)
        st = tail(os.path.join(c, "run.status"), 2)
        infos.append((g, c, p, st))
        if p and p["rate"] and p["age"] < 600 and cells(c):
            ref = p["rate"] / cells(c)
    ref = ref or REF_RATE
    if mode == "conc":
        ref *= 3 / 1.15      # 3 runs share the machine
    for g, c, p, st in infos:
        endc = end_time(c)
        done = any("ALL DONE" in l for l in st)
        print(f"\ngap_study_{g}mm  ({c}, {cells(c) or '?'} cells)")
        for l in st:
            print("   status: " + l)
        if p is None or p["t"] == 0:
            est = endc * ref * (cells(c) or 165822)
            rem_list.append(("pending", g, est))
            print(f"   not started; estimated run time {est/3600:.1f} h")
            continue
        r = p["rate"] or ref * (cells(c) or 165822)
        rem = 0 if done else max((endc - p["t"]) * r - (p["age"] if p["age"] < 600 else 0), 0)
        rem_list.append(("done" if done else "running", g, rem))
        print(f"   sim t = {p['t']:.4f} / {endc} s ({100*p['t']/endc:.1f} %), wall {p['wall']/3600:.1f} h, "
              f"rate {r/3600:.2f} h per sim-s, log updated {p['age']:.0f} s ago"
              + ("" if done else f", case ETA ~{fmt(now + dt.timedelta(seconds=rem))}"))
        if p["wt"]:
            print("   " + p["wt"])
    # whole study ETA
    if mode == "conc":
        total = max((x[2] for x in rem_list), default=0)
    else:
        total = sum(x[2] for x in rem_list)
    base = max(t_start, now)
    print(f"\nwhole study (all three + comparison) ETA ~{fmt(base + dt.timedelta(seconds=total + 1800))}"
          f"  [{'concurrent' if mode == 'conc' else 'sequential'} estimate]")
    print("results: C:\\Users\\dukyo\\laser_wire_ded\\viz\\gap_study_<n>mm  and  ...\\viz\\gap_study_compare")


if __name__ == "__main__":
    sys.exit(main())
