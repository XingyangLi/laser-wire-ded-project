#!/usr/bin/env python3
"""
Laser wire DED control GUI (tkinter).

Runs on Windows (Python 3.11+) against the WSL Ubuntu-24.04 OpenFOAM stack, or
locally on Linux when OpenFOAM is available. Long jobs go through
launch_wsl_job.ps1 so WSL stays attached and the PC stays awake.

    python app.py
    # or double-click launch_gui.bat on Windows
"""
from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

try:
    import tkinter as tk
    from tkinter import ttk, messagebox, filedialog, scrolledtext
except ImportError as e:
    sys.stderr.write(
        "tkinter is required. On Windows use Python from python.org; "
        "on Ubuntu: sudo apt install python3-tk\n"
    )
    raise SystemExit(1) from e

HERE = Path(__file__).resolve().parent
# Generator scripts (generate_case.py, materials.py, ...) live in the repo root
# (one level up). Fall back to the old gui/project/ copy layout if needed.
PROJECT = HERE.parent if (HERE.parent / "generate_case.py").exists() else HERE / "project"
JOBS = HERE / "jobs"

# ---------------------------------------------------------------------------
# Paths / environment
# ---------------------------------------------------------------------------

IS_WIN = os.name == "nt"
# Windows project root = repo root (viz output goes to <root>\viz\<case>, git-ignored)
DEFAULT_WIN_ROOT = HERE.parent
DEFAULT_WSL_DISTRO = "Ubuntu-24.04"
DEFAULT_WSL_WORKDIR = "~/laser_wire_ded_stranded"
DEFAULT_WSL_OF_BASHRC = "/usr/lib/openfoam/openfoam2406/etc/bashrc"
DEFAULT_VIZENV = "~/vizenv/bin/python"

PROTECTED_CASE_RE = re.compile(
    r"^(full_transitional_r|results_keep$|laser_wire_ded_scan)",
    re.I,
)
PROTECTED_WSL_ROOTS = ("~/laser_wire_ded", "~/laser_wire_ded_scan", "/home/dukyong/laser_wire_ded")

PAPER = {
    "normal": dict(power=600.0, scan_mm_s=6.7, wfs_mm_s=11.4, direction="+", focus_mm=0.5),
    "lof": dict(power=400.0, scan_mm_s=10.0, wfs_mm_s=17.0, direction="+", focus_mm=0.5),
    "transitional_r": dict(power=600.0, scan_mm_s=5.8, wfs_mm_s=29.0, direction="-", focus_mm=0.5),
}

MATERIALS = ["Invar36", "SS304", "316L", "Ti6Al4V", "IN718", "Fe", "Ni"]
PRESETS = [
    "Transitional-R solid",
    "Transitional-R 7-strand (contact)",
    "Fe+Ni 5-strand on Invar",
    "Normal (solid)",
    "LoF (solid)",
    "Custom single-beam",
]


def win_to_wsl(path: Path | str) -> str:
    p = str(path).replace("\\", "/")
    m = re.match(r"^([A-Za-z]):/(.*)$", p)
    if m:
        return f"/mnt/{m.group(1).lower()}/{m.group(2)}"
    return p


def expand_user_wsl(path: str) -> str:
    if path.startswith("~/"):
        return "/home/dukyong/" + path[2:]
    if path == "~":
        return "/home/dukyong"
    return path


# ---------------------------------------------------------------------------
# Parameter model
# ---------------------------------------------------------------------------

class Params:
    """GUI state -> generate_case.py argv."""

    def __init__(self):
        self.case = f"gui_{datetime.now().strftime('%Y%m%d_%H%M')}"
        self.laser_config = "transitional_r"  # single|normal|lof|transitional_r
        self.power_w: Optional[float] = None  # None = use paper/default
        self.scan_mm_s: Optional[float] = None
        self.wfs_mm_s: Optional[float] = None
        self.spot_radius_mm = 1.2
        self.focus_mm = 0.5
        self.beam_radius_mm = 0.5
        self.beam_angle_deg = 25.0
        self.beam_direction = "-"
        self.wire_type = "solid"  # solid|stranded
        self.wire_diameter_mm: Optional[float] = None  # None -> generate default
        self.strands = 7
        self.strand_layout = "auto"
        self.strand_diameter_mm: Optional[float] = None
        self.strand_gap_mm = 0.04
        self.lay_length_mm: Optional[float] = None
        self.lay_direction = "right"
        self.strand_feed_basis = "metal"
        self.strand_materials = ""
        self.feed_start_s = 0.02
        self.feed_angle_deg: Optional[float] = None
        self.wire_gap_mm: Optional[float] = None
        self.track_length_mm: Optional[float] = None
        self.end_time_s: Optional[float] = None
        self.write_interval_s = 0.01
        self.resolution = "medium"
        self.dx_um: Optional[float] = None
        self.np = 8
        self.dim = "3d"
        self.domain_y = "auto"
        self.material = ""  # empty = let generate_case choose
        self.wire_material = ""
        self.substrate_material = ""
        self.max_wfs_mm_s = 100.0
        self.feed_ref_diameter_mm: Optional[float] = None
        self.liquidus = "table"
        self.wire_refine: Optional[int] = None
        self.no_wire_stubbing = False
        self.no_melted_follow_substrate = False

    def validate(self) -> list[str]:
        errs = []
        name = (self.case or "").strip()
        if not name:
            errs.append("Case name is required.")
        elif not re.match(r"^[A-Za-z0-9][A-Za-z0-9_\-]*$", name):
            errs.append("Case name: letters, digits, _ and - only.")
        elif PROTECTED_CASE_RE.search(name):
            errs.append(f"Case name '{name}' is protected (existing production results).")
        if self.wire_type == "stranded" and self.strands < 2:
            errs.append("Stranded wire needs at least 2 strands.")
        if self.strand_materials.strip():
            mats = [x.strip() for x in self.strand_materials.split(",") if x.strip()]
            if self.wire_type != "stranded":
                errs.append("Strand materials require wire type = stranded.")
            if len(mats) != self.strands:
                errs.append(f"Strand materials list {len(mats)} entries but strands={self.strands}.")
            for m in mats:
                if m not in MATERIALS:
                    errs.append(f"Unknown strand material '{m}'.")
        if self.np < 1 or self.np > 64:
            errs.append("NP should be between 1 and 64.")
        if self.end_time_s is not None and self.end_time_s <= 0:
            errs.append("End time must be > 0.")
        if self.track_length_mm is not None and self.track_length_mm <= 0:
            errs.append("Track length must be > 0.")
        return errs

    def to_argv(self) -> list[str]:
        a: list[str] = ["--case", self.case, "--np", str(self.np)]
        a += ["--laser-config", self.laser_config]
        a += ["--wire-type", self.wire_type]
        a += ["--resolution", self.resolution]
        a += ["--dim", self.dim]
        a += ["--domain-y", self.domain_y]
        a += ["--write-interval", str(self.write_interval_s)]
        a += ["--feed-start", str(self.feed_start_s)]
        a += ["--focus-height", str(self.focus_mm * 1e-3)]
        a += ["--beam-radius", str(self.beam_radius_mm * 1e-3)]
        a += ["--beam-angle", str(self.beam_angle_deg)]
        a += ["--spot-radius", str(self.spot_radius_mm * 1e-3)]
        a += ["--max-wfs", str(self.max_wfs_mm_s * 1e-3)]
        a += ["--liquidus", self.liquidus]
        if self.laser_config != "single" or self.beam_direction:
            a += ["--beam-direction", self.beam_direction]
        if self.power_w is not None:
            a += ["--power", str(self.power_w)]
        if self.scan_mm_s is not None:
            a += ["--scan-speed", str(self.scan_mm_s * 1e-3)]
        if self.wfs_mm_s is not None:
            a += ["--wire-feed-speed", str(self.wfs_mm_s * 1e-3)]
        if self.wire_diameter_mm is not None:
            a += ["--wire-diameter", str(self.wire_diameter_mm * 1e-3)]
        if self.feed_angle_deg is not None:
            a += ["--feed-angle", str(self.feed_angle_deg)]
        if self.wire_gap_mm is not None:
            a += ["--wire-gap", str(self.wire_gap_mm * 1e-3)]
        if self.track_length_mm is not None:
            a += ["--track-length", str(self.track_length_mm * 1e-3)]
        if self.end_time_s is not None:
            a += ["--end-time", str(self.end_time_s)]
        if self.dx_um is not None:
            a += ["--dx", str(self.dx_um * 1e-6)]
        if self.material:
            a += ["--material", self.material]
        if self.wire_material:
            a += ["--wire-material", self.wire_material]
        if self.substrate_material:
            a += ["--substrate-material", self.substrate_material]
        if self.wire_type == "stranded":
            a += ["--strands", str(self.strands)]
            a += ["--strand-layout", self.strand_layout]
            a += ["--strand-gap", str(self.strand_gap_mm * 1e-3)]
            a += ["--lay-direction", self.lay_direction]
            a += ["--strand-feed-basis", self.strand_feed_basis]
            if self.strand_diameter_mm is not None:
                a += ["--strand-diameter", str(self.strand_diameter_mm * 1e-3)]
            if self.lay_length_mm is not None:
                a += ["--lay-length", str(self.lay_length_mm * 1e-3)]
            if self.strand_materials.strip():
                a += ["--strand-materials", self.strand_materials.strip()]
            if self.feed_ref_diameter_mm is not None:
                a += ["--feed-reference-diameter", str(self.feed_ref_diameter_mm * 1e-3)]
        if self.wire_refine is not None:
            a += ["--wire-refine", str(self.wire_refine)]
        if self.no_wire_stubbing:
            a += ["--no-wire-stubbing"]
        if self.no_melted_follow_substrate:
            a += ["--no-melted-follow-substrate"]
        return a

    def command_preview(self) -> str:
        return "python3 generate_case.py " + " ".join(shlex.quote(x) for x in self.to_argv())


# ---------------------------------------------------------------------------
# Backend (Windows+WSL or local Linux)
# ---------------------------------------------------------------------------

class Backend:
    def __init__(self, win_root: Path, wsl_distro: str, wsl_workdir: str, of_bashrc: str):
        self.win_root = win_root
        self.wsl_distro = wsl_distro
        self.wsl_workdir = wsl_workdir
        self.of_bashrc = of_bashrc
        self.launcher = win_root / "launch_wsl_job.ps1"
        if not self.launcher.exists():
            alt = win_root / "scripts" / "pc" / "launch_wsl_job.ps1"
            if alt.exists():
                self.launcher = alt
        JOBS.mkdir(parents=True, exist_ok=True)

    def _guard_workdir(self):
        wd = expand_user_wsl(self.wsl_workdir).rstrip("/")
        protected = {expand_user_wsl(b).rstrip("/") for b in PROTECTED_WSL_ROOTS}
        # ~/laser_wire_ded is protected, but ~/laser_wire_ded_stranded is the normal workdir
        for b in protected:
            if wd == b:
                raise RuntimeError(f"Refusing to use protected WSL workdir {wd}")
            # only block subdirs of exact protected roots (not *_stranded / *_scan siblings via prefix of parent)
            if b.endswith("/laser_wire_ded") or b.endswith("laser_wire_ded"):
                # block wd that is laser_wire_ded or laser_wire_ded/<something>, not laser_wire_ded_*
                if wd == b or wd.startswith(b + "/"):
                    raise RuntimeError(f"Refusing to use protected WSL workdir {wd}")
            elif wd.startswith(b + "/"):
                raise RuntimeError(f"Refusing to use protected WSL workdir {wd}")

    def sync_project_to_wsl(self) -> str:
        """Copy gui/project/*.py into the WSL workdir (scripts only)."""
        self._guard_workdir()
        src = win_to_wsl(PROJECT) if IS_WIN else str(PROJECT)
        wd = expand_user_wsl(self.wsl_workdir)
        cmd = (
            f"mkdir -p {shlex.quote(wd)} && "
            f"cp -a {shlex.quote(src)}/*.py {shlex.quote(wd)}/ && "
            f"ls {shlex.quote(wd)}/generate_case.py"
        )
        return self.run_wsl(cmd, check=True)

    def run_wsl(self, bash_cmd: str, check: bool = False, timeout: Optional[float] = 120) -> str:
        if IS_WIN:
            full = ["wsl.exe", "-d", self.wsl_distro, "--", "bash", "-lc", bash_cmd]
        else:
            full = ["bash", "-lc", bash_cmd]
        p = subprocess.run(full, capture_output=True, text=True, timeout=timeout)
        out = (p.stdout or "") + (("\n" + p.stderr) if p.stderr else "")
        if check and p.returncode:
            raise RuntimeError(out or f"exit {p.returncode}")
        return out

    def write_job_script(self, name: str, body: str) -> Path:
        JOBS.mkdir(parents=True, exist_ok=True)
        path = JOBS / name
        path.write_text(body.replace("\r\n", "\n"), encoding="utf-8", newline="\n")
        return path

    def launch_detached(self, script_path: Path, log_path: Path) -> None:
        """Start launch_wsl_job.ps1 hidden (Windows) or nohup bash (Linux)."""
        log_path.parent.mkdir(parents=True, exist_ok=True)
        if IS_WIN:
            if not self.launcher.exists():
                raise RuntimeError(f"Missing {self.launcher}")
            wsl_script = win_to_wsl(script_path)
            # Write a tiny starter so quoting stays simple under PowerShell 5.1
            starter = JOBS / f"_start_{script_path.stem}.ps1"
            starter.write_text(
                "Start-Process -WindowStyle Hidden -FilePath powershell.exe "
                f"-ArgumentList @('-NoProfile','-ExecutionPolicy','Bypass',"
                f"'-File','{self.launcher}',"
                f"'-Script','{wsl_script}',"
                f"'-Log','{log_path}')" + chr(10),
                encoding="utf-8",
                newline=chr(10),
            )
            subprocess.Popen(
                [
                    "powershell.exe", "-NoProfile", "-WindowStyle", "Hidden",
                    "-ExecutionPolicy", "Bypass",
                    "-File", str(starter),
                ],
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        else:
            subprocess.Popen(
                ["bash", str(script_path)],
                stdout=open(log_path, "w"),
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )

    def case_paths(self, case: str) -> dict[str, str]:
        wd = expand_user_wsl(self.wsl_workdir) if IS_WIN else str(Path(self.wsl_workdir).expanduser())
        viz_win = self.win_root / "viz" / case
        return {
            "case_dir": f"{wd}/{case}",
            "status": f"{wd}/{case}.status",
            "log": f"{wd}/{case}/log.laserWireDEDFoam",
            "mesh_log": f"{wd}/{case}/log.Allrun.mesh",
            "viz_win": str(viz_win),
            "viz_wsl": win_to_wsl(viz_win) if IS_WIN else str(viz_win),
            "job_out": str(HERE / "jobs" / f"{case}.out"),
        }

    def make_pipeline_script(self, params: Params, steps: str) -> Path:
        """steps: generate | mesh | solve | viz | generate_mesh | all"""
        self._guard_workdir()
        argv = params.to_argv()
        # force absolute case path under workdir
        case = params.case
        paths = self.case_paths(case)
        proj_wsl = win_to_wsl(PROJECT) if IS_WIN else str(PROJECT)
        wd = expand_user_wsl(self.wsl_workdir)
        of = self.of_bashrc
        gen_args = " ".join(shlex.quote(x) for x in argv)
        # rewrite --case to absolute under workdir
        gen_args = re.sub(
            r"--case\s+\S+",
            f"--case {shlex.quote(case)}",
            gen_args,
            count=1,
        )
        is_multi = bool(params.strand_materials.strip())
        viz_py = "visualize_multicomp.py" if is_multi else "visualize.py"
        vizenv = DEFAULT_VIZENV
        body = f"""#!/bin/bash
set -euo pipefail
WSL_WD={shlex.quote(wd)}
CASE={shlex.quote(case)}
NP={params.np}
SRC_PROJ={shlex.quote(proj_wsl)}
OUT_VIZ={shlex.quote(paths['viz_wsl'])}
ST="$WSL_WD/$CASE.status"
mkdir -p "$WSL_WD"
cd "$WSL_WD"
# sync latest generators (never delete case dirs)
cp -a "$SRC_PROJ"/*.py "$WSL_WD/"
source {shlex.quote(of)} >/dev/null 2>&1 || true
echo "$(date) GUI job steps={steps} NP=$NP" >> "$ST"
export PATH="$HOME/lwded_bin:$HOME/OpenFOAM/$USER-v2406/platforms/linux64GccDPInt32Opt/bin:$PATH"  # prefer rebuilt solver
"""
        if steps in ("generate", "generate_mesh", "all"):
            body += f"""
echo "$(date) generate..." >> "$ST"
python3 generate_case.py {gen_args} > "gen_$CASE.log" 2>&1 \\
  || {{ echo "$(date) GENERATE FAILED" >> "$ST"; exit 1; }}
mkdir -p "$OUT_VIZ"
cp -f "gen_$CASE.log" "$OUT_VIZ/" 2>/dev/null || true
cp -f "$CASE/case_params.json" "$OUT_VIZ/" 2>/dev/null || true
echo "$(date) generate done" >> "$ST"
"""
        if steps in ("mesh", "generate_mesh", "all"):
            body += f"""
echo "$(date) mesh..." >> "$ST"
(cd "$CASE" && MESH_ONLY=1 ./Allrun $NP) \\
  || {{ echo "$(date) MESH FAILED" >> "$ST"; exit 1; }}
echo "$(date) mesh done" >> "$ST"
"""
        if steps in ("solve", "all"):
            body += f"""
echo "$(date) solve..." >> "$ST"
cd "$CASE"
if [ "$NP" -gt 1 ]; then
  mpirun -np "$NP" laserWireDEDFoam -parallel > log.laserWireDEDFoam 2>&1
else
  laserWireDEDFoam > log.laserWireDEDFoam 2>&1
fi
rc=$?
cd ..
echo "$(date) solver finished rc=$rc" >> "$ST"
[ $rc -eq 0 ] || exit $rc
"""
        if steps in ("viz", "all"):
            body += f"""
echo "$(date) visualize..." >> "$ST"
mkdir -p "$OUT_VIZ"
VIZPY={shlex.quote(viz_py)}
if [ -x {shlex.quote(vizenv)} ]; then PY={shlex.quote(vizenv)}; else PY=python3; fi
"$PY" "$VIZPY" --case "$CASE" --out "$OUT_VIZ" > "$CASE/log.visualize" 2>&1 \\
  || echo "$(date) visualize had errors (see log.visualize)" >> "$ST"
echo "$(date) visualize done" >> "$ST"
"""
        body += f'echo "$(date) ALL DONE steps={steps}" >> "$ST"\n'
        return self.write_job_script(f"job_{case}_{steps}.sh", body)

    def probe_status(self, case: str, prefer_running: bool) -> dict:
        """Ask WSL for a plain-language summary of the run that is actually on disk."""
        probe = HERE / "wsl_status_probe.py"
        probe_wsl = win_to_wsl(probe) if IS_WIN else str(probe)
        flag = " --prefer-running" if prefer_running else ""
        cmd = (
            f"python3 {shlex.quote(probe_wsl)} --case {shlex.quote(case)} "
            f"--workdir {shlex.quote(self.wsl_workdir)}{flag}"
        )
        try:
            raw = self.run_wsl(cmd, timeout=40)
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
        for line in reversed(raw.splitlines()):
            line = line.strip()
            if line.startswith("{") and line.endswith("}"):
                try:
                    return json.loads(line)
                except json.JSONDecodeError:
                    break
        return {"ok": False, "error": (raw or "WSL returned no status").strip()[:1500]}

    def render_latest(self, case_dir: str, case_name: str, multicomp: bool) -> str:
        """Render the newest saved snapshot of a case. Does not start the solver."""
        viz_win = self.win_root / "viz" / case_name
        viz_win.mkdir(parents=True, exist_ok=True)
        viz_wsl = win_to_wsl(viz_win) if IS_WIN else str(viz_win)
        script = "visualize_multicomp.py" if multicomp else "visualize.py"
        py_script = win_to_wsl(PROJECT / script) if IS_WIN else str(PROJECT / script)
        cmd = (
            f"source {shlex.quote(self.of_bashrc)} >/dev/null 2>&1 || true; "
            'if [ -x "$HOME/vizenv/bin/python" ]; then PY="$HOME/vizenv/bin/python"; else PY=python3; fi; '
            f'"$PY" {shlex.quote(py_script)} --case {shlex.quote(case_dir)} '
            f"--out {shlex.quote(viz_wsl)} --only-latest"
        )
        out = self.run_wsl(cmd, check=True, timeout=300)
        return (out or "render finished") + f"\nPictures: {viz_win}"

    def generate_print(self, params: Params) -> str:
        """Validate by running generate_case --print (no files written beyond sync)."""
        self.sync_project_to_wsl()
        argv = params.to_argv() + ["--print"]
        # use a dummy case name under workdir for parser
        args = " ".join(shlex.quote(x) for x in argv)
        wd = expand_user_wsl(self.wsl_workdir)
        cmd = f"cd {shlex.quote(wd)} && python3 generate_case.py {args}"
        return self.run_wsl(cmd, check=True, timeout=60)

    def generate_only(self, params: Params) -> str:
        self.sync_project_to_wsl()
        argv = params.to_argv()
        args = " ".join(shlex.quote(x) for x in argv)
        wd = expand_user_wsl(self.wsl_workdir)
        cmd = (
            f"cd {shlex.quote(wd)} && python3 generate_case.py {args} "
            f"&& test -f {shlex.quote(params.case)}/case_params.json "
            f"&& echo GENERATED_OK"
        )
        return self.run_wsl(cmd, check=True, timeout=120)


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Laser Wire DED — Run Control")
        self.geometry("1000x920")
        self.minsize(900, 740)
        self._status_busy = False
        self._watch_pinned = False
        self._pinned_dir = ""
        self._watch_dirs: dict[str, str] = {}
        self._watched_case: dict = {}
        self._status_after = None

        self.params = Params()
        win_root = DEFAULT_WIN_ROOT if IS_WIN else HERE.parent
        if IS_WIN and not win_root.exists():
            win_root = HERE.parent
        self.win_root_var = tk.StringVar(value=str(win_root))
        self.wsl_distro_var = tk.StringVar(value=DEFAULT_WSL_DISTRO)
        self.wsl_wd_var = tk.StringVar(value=DEFAULT_WSL_WORKDIR)
        self.of_bashrc_var = tk.StringVar(value=DEFAULT_WSL_OF_BASHRC)

        self._vars: dict[str, tk.Variable] = {}
        self._build()
        self.apply_preset("Transitional-R solid")
        self._log("Ready. The panel under the buttons follows whatever run is actually going, including one started from a terminal.")
        self._log(f"Project scripts: {PROJECT}")
        self._log(f"Windows root: {self.win_root_var.get()}")
        self._log(f"WSL workdir: {self.wsl_wd_var.get()} (solver + cases)")
        self.after(600, self.refresh_status)
        self._status_after = self.after(8000, self._schedule_status)

    def backend(self) -> Backend:
        return Backend(
            Path(self.win_root_var.get()),
            self.wsl_distro_var.get().strip(),
            self.wsl_wd_var.get().strip(),
            self.of_bashrc_var.get().strip(),
        )

    # ---- layout ----
    def _build(self):
        top = ttk.Frame(self, padding=8)
        top.pack(fill=tk.BOTH, expand=True)

        # preset + paths
        bar = ttk.Frame(top)
        bar.pack(fill=tk.X)
        ttk.Label(bar, text="Preset:").pack(side=tk.LEFT)
        self.preset_var = tk.StringVar(value=PRESETS[0])
        cb = ttk.Combobox(bar, textvariable=self.preset_var, values=PRESETS, width=36, state="readonly")
        cb.pack(side=tk.LEFT, padx=4)
        cb.bind("<<ComboboxSelected>>", lambda e: self.apply_preset(self.preset_var.get()))
        ttk.Button(bar, text="Apply preset", command=lambda: self.apply_preset(self.preset_var.get())).pack(side=tk.LEFT)

        paths = ttk.LabelFrame(top, text="Paths", padding=6)
        paths.pack(fill=tk.X, pady=6)
        self._path_row(paths, 0, "Windows project root", self.win_root_var)
        self._path_row(paths, 1, "WSL distro", self.wsl_distro_var)
        self._path_row(paths, 2, "WSL workdir (cases/solver)", self.wsl_wd_var)
        self._path_row(paths, 3, "OpenFOAM bashrc", self.of_bashrc_var)

        nb = ttk.Notebook(top)
        nb.pack(fill=tk.BOTH, expand=True, pady=4)

        f_case = ttk.Frame(nb, padding=8)
        f_laser = ttk.Frame(nb, padding=8)
        f_wire = ttk.Frame(nb, padding=8)
        f_mesh = ttk.Frame(nb, padding=8)
        f_mat = ttk.Frame(nb, padding=8)
        nb.add(f_case, text="Case")
        nb.add(f_laser, text="Laser / process")
        nb.add(f_wire, text="Wire")
        nb.add(f_mesh, text="Mesh / run")
        nb.add(f_mat, text="Materials")

        # Case
        self._entry(f_case, "case", "Case name", self.params.case, width=40)
        ttk.Label(
            f_case,
            text="Cases are written under the WSL workdir. Protected names (full_transitional_r*, results_keep) are blocked.",
            wraplength=700,
        ).grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=4)

        # Laser
        self._combo(f_laser, "laser_config", "Laser config",
                    ["transitional_r", "normal", "lof", "single"], "transitional_r")
        self._entry(f_laser, "power_w", "Power [W] (blank=preset)", "")
        self._entry(f_laser, "scan_mm_s", "Scan speed [mm/s] (blank=preset)", "")
        self._entry(f_laser, "wfs_mm_s", "Wire feed speed [mm/s] (blank=preset)", "")
        self._entry(f_laser, "spot_radius_mm", "Spot radius [mm] (single beam)", "1.2")
        self._entry(f_laser, "focus_mm", "Focus height [mm]", "0.5")
        self._entry(f_laser, "beam_radius_mm", "Coax beam radius [mm]", "0.5")
        self._entry(f_laser, "beam_angle_deg", "Beam angle [deg]", "25")
        self._combo(f_laser, "beam_direction", "Beam direction (+/−)", ["-", "+"], "-")
        self._entry(f_laser, "feed_start_s", "Feed start [s]", "0.02")
        self._entry(f_laser, "track_length_mm", "Track length [mm] (blank=auto)", "")
        self._entry(f_laser, "end_time_s", "End time [s] (blank=auto)", "")
        self._entry(f_laser, "write_interval_s", "Write interval [s]", "0.01")

        # Wire
        self._combo(f_wire, "wire_type", "Wire type", ["solid", "stranded"], "solid")
        self._entry(f_wire, "wire_diameter_mm", "Wire diameter [mm] (blank=default)", "")
        self._entry(f_wire, "strands", "Strand count", "7")
        self._combo(f_wire, "strand_layout", "Strand layout", ["auto", "ring", "centre"], "auto")
        self._entry(f_wire, "strand_diameter_mm", "Strand diameter [mm] (blank=fit envelope)", "")
        self._entry(f_wire, "strand_gap_mm", "Strand gap [mm]", "0.04")
        self._entry(f_wire, "lay_length_mm", "Lay length [mm] (blank=10×d)", "")
        self._combo(f_wire, "lay_direction", "Lay direction", ["right", "left"], "right")
        self._combo(f_wire, "strand_feed_basis", "Feed basis", ["metal", "wfs"], "metal")
        self._entry(f_wire, "strand_materials", "Strand materials (e.g. Fe,Ni,Fe,Ni,Fe)", "", width=40)
        self._entry(f_wire, "feed_angle_deg", "Feed angle [deg] (blank=default)", "")
        self._entry(f_wire, "wire_gap_mm", "Wire tip gap [mm] (blank=default)", "")
        self._entry(f_wire, "feed_ref_diameter_mm", "Feed reference diameter [mm]", "")
        self._entry(f_wire, "max_wfs_mm_s", "Max WFS [mm/s]", "100")

        # Mesh
        self._combo(f_mesh, "resolution", "Resolution", ["coarse", "medium", "fine"], "medium")
        self._entry(f_mesh, "dx_um", "dx [µm] (blank=use resolution)", "")
        self._entry(f_mesh, "np", "MPI ranks (NP)", "8")
        self._combo(f_mesh, "dim", "Dimension", ["3d", "2d"], "3d")
        self._combo(f_mesh, "domain_y", "Domain Y", ["auto", "half", "full"], "auto")
        self._entry(f_mesh, "wire_refine", "Wire refine levels (blank=default)", "")

        # Materials
        mats = [""] + MATERIALS
        self._combo(f_mat, "material", "Material (both)", mats, "")
        self._combo(f_mat, "wire_material", "Wire material", mats, "")
        self._combo(f_mat, "substrate_material", "Substrate material", mats, "")
        self._combo(f_mat, "liquidus", "Liquidus model", ["table", "mixture"], "table")
        self._check(f_mat, "no_wire_stubbing", "Disable wire-stubbing guard (--no-wire-stubbing)")
        self._check(f_mat, "no_melted_follow_substrate", "Old molten follow feed (--no-melted-follow-substrate)")

        # Actions
        act = ttk.Frame(top, padding=4)
        act.pack(fill=tk.X)
        ttk.Button(act, text="Validate (--print)", command=self.on_validate).pack(side=tk.LEFT, padx=2)
        ttk.Button(act, text="Generate case", command=self.on_generate).pack(side=tk.LEFT, padx=2)
        ttk.Button(act, text="Mesh only", command=self.on_mesh).pack(side=tk.LEFT, padx=2)
        ttk.Button(act, text="Run solver", command=self.on_solve).pack(side=tk.LEFT, padx=2)
        ttk.Button(act, text="Generate+Mesh+Solve", command=self.on_all).pack(side=tk.LEFT, padx=2)
        ttk.Button(act, text="Refresh status", command=self.refresh_status).pack(side=tk.LEFT, padx=2)
        ttk.Button(act, text="Visualize", command=self.on_viz).pack(side=tk.LEFT, padx=2)
        ttk.Button(act, text="Open viz folder", command=self.on_open_viz).pack(side=tk.LEFT, padx=2)
        ttk.Button(act, text="Show CLI", command=self.on_show_cli).pack(side=tk.LEFT, padx=2)

        dash = ttk.LabelFrame(top, text="What is happening", padding=8)
        dash.pack(fill=tk.BOTH, expand=True, pady=4)
        self._dash = dash

        head_row = ttk.Frame(dash)
        head_row.pack(fill=tk.X)
        self.status_headline = tk.Label(
            head_row, text="Looking for a simulation…",
            font=("Segoe UI", 14, "bold"), anchor="w", justify=tk.LEFT,
        )
        self.status_headline.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.status_updated = ttk.Label(head_row, text="")
        self.status_updated.pack(side=tk.RIGHT)

        self.status_banner = tk.Label(
            dash, text="", anchor="w", justify=tk.LEFT, wraplength=920,
            bg="#fff4cc", padx=6, pady=4,
        )
        self.status_progress = ttk.Progressbar(dash, maximum=100, mode="determinate")
        self.status_progress.pack(fill=tk.X, pady=(6, 0))
        self.status_progress_label = ttk.Label(dash, text="")
        self.status_progress_label.pack(anchor="w")
        self.status_explain = tk.Label(
            dash, text="", anchor="w", justify=tk.LEFT, wraplength=920,
            font=("Segoe UI", 10),
        )
        self.status_explain.pack(fill=tk.X, pady=4)

        grid = ttk.Frame(dash)
        grid.pack(fill=tk.X, pady=2)
        self.status_facts = {}
        fact_rows = [
            ("where", "Case folder"),
            ("clock", "Simulation clock"),
            ("wall", "Computer time"),
            ("eta", "Time left"),
            ("pool", "Melt pool"),
            ("temp", "Hottest point"),
            ("bead", "Bead so far"),
            ("cores", "Cores"),
        ]
        for i, (key, label) in enumerate(fact_rows):
            r, c = divmod(i, 2)
            ttk.Label(grid, text=label, width=18).grid(row=r, column=c * 2, sticky=tk.W, pady=1)
            lab = ttk.Label(grid, text="—")
            lab.grid(row=r, column=c * 2 + 1, sticky=tk.W, padx=(0, 12))
            self.status_facts[key] = lab
        grid.columnconfigure(1, weight=1)
        grid.columnconfigure(3, weight=1)

        self.status_next = tk.Label(
            dash, text="", anchor="w", justify=tk.LEFT, wraplength=920,
            font=("Segoe UI", 10, "italic"),
        )
        self.status_next.pack(fill=tk.X, pady=(4, 2))

        controls = ttk.Frame(dash)
        controls.pack(fill=tk.X, pady=2)
        ttk.Label(controls, text="Watch:").pack(side=tk.LEFT)
        self.watch_var = tk.StringVar(value="")
        self.watch_combo = ttk.Combobox(controls, textvariable=self.watch_var, width=48, state="readonly")
        self.watch_combo.pack(side=tk.LEFT, padx=4)
        self.watch_combo.bind("<<ComboboxSelected>>", self._on_watch_selected)
        ttk.Button(controls, text="Refresh", command=self.refresh_status).pack(side=tk.LEFT, padx=2)
        self.auto_status = tk.BooleanVar(value=True)
        ttk.Checkbutton(controls, text="Auto-refresh", variable=self.auto_status).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text="Watch the case named above", command=self.watch_form_case).pack(side=tk.LEFT, padx=2)
        ttk.Button(controls, text="Picture of latest save", command=self.on_picture).pack(side=tk.LEFT, padx=2)

        dash.bind("<Configure>", self._reflow_status)

        tailf = ttk.LabelFrame(dash, text="Last lines from the solver", padding=4)
        tailf.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        self.solver_tail = scrolledtext.ScrolledText(tailf, height=6, wrap=tk.WORD, font=("Consolas", 9))
        self.solver_tail.pack(fill=tk.BOTH, expand=True)
        self.solver_tail.configure(state=tk.DISABLED)

        logf = ttk.LabelFrame(top, text="Activity", padding=4)
        logf.pack(fill=tk.BOTH, expand=False, pady=4)
        self.log = scrolledtext.ScrolledText(logf, height=5, wrap=tk.WORD, font=("Consolas", 9))
        self.log.pack(fill=tk.BOTH, expand=True)

    def _path_row(self, parent, row, label, var):
        ttk.Label(parent, text=label, width=28).grid(row=row, column=0, sticky=tk.W)
        ttk.Entry(parent, textvariable=var, width=70).grid(row=row, column=1, sticky=tk.EW, padx=4)
        parent.columnconfigure(1, weight=1)

    def _entry(self, parent, key, label, default, width=18, row=None):
        if row is None:
            row = parent.grid_size()[1]
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=2)
        var = tk.StringVar(value=str(default))
        self._vars[key] = var
        ttk.Entry(parent, textvariable=var, width=width).grid(row=row, column=1, sticky=tk.W, padx=4)

    def _combo(self, parent, key, label, values, default, row=None):
        if row is None:
            row = parent.grid_size()[1]
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, pady=2)
        var = tk.StringVar(value=str(default))
        self._vars[key] = var
        ttk.Combobox(parent, textvariable=var, values=values, width=28, state="readonly").grid(
            row=row, column=1, sticky=tk.W, padx=4
        )

    def _check(self, parent, key, label, row=None):
        if row is None:
            row = parent.grid_size()[1]
        var = tk.BooleanVar(value=False)
        self._vars[key] = var
        ttk.Checkbutton(parent, text=label, variable=var).grid(row=row, column=0, columnspan=2, sticky=tk.W)

    def _log(self, msg: str):
        ts = datetime.now().strftime("%H:%M:%S")
        self.log.insert(tk.END, f"[{ts}] {msg}\n")
        self.log.see(tk.END)
        self.update_idletasks()

    def _set(self, key, value):
        if key not in self._vars:
            return
        v = self._vars[key]
        if isinstance(v, tk.BooleanVar):
            v.set(bool(value))
        else:
            v.set("" if value is None else str(value))

    def _get_float(self, key) -> Optional[float]:
        s = str(self._vars[key].get()).strip()
        if s == "":
            return None
        return float(s)

    def _get_int(self, key) -> Optional[int]:
        s = str(self._vars[key].get()).strip()
        if s == "":
            return None
        return int(s)

    def read_params(self) -> Params:
        p = Params()
        p.case = str(self._vars["case"].get()).strip()
        p.laser_config = str(self._vars["laser_config"].get())
        p.power_w = self._get_float("power_w")
        p.scan_mm_s = self._get_float("scan_mm_s")
        p.wfs_mm_s = self._get_float("wfs_mm_s")
        p.spot_radius_mm = self._get_float("spot_radius_mm") or 1.2
        p.focus_mm = self._get_float("focus_mm") if self._get_float("focus_mm") is not None else 0.5
        p.beam_radius_mm = self._get_float("beam_radius_mm") or 0.5
        p.beam_angle_deg = self._get_float("beam_angle_deg") or 25.0
        p.beam_direction = str(self._vars["beam_direction"].get())
        p.wire_type = str(self._vars["wire_type"].get())
        p.wire_diameter_mm = self._get_float("wire_diameter_mm")
        p.strands = self._get_int("strands") or 7
        p.strand_layout = str(self._vars["strand_layout"].get())
        p.strand_diameter_mm = self._get_float("strand_diameter_mm")
        p.strand_gap_mm = self._get_float("strand_gap_mm") if self._get_float("strand_gap_mm") is not None else 0.04
        p.lay_length_mm = self._get_float("lay_length_mm")
        p.lay_direction = str(self._vars["lay_direction"].get())
        p.strand_feed_basis = str(self._vars["strand_feed_basis"].get())
        p.strand_materials = str(self._vars["strand_materials"].get()).strip()
        p.feed_start_s = self._get_float("feed_start_s") if self._get_float("feed_start_s") is not None else 0.02
        p.feed_angle_deg = self._get_float("feed_angle_deg")
        p.wire_gap_mm = self._get_float("wire_gap_mm")
        p.track_length_mm = self._get_float("track_length_mm")
        p.end_time_s = self._get_float("end_time_s")
        p.write_interval_s = self._get_float("write_interval_s") or 0.01
        p.resolution = str(self._vars["resolution"].get())
        p.dx_um = self._get_float("dx_um")
        p.np = self._get_int("np") or 8
        p.dim = str(self._vars["dim"].get())
        p.domain_y = str(self._vars["domain_y"].get())
        p.wire_refine = self._get_int("wire_refine")
        p.material = str(self._vars["material"].get()).strip()
        p.wire_material = str(self._vars["wire_material"].get()).strip()
        p.substrate_material = str(self._vars["substrate_material"].get()).strip()
        p.liquidus = str(self._vars["liquidus"].get())
        p.max_wfs_mm_s = self._get_float("max_wfs_mm_s") or 100.0
        p.feed_ref_diameter_mm = self._get_float("feed_ref_diameter_mm")
        p.no_wire_stubbing = bool(self._vars["no_wire_stubbing"].get())
        p.no_melted_follow_substrate = bool(self._vars["no_melted_follow_substrate"].get())
        return p

    def apply_preset(self, name: str):
        # reset blanks then set
        for k in self._vars:
            if isinstance(self._vars[k], tk.BooleanVar):
                self._vars[k].set(False)
        self._set("case", f"gui_{datetime.now().strftime('%Y%m%d_%H%M')}")
        self._set("spot_radius_mm", "1.2")
        self._set("beam_radius_mm", "0.5")
        self._set("beam_angle_deg", "25")
        self._set("write_interval_s", "0.01")
        self._set("resolution", "medium")
        self._set("np", "8")
        self._set("dim", "3d")
        self._set("domain_y", "auto")
        self._set("max_wfs_mm_s", "100")
        self._set("strand_gap_mm", "0.04")
        self._set("lay_direction", "right")
        self._set("strand_feed_basis", "metal")
        self._set("liquidus", "table")
        self._set("dx_um", "")
        self._set("track_length_mm", "")
        self._set("end_time_s", "")
        self._set("wire_diameter_mm", "")
        self._set("strand_diameter_mm", "")
        self._set("lay_length_mm", "")
        self._set("feed_angle_deg", "")
        self._set("wire_gap_mm", "")
        self._set("feed_ref_diameter_mm", "")
        self._set("wire_refine", "")
        self._set("strand_materials", "")
        self._set("material", "")
        self._set("wire_material", "")
        self._set("substrate_material", "")
        self._set("power_w", "")
        self._set("scan_mm_s", "")
        self._set("wfs_mm_s", "")

        if name.startswith("Transitional-R solid"):
            self._set("laser_config", "transitional_r")
            self._set("wire_type", "solid")
            self._set("focus_mm", "0.5")
            self._set("feed_start_s", "0.02")
            self._set("beam_direction", "-")
            self._set("case", "gui_tr_solid")
        elif "7-strand" in name:
            self._set("laser_config", "transitional_r")
            self._set("wire_type", "stranded")
            self._set("strands", "7")
            self._set("strand_layout", "auto")
            self._set("focus_mm", "0")  # contact setup
            self._set("feed_start_s", "0")
            self._set("beam_direction", "-")
            self._set("case", "gui_tr_7strand")
        elif "Fe+Ni" in name:
            self._set("laser_config", "transitional_r")
            self._set("wire_type", "stranded")
            self._set("strands", "5")
            self._set("strand_layout", "ring")
            self._set("strand_diameter_mm", "0.3")
            self._set("strand_materials", "Fe,Ni,Fe,Ni,Fe")
            self._set("substrate_material", "Invar36")
            self._set("focus_mm", "0")
            self._set("feed_start_s", "0")
            self._set("beam_direction", "-")
            self._set("case", "gui_fe_ni_5strand")
        elif name.startswith("Normal"):
            self._set("laser_config", "normal")
            self._set("wire_type", "solid")
            self._set("focus_mm", "0.5")
            self._set("feed_start_s", "0.02")
            self._set("beam_direction", "+")
            self._set("case", "gui_normal")
        elif name.startswith("LoF"):
            self._set("laser_config", "lof")
            self._set("wire_type", "solid")
            self._set("focus_mm", "0.5")
            self._set("feed_start_s", "0.02")
            self._set("beam_direction", "+")
            self._set("case", "gui_lof")
        else:  # Custom single-beam
            self._set("laser_config", "single")
            self._set("wire_type", "solid")
            self._set("power_w", "2000")
            self._set("scan_mm_s", "10")
            self._set("wfs_mm_s", "25")
            self._set("focus_mm", "0.5")
            self._set("feed_start_s", "0.02")
            self._set("beam_direction", "+")
            self._set("wire_material", "316L")
            self._set("substrate_material", "316L")
            self._set("case", "gui_custom")
        self._log(f"Applied preset: {name}")

    def _checked(self) -> Optional[Params]:
        try:
            p = self.read_params()
        except ValueError as e:
            messagebox.showerror("Invalid input", str(e))
            return None
        errs = p.validate()
        if errs:
            messagebox.showerror("Validation", "\n".join(errs))
            return None
        return p

    def _bg(self, title: str, fn: Callable[[], str]):
        self._log(f"{title}...")

        def work():
            try:
                out = fn()
                self.after(0, lambda: self._done(title, out, None))
            except Exception as e:
                self.after(0, lambda: self._done(title, "", e))

        threading.Thread(target=work, daemon=True).start()

    def _done(self, title, out, err):
        if err:
            self._log(f"{title} FAILED:\n{err}")
            messagebox.showerror(title, str(err)[:800])
        else:
            self._log(f"{title} OK:\n{out}")

    def on_validate(self):
        p = self._checked()
        if not p:
            return
        self._log("CLI: " + p.command_preview())
        be = self.backend()
        self._bg("Validate", lambda: be.generate_print(p))

    def on_generate(self):
        p = self._checked()
        if not p:
            return
        if not messagebox.askyesno(
            "Generate case",
            f"Write case '{p.case}' under {self.wsl_wd_var.get()}?\n"
            "(Does not start the solver.)",
        ):
            return
        be = self.backend()
        self._bg("Generate", lambda: be.generate_only(p))

    def _launch_steps(self, steps: str):
        p = self._checked()
        if not p:
            return
        if steps in ("solve", "all") and not messagebox.askyesno(
            "Start solver",
            f"Launch detached '{steps}' for case '{p.case}'?\n"
            "This can run for hours. PC will stay awake via launch_wsl_job.ps1.",
        ):
            return
        be = self.backend()

        def work():
            be.sync_project_to_wsl()
            script = be.make_pipeline_script(p, steps)
            log_path = Path(be.case_paths(p.case)["job_out"])
            be.launch_detached(script, log_path)
            return f"Started {steps}\nscript: {script}\nlog: {log_path}\nstatus: {be.case_paths(p.case)['status']}"

        self._bg(f"Launch {steps}", work)

    def on_mesh(self):
        self._launch_steps("generate_mesh")

    def on_solve(self):
        self._launch_steps("solve")

    def on_all(self):
        self._launch_steps("all")

    def _reflow_status(self, event):
        width = max(420, event.width - 28)
        for lab in (self.status_explain, self.status_next, self.status_banner, self.status_headline):
            lab.configure(wraplength=width)

    def _schedule_status(self):
        if self.auto_status.get():
            self.refresh_status()
        self._status_after = self.after(8000, self._schedule_status)

    def _on_watch_selected(self, _event=None):
        label = self.watch_var.get().strip()
        self._pinned_dir = self._watch_dirs.get(label, "")
        self._watch_pinned = True
        self.refresh_status()

    def watch_form_case(self):
        name = str(self._vars["case"].get()).strip()
        if not name:
            messagebox.showinfo("Case name", "Type a case name on the Case tab first.")
            return
        self._watch_pinned = True
        self._pinned_dir = ""
        self.watch_var.set(name)
        self.refresh_status()

    def refresh_status(self):
        if self._status_busy:
            return
        self._status_busy = True
        if self._watch_pinned and self._pinned_dir:
            chosen = self._pinned_dir
        else:
            label = self.watch_var.get().strip()
            chosen = self._watch_dirs.get(label, label)
        if not chosen:
            case_var = self._vars.get("case")
            chosen = str(case_var.get()).strip() if case_var is not None else ""
        prefer = not self._watch_pinned
        be = self.backend()

        def work():
            data = be.probe_status(chosen, prefer)
            self.after(0, lambda: self._show_status(data))

        threading.Thread(target=work, daemon=True).start()

    def _show_status(self, data: dict):
        self._status_busy = False
        self.status_updated.configure(text=datetime.now().strftime("updated %H:%M:%S"))
        if not data.get("ok", False):
            self.status_headline.configure(text="Could not read the run.", fg="#8a1c1c")
            self.status_explain.configure(
                text="Status lives in WSL, not in this Windows window. "
                + str(data.get("error") or "No details.")[:500]
            )
            self.status_next.configure(text="Check that Ubuntu-24.04 is installed and that `wsl` works from PowerShell.")
            self.status_banner.pack_forget()
            return

        focus = data.get("focus") or {}
        self._watched_case = focus
        banner = (data.get("banner") or "").strip()
        if banner:
            self.status_banner.configure(text=banner)
            if not self.status_banner.winfo_ismapped():
                self.status_banner.pack(fill=tk.X, pady=(4, 0), before=self.status_progress)
        else:
            self.status_banner.pack_forget()

        colors = {
            "running": "#0b6a3c",
            "meshing": "#8a5a00",
            "finished": "#0b4f8a",
            "stopped": "#8a1c1c",
            "failed": "#8a1c1c",
        }
        self.status_headline.configure(
            text=focus.get("headline") or "No simulation.",
            fg=colors.get(focus.get("stage"), "#222222"),
        )
        self.status_explain.configure(text=focus.get("explain") or "")
        self.status_next.configure(text=focus.get("next_step") or "")
        self.status_progress_label.configure(text=focus.get("progress_caption") or "")
        percent = focus.get("percent")
        if isinstance(percent, (int, float)):
            self.status_progress.configure(mode="determinate", value=float(percent))
        else:
            self.status_progress.configure(mode="determinate", value=0)
        facts = focus.get("facts") or {}
        for key, lab in self.status_facts.items():
            lab.configure(text=str(facts.get(key) or "—"))

        self._watch_dirs = {}
        labels = []
        focus_dir = focus.get("dir") or ""
        focus_label = ""
        for item in data.get("cases") or []:
            label = item.get("label") or item.get("dir") or ""
            directory = item.get("dir") or ""
            if not label:
                continue
            labels.append(label)
            self._watch_dirs[label] = directory
            if directory and directory == focus_dir:
                focus_label = label
        self.watch_combo.configure(values=labels)
        if focus_label and not self._watch_pinned:
            self.watch_var.set(focus_label)
        elif self._watch_pinned and self._pinned_dir:
            pinned_label = next((lb for lb, d in self._watch_dirs.items() if d == self._pinned_dir), "")
            if pinned_label:
                self.watch_var.set(pinned_label)

        self.solver_tail.configure(state=tk.NORMAL)
        self.solver_tail.delete("1.0", tk.END)
        self.solver_tail.insert(tk.END, focus.get("log_tail") or "(no solver log yet)")
        self.solver_tail.configure(state=tk.DISABLED)

    def on_picture(self):
        case = self._watched_case or {}
        if not case.get("dir"):
            messagebox.showinfo("No run", "Status has not found a case yet. Wait for the panel to update.")
            return
        if not messagebox.askyesno(
            "Picture of the pool",
            f"Render the newest saved moment of {case.get('name')}?\n\n"
            "The solver keeps running. One picture usually takes a minute or two.",
        ):
            return
        be = self.backend()
        case_dir = case["dir"]
        name = case.get("name") or "case"
        multicomp = bool(case.get("multicomp"))

        def work():
            out = be.render_latest(case_dir, name, multicomp)
            png = be.win_root / "viz" / name / "latest_3d.png"
            if png.is_file() and IS_WIN:
                self.after(0, lambda p=png: os.startfile(str(p)))
            return out

        self._bg("Picture", work)

    def on_viz(self):
        p = self._checked()
        if not p:
            return
        if not messagebox.askyesno("Visualize", f"Launch visualize job for '{p.case}'?"):
            return
        self._launch_steps("viz")

    def on_open_viz(self):
        p = self.read_params()
        paths = self.backend().case_paths(p.case)
        viz = Path(paths["viz_win"])
        viz.mkdir(parents=True, exist_ok=True)
        self._log(f"Opening {viz}")
        if IS_WIN:
            os.startfile(str(viz))  # noqa: S606
        else:
            subprocess.Popen(["xdg-open", str(viz)])

    def on_show_cli(self):
        p = self._checked()
        if not p:
            return
        self._log(p.command_preview())
        messagebox.showinfo("generate_case.py", p.command_preview())


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
