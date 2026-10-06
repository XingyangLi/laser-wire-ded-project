#!/usr/bin/env python3
"""
run_case.py - mesh, run and post-process a laser wire DED case (Linux / WSL).

    python run_case.py --case case_lwded --np 8                 # mesh + run + render
    python run_case.py --generate --case c2 --power 2500 --np 8 # generate (extra args -> generate_case.py) then run
    python run_case.py --case case_lwded --steps mesh           # mesh + initial fields only
    python run_case.py --case case_lwded --steps solve --np 8   # (re)start the solver (continues from latest time)
    python run_case.py --case case_lwded --steps viz            # renders only
    python run_case.py --case case_lwded --smoke 50 --np 4      # 50 time steps sanity check
    python run_case.py --build                                  # compile laserWireDEDFoam only

OpenFOAM: uses the sourced environment, else the newest /usr/lib/openfoam/openfoam*/etc/bashrc
(or --bashrc). Visualisation uses --python (default: ~/vizenv/bin/python if present).
"""
from __future__ import annotations

import argparse
import glob
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def find_bashrc(explicit):
    if explicit:
        return explicit
    if os.environ.get("WM_PROJECT_DIR"):
        return None
    c = sorted(glob.glob("/usr/lib/openfoam/openfoam*/etc/bashrc") + glob.glob("/opt/openfoam*/etc/bashrc")
               + glob.glob(os.path.expanduser("~/OpenFOAM/OpenFOAM-v*/etc/bashrc")))
    return c[-1] if c else None


def sh(cmd, cwd, bashrc, log=None, check=True):
    pre = f"source {shlex.quote(bashrc)} >/dev/null 2>&1 || true; " if bashrc else ""
    full = f"{pre}cd {shlex.quote(str(cwd))} && {cmd}"
    print(f"[run] {cmd}" + (f"  (log: {log})" if log else ""), flush=True)
    if log:
        with open(Path(cwd) / log, "w") as fh:
            rc = subprocess.run(["bash", "-c", full], stdout=fh, stderr=subprocess.STDOUT).returncode
    else:
        rc = subprocess.run(["bash", "-c", full]).returncode
    if check and rc:
        tail = ""
        if log and (Path(cwd) / log).exists():
            tail = "".join((Path(cwd) / log).read_text(errors="replace").splitlines(True)[-25:])
        raise SystemExit(f"command failed ({rc}): {cmd}\n{tail}")
    return rc


def set_entry(case, key, value):
    f = case / "system/controlDict"
    t = f.read_text()
    t, n = re.subn(rf"^(\s*{key}\s+)[^;]+;", rf"\g<1>{value};", t, count=1, flags=re.M)
    if n:
        f.write_text(t)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", default="case_lwded")
    ap.add_argument("--np", type=int, default=8)
    ap.add_argument("--steps", choices=["all", "mesh", "solve", "viz"], default="all")
    ap.add_argument("--smoke", type=int, metavar="N")
    ap.add_argument("--build", action="store_true", help="compile the solver (and exit if no case)")
    ap.add_argument("--bashrc")
    ap.add_argument("--python", default=None, help="python with pyvista for visualize.py")
    ap.add_argument("--viz-out", default=None)
    ap.add_argument("--generate", action="store_true", help="run generate_case.py first (extra args passed)")
    a, rest = ap.parse_known_args()
    bashrc = find_bashrc(a.bashrc)
    case = Path(a.case)
    if not case.is_absolute():
        case = HERE / case
    if a.build or not glob.glob(os.path.expanduser("~/OpenFOAM/*/platforms/*/bin/laserWireDEDFoam")):
        sh("./Allwmake", HERE / "solver", bashrc, log="build.log")
        if a.build and not a.generate and a.steps == "all" and not case.exists():
            return 0
    if a.generate:
        import generate_case
        generate_case.main(["--case", str(case), "--np", str(a.np)] + rest)
    elif rest:
        raise SystemExit(f"unknown arguments {rest} (use --generate to pass them to generate_case.py)")
    if a.steps in ("all", "mesh"):
        # the case's own Allrun knows the full mesh sequence (blockMesh, optional wire-box refinement,
        # topoSet/createPatch, setFields, optional setExprFields for the stranded wire, decomposePar)
        sh(f"MESH_ONLY=1 ./Allrun {a.np}", case, bashrc, "log.Allrun.mesh")
    if a.steps in ("all", "solve"):
        if a.smoke:
            sh(f"foamDictionary -entry stopAt -set nextWrite system/controlDict >/dev/null", case, bashrc)
        solver = "laserWireDEDFoam" + (" -parallel" if a.np > 1 else "")
        mpi = f"mpirun -np {a.np} " if a.np > 1 else ""
        if a.smoke:
            sh(f"timeout 3600 bash -c '{mpi}{solver} > log.laserWireDEDFoam 2>&1 & PID=$!; "
               f"while kill -0 $PID 2>/dev/null; do n=$(grep -c \"^Time =\" log.laserWireDEDFoam); "
               f"[ $n -ge {a.smoke} ] && kill $PID; sleep 2; done'", case, bashrc, check=False)
            sh("foamDictionary -entry stopAt -set endTime system/controlDict >/dev/null", case, bashrc)
            print(open(case / "log.laserWireDEDFoam").read()[-3000:])
            return 0
        sh(f"{mpi}{solver}", case, bashrc, "log.laserWireDEDFoam")
    if a.steps in ("all", "viz"):
        py = a.python or (os.path.expanduser("~/vizenv/bin/python")
                          if os.path.exists(os.path.expanduser("~/vizenv/bin/python")) else sys.executable)
        out = a.viz_out or str(case / "viz")
        sh(f"{shlex.quote(py)} {shlex.quote(str(HERE / 'visualize.py'))} --case {shlex.quote(str(case))} "
           f"--out {shlex.quote(out)}", case, None, "log.visualize", check=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
