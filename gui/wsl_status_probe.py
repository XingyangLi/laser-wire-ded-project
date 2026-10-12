#!/usr/bin/env python3
"""Summarize a laserWireDEDFoam run in plain language. Prints one JSON object.

Runs inside WSL (it reads /proc and the OpenFOAM case). The Windows GUI calls it.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path

SETUP_TOKENS = (
    "blockMesh",
    "topoSet",
    "createPatch",
    "setFields",
    "setExprFields",
    "decomposePar",
    "checkMesh",
    "refineMesh",
    "Allrun",
)
MELT_RE = re.compile(
    r"MeltPool: L = (\S+) mm\s+W = (\S+) mm\s+D = (\S+) mm\s+"
    r"Tmax = (\S+) K.*?h = (\S+) w = (\S+) mm.*?penetration = (\S+) mm"
)
TIME_RE = re.compile(r"^Time = (\S+)\s*$", re.M)
EXEC_RE = re.compile(
    r"^ExecutionTime = (\S+) s\s+ClockTime = (\S+) s\s*$", re.M
)
DT_RE = re.compile(r"^deltaT = (\S+)\s*$", re.M)
END_RE = re.compile(r"^endTime\s+(\S+)\s*;", re.M)


def expand(path: str) -> str:
    return os.path.expanduser(path)


def fmt_dur(seconds: float | None) -> str:
    if seconds is None or seconds < 0 or seconds != seconds:
        return "not known yet"
    s = int(round(seconds))
    if s < 90:
        return f"{s} seconds"
    minutes, sec = divmod(s, 60)
    if minutes < 90:
        return f"{minutes} min {sec} s" if sec else f"{minutes} min"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes} min"


def fmt_clock(seconds: float | None) -> str:
    if seconds is None:
        return "not known yet"
    when = datetime.now() + timedelta(seconds=max(0.0, seconds))
    if seconds > 18 * 3600:
        return when.strftime("%a %I:%M %p").lstrip("0")
    return when.strftime("%I:%M %p").lstrip("0")


def fmt_sim(seconds: float | None) -> str:
    if seconds is None:
        return "—"
    if abs(seconds) < 1:
        return f"{seconds * 1000:.1f} ms"
    if abs(seconds) < 10:
        return f"{seconds:.3f} s"
    return f"{seconds:.2f} s"


def fmt_mm(value: float | None) -> str:
    if value is None:
        return "—"
    if abs(value) < 5e-4:
        return "0 mm"
    if abs(value) >= 0.1:
        return f"{value:.2f} mm"
    return f"{value:.3f} mm"


def read_tail(path: Path, nbytes: int = 500_000) -> str:
    try:
        with path.open("rb") as handle:
            handle.seek(0, os.SEEK_END)
            size = handle.tell()
            handle.seek(max(0, size - nbytes))
            data = handle.read().decode("utf-8", "replace")
    except OSError:
        return ""
    # Drop a partial first line when we started mid-file.
    if size_known_partial(path, nbytes):
        nl = data.find("\n")
        if nl >= 0:
            data = data[nl + 1 :]
    return data


def size_known_partial(path: Path, nbytes: int) -> bool:
    try:
        return path.stat().st_size > nbytes
    except OSError:
        return False


def list_procs() -> list[dict]:
    proc = Path("/proc")
    found = []
    if not proc.is_dir():
        return found
    try:
        clk = os.sysconf("SC_CLK_TCK")
        uptime = float(Path("/proc/uptime").read_text().split()[0])
    except (OSError, ValueError):
        clk, uptime = None, None
    for entry in proc.iterdir():
        if not entry.name.isdigit():
            continue
        try:
            raw = (entry / "cmdline").read_bytes().replace(b"\x00", b" ").decode("utf-8", "replace")
            cwd = os.readlink(entry / "cwd")
        except OSError:
            continue
        if not raw.strip():
            continue
        etime = None
        if clk and uptime is not None:
            try:
                stat = (entry / "stat").read_text()
                fields = stat[stat.rfind(")") + 2 :].split()
                start_ticks = int(fields[19])
                etime = max(0.0, uptime - start_ticks / clk)
            except (OSError, IndexError, ValueError):
                etime = None
        first = os.path.basename(raw.split()[0]) if raw.split() else ""
        kind = None
        # mpirun's command line contains the solver name; only the solver binary counts.
        if first.startswith("laserWireDEDFoam"):
            kind = "solver"
        elif any(tok in raw for tok in SETUP_TOKENS):
            kind = "setup"
        if kind:
            found.append({"pid": int(entry.name), "cwd": cwd, "kind": kind, "etime_s": etime, "cmd": raw.strip()[:180]})
    return found


def discover_cases(roots: list[str], extra: list[str]) -> list[Path]:
    seen = set()
    found: list[Path] = []

    def add(path: Path):
        try:
            key = str(path.resolve())
        except OSError:
            key = str(path)
        if key in seen:
            return
        if (path / "system" / "controlDict").is_file():
            seen.add(key)
            found.append(path)

    for raw in extra:
        if raw:
            add(Path(raw))
    for raw in roots:
        root = Path(expand(raw))
        if not root.is_dir():
            continue
        add(root)
        try:
            children = list(root.iterdir())
        except OSError:
            continue
        for child in children:
            if child.is_dir():
                add(child)
    return found


def end_time(case: Path) -> float | None:
    try:
        text = (case / "system" / "controlDict").read_text(errors="replace")
    except OSError:
        return None
    match = END_RE.search(text)
    if not match:
        return None
    try:
        return float(match.group(1).rstrip(";"))
    except ValueError:
        return None


def newest_saved_time(case: Path) -> float | None:
    best = None
    for folder in (case, case / "processor0"):
        if not folder.is_dir():
            continue
        try:
            names = list(folder.iterdir())
        except OSError:
            continue
        for name in names:
            if not name.is_dir():
                continue
            try:
                value = float(name.name)
            except ValueError:
                continue
            if value > 0 and (best is None or value > best):
                best = value
    return best


def parse_log(case: Path) -> dict:
    log = case / "log.laserWireDEDFoam"
    info = {
        "has_log": log.is_file(),
        "log_age_s": None,
        "sim_time_s": None,
        "clock_s": None,
        "delta_t_s": None,
        "rate": None,
        "pool": None,
        "fatal": False,
        "ended_clean": False,
        "tail": "",
        "t_line": "",
        "melt_line": "",
    }
    if not log.is_file():
        return info
    try:
        info["log_age_s"] = max(0.0, time.time() - log.stat().st_mtime)
    except OSError:
        pass
    text = read_tail(log)
    times = [float(x) for x in TIME_RE.findall(text)]
    clocks = [float(x[1]) for x in EXEC_RE.findall(text)]
    if times:
        info["sim_time_s"] = times[-1]
    if clocks:
        info["clock_s"] = clocks[-1]
    dts = DT_RE.findall(text)
    if dts:
        try:
            info["delta_t_s"] = float(dts[-1])
        except ValueError:
            pass
    if len(times) >= 2 and len(clocks) >= 2:
        n = min(len(times), len(clocks))
        times, clocks = times[-n:], clocks[-n:]
        i0 = max(0, n - 80)
        dt_sim = times[-1] - times[i0]
        dt_wall = clocks[-1] - clocks[i0]
        if dt_sim > 0 and dt_wall > 0:
            info["rate"] = dt_sim / dt_wall
    melts = list(MELT_RE.finditer(text))
    if melts:
        g = melts[-1].groups()
        try:
            info["pool"] = {
                "L_mm": float(g[0]),
                "W_mm": float(g[1]),
                "D_mm": float(g[2]),
                "Tmax_K": float(g[3]),
                "h_mm": float(g[4]),
                "w_mm": float(g[5]),
                "pen_mm": float(g[6]),
            }
        except ValueError:
            info["pool"] = None
    if "FOAM FATAL" in text or "FOAM exiting" in text or "Segmentation fault" in text:
        info["fatal"] = True
    if re.search(r"(?m)^End\s*$", text) or "Finalising parallel run" in text:
        info["ended_clean"] = True
    lines = [ln for ln in text.splitlines() if ln.strip()]
    info["tail"] = "\n".join(lines[-12:])
    t_lines = [ln for ln in lines if ln.startswith("T:")]
    melt_lines = [ln for ln in lines if ln.startswith("MeltPool:")]
    info["t_line"] = t_lines[-1] if t_lines else ""
    info["melt_line"] = melt_lines[-1] if melt_lines else ""
    return info


def log_mtime(case: Path) -> float:
    newest = 0.0
    for rel in ("log.laserWireDEDFoam", "log.blockMesh", "log.decomposePar", "log.setFields"):
        path = case / rel
        try:
            newest = max(newest, path.stat().st_mtime)
        except OSError:
            pass
    return newest


def is_multicomp(case: Path) -> bool:
    for rel in ("0/cFe", "0.orig/cFe.orig", "0/cNi", "0.orig/cNi.orig"):
        if (case / rel).is_file():
            return True
    return False


def short_home(path: str) -> str:
    home = str(Path.home())
    if path == home:
        return "~"
    if path.startswith(home + "/"):
        return "~/" + path[len(home) + 1 :]
    return path


def classify(case: Path, solvers_here: list[dict], setup_here: list[dict], info: dict, end: float | None) -> str:
    if solvers_here:
        return "running"
    if setup_here and not info["has_log"]:
        return "meshing"
    if not (case / "system" / "controlDict").is_file() and not info["has_log"]:
        return "absent"
    if info["fatal"] and not solvers_here:
        return "failed"
    sim = info["sim_time_s"]
    reached = end is not None and sim is not None and sim >= 0.98 * end
    if info["ended_clean"] or reached:
        return "finished"
    if info["has_log"]:
        return "stopped"
    if setup_here:
        return "meshing"
    if (case / "log.blockMesh").is_file() or (case / "processor0").is_dir():
        return "ready"
    if (case / "system" / "controlDict").is_file():
        return "ready"
    return "absent"


def readable_tail(info: dict) -> str:
    """A few lines a person can read, then the raw log underneath."""
    lines = []
    if info.get("sim_time_s") is not None:
        lines.append(f"Simulation clock: {info['sim_time_s']:.4f} s")
    if info.get("delta_t_s"):
        lines.append(f"Latest step size: {info['delta_t_s']:.3e} s")
    if info.get("t_line"):
        lines.append(info["t_line"])
    if info.get("melt_line"):
        lines.append(info["melt_line"])
    raw = info.get("tail") or ""
    if not lines and not raw:
        return "(no solver log yet)"
    body = "\n".join(lines)
    if raw:
        body = (body + "\n\nRaw log:\n" + raw).strip()
    return body


def describe(case: Path, stage: str, info: dict, end: float | None, nprocs: int, etime: float | None) -> dict:
    sim = info["sim_time_s"]
    percent = None
    if end and sim is not None and end > 0:
        percent = max(0.0, min(100.0, 100.0 * sim / end))
    eta = None
    if stage == "running" and info["rate"] and end is not None and sim is not None and info["rate"] > 0:
        eta = max(0.0, (end - sim) / info["rate"])

    pool = info["pool"]
    where = short_home(str(case))
    if percent is None:
        clock = "not started" if sim is None else fmt_sim(sim)
    else:
        clock = f"{fmt_sim(sim)} of {fmt_sim(end)}  ({percent:.0f}%)"
    wall = "—"
    if info["clock_s"] is not None:
        wall = fmt_dur(info["clock_s"]) + " used"
    elif etime is not None and stage == "running":
        wall = fmt_dur(etime) + " used"
    if stage == "running" and eta is not None:
        eta_txt = f"about {fmt_dur(eta)}  (around {fmt_clock(eta)})"
    elif stage == "running":
        eta_txt = "too early to estimate — check again in a minute"
    elif stage == "finished":
        eta_txt = "done"
    else:
        eta_txt = "—"

    if pool is None:
        pool_txt = "not printed yet"
        temp_txt = "—"
        bead_txt = "—"
    else:
        if pool["L_mm"] <= 0 and pool["Tmax_K"] < 500:
            pool_txt = "no liquid pool yet — the metal is still heating up"
        elif pool["L_mm"] <= 0:
            pool_txt = "no liquid pool yet"
        else:
            pool_txt = f"{fmt_mm(pool['L_mm'])} long, {fmt_mm(pool['W_mm'])} wide, {fmt_mm(pool['D_mm'])} deep"
        temp_txt = f"{pool['Tmax_K']:.0f} K  ({pool['Tmax_K'] - 273.15:.0f} °C)"
        if pool["h_mm"] < 0.01 and pool["w_mm"] < 0.01:
            bead_txt = "nothing deposited at the measurement point yet"
        else:
            bead_txt = f"height {fmt_mm(pool['h_mm'])}, width {fmt_mm(pool['w_mm'])}, penetration {fmt_mm(pool['pen_mm'])}"

    cores = f"{nprocs} cores" if nprocs else "solver is not running"
    saved = newest_saved_time(case)
    saved_txt = ""
    if saved is not None:
        saved_txt = f" The newest 3D snapshot on disk is at {fmt_sim(saved)}."
        if sim is not None and sim - saved > 0.002:
            saved_txt += " The live clock is ahead of that snapshot, so a picture is one save behind."

    dt_txt = ""
    if info["delta_t_s"] and stage == "running":
        dt_txt = (
            f" Each step only moves the simulation forward by {info['delta_t_s']:.2e} s,"
            " so a blank terminal does not mean the job is stuck."
        )

    headlines = {
        "running": "The melt-pool simulation is running.",
        "meshing": "The mesh is being built. The solver has not started.",
        "finished": "This run finished.",
        "stopped": "The solver is not running, and it did not reach the end time.",
        "failed": "The solver stopped because of an error.",
        "ready": "The case is set up, but the solver has not been started.",
        "absent": "No simulation was found for this name.",
    }
    next_steps = {
        "running": "Leave it alone. The window where you started it stays blank on purpose; the log is in a file. Use “Picture of latest save” when you want to see the pool. That does not stop the run.",
        "meshing": "Wait. Meshing usually takes a few minutes, then the solver starts by itself if you used Allrun or Generate+Mesh+Solve.",
        "finished": "Use “Picture of latest save” for one frame, or Visualize for the whole movie. Pictures land in the viz folder.",
        "stopped": "Something stopped the job early (a closed window, Ctrl+C, or the PC sleeping). The last lines below are the clue. Start it again only if you want a new run.",
        "failed": "Read the last lines below. A missing solver shows up as “command not found”; a bad mesh shows up as FOAM FATAL.",
        "ready": "Start it with Run solver in this window, or in WSL with ./Allrun. Status will follow it.",
        "absent": "Either generate a case with the buttons above, or pick a run that already exists from the Watch list.",
    }
    explain = (
        "The simulation clock is how far the melt pool has progressed inside the model. "
        "It is not the time you have been waiting."
        + dt_txt
        + saved_txt
    )
    if stage == "running" and info["log_age_s"] is not None and info["log_age_s"] > 120:
        explain += (
            f" The log file has not changed for {fmt_dur(info['log_age_s'])},"
            " which is unusually long for this solver. It may be stuck."
        )
    if stage == "finished":
        explain = "The solver reached the end of the requested time. Nothing is computing now." + saved_txt
    if stage in ("ready", "absent", "meshing"):
        explain = headlines[stage]

    progress = "No progress yet"
    if percent is not None:
        progress = f"Simulation progress: {fmt_sim(sim)} of {fmt_sim(end)} ({percent:.0f}%)"
    elif stage == "finished":
        progress = "Finished"

    return {
        "dir": str(case),
        "name": case.name,
        "stage": stage,
        "headline": headlines.get(stage, stage),
        "explain": explain,
        "next_step": next_steps.get(stage, ""),
        "percent": percent,
        "progress_caption": progress,
        "multicomp": is_multicomp(case),
        "facts": {
            "where": where,
            "clock": clock,
            "wall": wall,
            "eta": eta_txt,
            "pool": pool_txt,
            "temp": temp_txt,
            "bead": bead_txt,
            "cores": cores,
        },
        "log_tail": readable_tail(info),
    }


def resolve_requested(name: str, cases: list[Path]) -> Path | None:
    if not name:
        return None
    direct = Path(expand(name))
    if direct.is_dir() and (direct / "system" / "controlDict").is_file():
        return direct
    matches = [c for c in cases if c.name == name]
    if not matches:
        return None
    matches.sort(key=log_mtime, reverse=True)
    return matches[0]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", default="")
    ap.add_argument("--workdir", default="~/laser_wire_ded_stranded")
    ap.add_argument("--prefer-running", action="store_true")
    args = ap.parse_args()

    procs = list_procs()
    solvers = [p for p in procs if p["kind"] == "solver"]
    setups = [p for p in procs if p["kind"] == "setup"]
    roots = [args.workdir, "~/lwded_runs", "~/laser_wire_ded_stranded"]
    extras = [p["cwd"] for p in procs]
    cases = discover_cases(roots, extras)

    def norm(path: str | Path) -> str:
        try:
            return str(Path(path).resolve())
        except OSError:
            return str(path)

    def here(group, case: Path) -> list[dict]:
        key = norm(case)
        return [p for p in group if norm(p["cwd"]) == key]

    by_dir = {norm(case): case for case in cases}
    requested = resolve_requested(args.case, cases)
    focus = requested
    switched = ""
    switch_reason = ""
    running_cases = []
    for proc in solvers:
        path = by_dir.get(norm(proc["cwd"]))
        if path is None and Path(proc["cwd"], "system", "controlDict").is_file():
            path = Path(proc["cwd"])
            by_dir[norm(path)] = path
        if path is not None and all(norm(path) != norm(old) for old in running_cases):
            running_cases.append(path)

    if args.prefer_running and running_cases:
        running_cases.sort(key=log_mtime, reverse=True)
        focus = running_cases[0]
        if requested is None or norm(focus) != norm(requested):
            switched = args.case or (requested.name if requested else "the name in the form")
            switch_reason = "running"
    elif focus is None or not (focus / "system" / "controlDict").is_file():
        with_logs = [c for c in cases if (c / "log.laserWireDEDFoam").is_file()]
        with_logs.sort(key=log_mtime, reverse=True)
        if with_logs:
            focus = with_logs[0]
            switched = args.case or "the name in the form"
            switch_reason = "recent"

    catalog = []
    for case in sorted(cases, key=log_mtime, reverse=True)[:16]:
        info = parse_log(case) if (case / "log.laserWireDEDFoam").is_file() else {
            "has_log": False, "log_age_s": None, "sim_time_s": None, "clock_s": None,
            "delta_t_s": None, "rate": None, "pool": None, "fatal": False,
            "ended_clean": False, "tail": "",
        }
        # Cheap classify without re-reading when this isn't the focus: still need stage for the menu.
        stage = classify(case, here(solvers, case), here(setups, case), info, end_time(case))
        catalog.append({"dir": str(case), "name": case.name, "stage": stage, "label": f"{case.name}  —  {stage}  —  {short_home(str(case.parent))}"})

    if focus is None:
        payload = {
            "ok": True,
            "switched_from": args.case,
            "focus": {
                "dir": "",
                "name": args.case or "(none)",
                "stage": "absent",
                "headline": "No simulation was found.",
                "explain": "Nothing is running, and there is no case folder to read. Generate a case, or start one in WSL.",
                "next_step": "Use Generate case, then Run solver. A run started from a terminal in ~/lwded_runs will show up here on the next refresh.",
                "percent": None,
                "progress_caption": "No run",
                "multicomp": False,
                "facts": {
                    "where": "—",
                    "clock": "—",
                    "wall": "—",
                    "eta": "—",
                    "pool": "—",
                    "temp": "—",
                    "bead": "—",
                    "cores": "solver is not running",
                },
                "log_tail": "",
            },
            "cases": catalog,
            "banner": "",
        }
        print(json.dumps(payload))
        return 0

    info = parse_log(focus)
    sol = here(solvers, focus)
    stp = here(setups, focus)
    end = end_time(focus)
    stage = classify(focus, sol, stp, info, end)
    nprocs = len(sol)
    etime = max((p["etime_s"] or 0 for p in sol), default=None) if sol else None
    described = describe(focus, stage, info, end, nprocs, etime)
    banner = ""
    if switched and switch_reason == "running":
        banner = (
            f"Showing {described['name']} because that simulation is running right now. "
            f"The name in the form ({switched}) is a different case. "
            "Use Watch to look at another run, or “Watch the case named above” to follow the form."
        )
    elif switched:
        banner = (
            f"Nothing is running. Showing {described['name']} because it is the most recent run on this PC. "
            f"The name in the form ({switched}) does not have a solver log. "
            "Use Watch to pick a different case."
        )
    elif running_cases and all(norm(c) != norm(focus) for c in running_cases):
        other = running_cases[0]
        banner = (
            f"This case is not the one computing. {other.name} in {short_home(str(other))} is running right now."
        )
    described_banner = banner
    payload = {
        "ok": True,
        "switched_from": switched,
        "banner": described_banner,
        "focus": described,
        "cases": catalog,
    }
    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        raise SystemExit(1)
