#!/usr/bin/env python3
"""Local model-setup studio for laser wire DED.

Opens a browser page that edits process parameters and draws the domain, wire,
and laser beams from the same geometry generate_case.py will write. The solver
is unchanged: Run still launches laserWireDEDFoam in WSL.

    python studio_server.py
"""
from __future__ import annotations

import io
import json
import math
import re
import shlex
import sys
import threading
import traceback
import webbrowser
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

ROOT = Path(__file__).resolve().parents[1]
GUI = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(GUI))

import generate_case as gc  # noqa: E402
from app import Backend, DEFAULT_WSL_DISTRO, DEFAULT_WSL_OF_BASHRC, DEFAULT_WSL_WORKDIR, PROTECTED_CASE_RE  # noqa: E402

STATIC = GUI / "studio"
PORT = 8765
PROTECTED = re.compile(r"^(full_transitional_r|val3mm_fe_ni_v2$|results_keep)", re.I)

STRAND_COLORS = {
    "Fe": "#c45c26",
    "Ni": "#d5dbe3",
    "Invar36": "#c4a46a",
    "SS304": "#9aa7b5",
    "316L": "#8fa4b8",
    "IN718": "#b7a48a",
    "Ti6Al4V": "#7f93a8",
}


def mm(x):
    return None if x is None else float(x) * 1e3


def opt_float(model, key):
    v = model.get(key)
    if v is None or v == "":
        return None
    return float(v)


def argv_from_model(m: dict) -> list[str]:
    """Engineering-unit form state -> generate_case.py argv (SI)."""
    case = str(m.get("case") or "studio_case").strip()
    a = ["--case", case, "--np", str(int(m.get("np") or 8))]
    a += ["--laser-config", str(m.get("laser_config") or "single")]
    a += ["--wire-type", str(m.get("wire_type") or "solid")]
    a += ["--resolution", str(m.get("resolution") or "medium")]
    a += ["--dim", str(m.get("dim") or "3d")]
    a += ["--domain-y", str(m.get("domain_y") or "auto")]
    a += ["--write-interval", str(float(m.get("write_interval_s") or 0.01))]
    a += ["--max-co", str(float(m.get("max_co") if m.get("max_co") not in (None, "") else 0.4))]
    a += ["--capillary-dt-factor", str(float(m.get("capillary_dt_factor") if m.get("capillary_dt_factor") not in (None, "") else 0.8))]
    a += ["--feed-start", str(float(m.get("feed_start_s") if m.get("feed_start_s") not in (None, "") else 0.02))]
    a += ["--beam-angle", str(float(m.get("beam_angle_deg") or 25))]
    a += ["--focus-height", str(float(m.get("focus_mm") if m.get("focus_mm") not in (None, "") else 0.5) * 1e-3)]
    a += ["--beam-radius", str(float(m.get("beam_radius_mm") or 0.5) * 1e-3)]
    a += ["--spot-radius", str(float(m.get("spot_radius_mm") or 1.2) * 1e-3)]
    a += ["--profile", str(m.get("profile") or "gaussian")]
    a += ["--alpha-hit", str(float(m.get("alpha_hit") if m.get("alpha_hit") not in (None, "") else 0.5))]
    a += ["--strand-k-factor", str(float(m.get("strand_k_factor") if m.get("strand_k_factor") not in (None, "") else 1))]
    a += ["--unmelted-k-factor", str(float(m.get("unmelted_k_factor") if m.get("unmelted_k_factor") not in (None, "") else 1))]
    a += ["--preheat", str(float(m.get("preheat_k") or 300))]
    a += ["--gas-viscosity-factor", str(float(m.get("gas_viscosity_factor") or 20))]
    a += ["--mushy-C", str(float(m.get("mushy_C") or 1e8))]
    a += ["--max-wfs", str(float(m.get("max_wfs_mm_s") or 100) * 1e-3)]
    a += ["--feed-scale", str(float(m.get("feed_scale") if m.get("feed_scale") not in (None, "") else 1))]
    a += ["--liquidus", str(m.get("liquidus") or "table")]
    a += ["--wire-aim", str(float(m.get("wire_aim_mm") or 0) * 1e-3)]
    a += ["--feed-side", str(m.get("feed_side") or "front")]
    if m.get("beam_direction"):
        a += ["--beam-direction", str(m["beam_direction"])]
    if m.get("power_w") not in (None, ""):
        a += ["--power", str(float(m["power_w"]))]
    if m.get("scan_mm_s") not in (None, ""):
        a += ["--scan-speed", str(float(m["scan_mm_s"]) * 1e-3)]
    if m.get("wfs_mm_s") not in (None, ""):
        a += ["--wire-feed-speed", str(float(m["wfs_mm_s"]) * 1e-3)]
    if m.get("wire_diameter_mm") not in (None, ""):
        a += ["--wire-diameter", str(float(m["wire_diameter_mm"]) * 1e-3)]
    if m.get("feed_angle_deg") not in (None, ""):
        a += ["--feed-angle", str(float(m["feed_angle_deg"]))]
    if m.get("wire_gap_mm") not in (None, ""):
        a += ["--wire-gap", str(float(m["wire_gap_mm"]) * 1e-3)]
    if m.get("track_length_mm") not in (None, ""):
        a += ["--track-length", str(float(m["track_length_mm"]) * 1e-3)]
    if m.get("end_time_s") not in (None, ""):
        a += ["--end-time", str(float(m["end_time_s"]))]
    if m.get("dx_um") not in (None, ""):
        a += ["--dx", str(float(m["dx_um"]) * 1e-6)]
    if m.get("rayleigh_mm") not in (None, ""):
        a += ["--rayleigh-length", str(float(m["rayleigh_mm"]) * 1e-3)]
    if m.get("absorptivity") not in (None, ""):
        a += ["--absorptivity", str(float(m["absorptivity"]))]
    if m.get("absorptivity_substrate") not in (None, ""):
        a += ["--absorptivity-substrate", str(float(m["absorptivity_substrate"]))]
    if m.get("absorptivity_wire") not in (None, ""):
        a += ["--absorptivity-wire", str(float(m["absorptivity_wire"]))]
    if m.get("wire_material"):
        a += ["--wire-material", str(m["wire_material"])]
    if m.get("substrate_material"):
        a += ["--substrate-material", str(m["substrate_material"])]
    if m.get("material"):
        a += ["--material", str(m["material"])]
    if str(m.get("wire_type")) == "stranded":
        a += ["--strands", str(int(m.get("strands") or 7))]
        a += ["--strand-layout", str(m.get("strand_layout") or "auto")]
        a += ["--strand-gap", str(float(m.get("strand_gap_mm") if m.get("strand_gap_mm") not in (None, "") else 0.04) * 1e-3)]
        a += ["--lay-direction", str(m.get("lay_direction") or "right")]
        a += ["--strand-feed-basis", str(m.get("strand_feed_basis") or "metal")]
        if m.get("strand_diameter_mm") not in (None, ""):
            a += ["--strand-diameter", str(float(m["strand_diameter_mm"]) * 1e-3)]
        if m.get("lay_length_mm") not in (None, ""):
            a += ["--lay-length", str(float(m["lay_length_mm"]) * 1e-3)]
        mats = str(m.get("strand_materials") or "").strip()
        if mats:
            a += ["--strand-materials", mats]
    if m.get("wire_refine") not in (None, ""):
        a += ["--wire-refine", str(int(m["wire_refine"]))]
    if m.get("upstream_mm") not in (None, ""):
        a += ["--upstream", str(float(m["upstream_mm"]) * 1e-3)]
    if m.get("downstream_mm") not in (None, ""):
        a += ["--downstream", str(float(m["downstream_mm"]) * 1e-3)]
    if m.get("half_width_mm") not in (None, ""):
        a += ["--half-width", str(float(m["half_width_mm"]) * 1e-3)]
    if m.get("substrate_mm") not in (None, ""):
        a += ["--substrate-thickness", str(float(m["substrate_mm"]) * 1e-3)]
    if m.get("gas_height_mm") not in (None, ""):
        a += ["--gas-height", str(float(m["gas_height_mm"]) * 1e-3)]
    if m.get("liquidus_unmixed") not in (None, ""):
        a += ["--liquidus-unmixed-threshold", str(float(m["liquidus_unmixed"]))]
    if m.get("laser_ramp_ms") not in (None, ""):
        a += ["--laser-ramp", str(float(m["laser_ramp_ms"]) * 1e-3)]
    for flag, key in (
        ("--no-marangoni", "no_marangoni"),
        ("--no-recoil", "no_recoil"),
        ("--no-evaporation", "no_evaporation"),
        ("--no-radiation", "no_radiation"),
        ("--no-convection", "no_convection"),
        ("--buoyancy", "buoyancy"),
        ("--no-shadowing", "no_shadowing"),
        ("--no-wire-stubbing", "no_wire_stubbing"),
        ("--no-melted-follow-substrate", "no_melted_follow_substrate"),
    ):
        if m.get(key):
            a.append(flag)
    return a


def _axis(c, s):
    o, u = c.origin, c.up
    return (o[0] + s * u[0], o[1] + s * u[1], o[2] + s * u[2])


def _pt(p):
    return [mm(p[0]), mm(p[1]), mm(p[2])]


def build_scene(m: dict) -> dict:
    argv = argv_from_model(m)
    notes = io.StringIO()
    try:
        args = gc.build_parser().parse_args(argv)
        with redirect_stdout(notes):
            case = gc.Case(args)
    except SystemExit as exc:
        msg = exc.code if isinstance(exc.code, str) else "The generator rejected these settings."
        return {"ok": False, "error": str(msg), "notes": notes.getvalue()}
    a = case.a
    th = case.th
    s_top = case.zt / math.sin(th)
    s_tip = (a.wire_gap + case.R * math.cos(th)) / math.sin(th)
    nseg = 36
    strands_draw = []
    section = []
    if case.strands:
        st = case.strands
        e1, e2, _u = case.wire_basis()
        hand = 1.0 if a.lay_direction == "right" else -1.0
        k = hand * 2 * math.pi / st["lay_length"]
        mats = getattr(a, "strand_material_list", None) or ["wire"] * st["n_strands"]
        centers = []
        if st["centre_strand"]:
            centers.append((0.0, 0.0, 0))
        for i in range(st["n_ring"]):
            ang = 2 * math.pi * i / st["n_ring"]
            centers.append((st["ring_radius"], ang, (1 if st["centre_strand"] else 0) + i))
        for Rc_or_0, ang, idx in centers:
            mat = mats[idx] if idx < len(mats) else "wire"
            color = STRAND_COLORS.get(mat, "#d08a45")
            line = []
            for i in range(nseg + 1):
                s = s_tip + (s_top - s_tip) * i / nseg
                base = _axis(case, s)
                if Rc_or_0 == 0.0 and ang == 0.0 and st["centre_strand"] and idx == 0:
                    off = (0.0, 0.0, 0.0)
                else:
                    ph = k * s + ang
                    off = tuple(e1[j] * Rc_or_0 * math.cos(ph) + e2[j] * Rc_or_0 * math.sin(ph) for j in range(3))
                p = tuple(base[j] + off[j] for j in range(3))
                line.append(_pt(p))
            strands_draw.append({"name": mat, "color": color, "radius": mm(st["strand_radius"]), "line": line})
            ph0 = k * s_tip + (ang if not (Rc_or_0 == 0 and idx == 0) else 0)
            if Rc_or_0 == 0 and idx == 0 and st["centre_strand"]:
                sx, sy = 0.0, 0.0
            else:
                sx = mm(Rc_or_0 * math.cos(ph0))
                sy = mm(Rc_or_0 * math.sin(ph0))
            section.append({"name": mat, "color": color, "x": sx, "y": sy, "r": mm(st["strand_radius"])})
        wire_r = mm(st["strand_radius"])
        envelope = mm(a.wire_diameter / 2)
    else:
        line = [_pt(_axis(case, s_tip + (s_top - s_tip) * i / nseg)) for i in range(nseg + 1)]
        strands_draw.append({"name": a.wire_material, "color": "#d08a45", "radius": mm(case.R), "line": line})
        section.append({"name": a.wire_material, "color": "#d08a45", "x": 0, "y": 0, "r": mm(case.R)})
        wire_r = mm(case.R)
        envelope = wire_r

    beams = []
    for name, power, F, d, radius, _pr in case.beams():
        dz = d[2] if abs(d[2]) > 1e-6 else -1.0
        # Draw from just above the gas top, through the focus, down to the plate.
        z_hi = case.zt + 0.4e-3
        t_hi = (z_hi - F[2]) / dz
        t_plate = (0.0 - F[2]) / dz
        stations = []
        zR = a.rayleigh_length
        for t in (t_hi, t_hi * 0.65, t_hi * 0.35, 0.0, t_plate):
            center = tuple(F[i] + t * d[i] for i in range(3))
            along = abs(t)
            if zR and zR > 0:
                w = radius * math.sqrt(1.0 + (along / zR) ** 2)
            else:
                w = radius
            stations.append({"c": _pt(center), "r": mm(w)})
        w_plate, _ = case.spot_size_at_z(0.0)
        beams.append({
            "name": name,
            "power": power,
            "focus": _pt(F),
            "direction": list(d),
            "radius": mm(radius),
            "spot_plate": mm(w_plate),
            "stations": stations,
        })

    y0 = 0.0 if not case.full else -case.y1
    hw = a.refine_halfwidth
    hwy = a.refine_halfwidth_y or hw
    refine = None
    if a.wire_refine and a.wire_refine > 0:
        refine = {
            "x0": mm(case.origin[0] - hw),
            "x1": mm(case.origin[0] + hw + (a.refine_downstream or 0)),
            "y0": 0.0 if not case.full else mm(-hwy),
            "y1": mm(hwy if case.full else hwy),
            "levels": a.wire_refine,
        }
        if not case.full:
            refine["y0"] = 0.0
            refine["y1"] = mm(hwy)

    if case.coax:
        w_plate, _ = case.spot_size_at_z(0.0)
        w_1, _ = case.spot_size_at_z(1e-3)
    else:
        w_plate = w_1 = a.spot_radius
    dt = case.summary().get("capillary_dt_limit")
    steps = int(a.end_time / dt) if dt else None
    spot_d = 2 * w_plate
    wire_label = "+".join(case.comp_names) if case.comp_names else a.wire_material
    one = (
        f"{a.laser_config.replace('_', ' ')}, {a.power:.0f} W, "
        f"{wire_label} wire on {a.substrate_material}, "
        f"{'stranded' if case.strands else 'solid'} {a.wire_diameter*1e3:.2f} mm"
    )
    return {
        "ok": True,
        "notes": notes.getvalue().strip(),
        "one_line": one,
        "domain": {
            "x0": mm(case.x0), "x1": mm(case.x1),
            "y0": mm(y0), "y1": mm(case.y1),
            "z0": mm(case.zb), "z1": mm(case.zt),
            "half": not case.full,
        },
        "origin": _pt(case.origin),
        "wire_tip": _pt(_axis(case, s_tip)),
        "wire_top": _pt(_axis(case, s_top)),
        "wire_radius": wire_r,
        "envelope_radius": envelope,
        "strands": strands_draw,
        "section": section,
        "beams": beams,
        "refine": refine,
        "dx": mm(case.dx),
        "dx_min": mm(case.dx_min),
        "derived": {
            "cells": case.ncells,
            "cells_block": case.ncells_block,
            "dx_um": case.dx * 1e6,
            "dx_min_um": case.dx_min * 1e6,
            "end_s": a.end_time,
            "track_mm": a.scan_speed * a.end_time * 1e3,
            "bead_mm2": case.bead_area * 1e6,
            "wfs_mm_s": a.wire_feed_speed * 1e3,
            "wfs_nominal_mm_s": a.wire_feed_speed_nominal * 1e3,
            "scan_mm_s": a.scan_speed * 1e3,
            "power_w": a.power,
            "spot_plate_mm": spot_d * 1e3,
            "spot_1mm_mm": 2 * w_1 * 1e3,
            "focus_mm": a.focus_height * 1e3,
            "wire_mm": a.wire_diameter * 1e3,
            "gap_mm": a.wire_gap * 1e3,
            "feed_deg": a.feed_angle,
            "n_beams": len(beams),
            "capillary_dt_s": dt,
            "steps": steps,
            "max_co": a.max_co,
            "write_s": a.write_interval,
            "cap_factor": a.capillary_dt_factor,
            "wire_material": a.wire_material,
            "substrate_material": a.substrate_material,
            "energy_j_per_mm": a.power / (a.scan_speed * 1e3),
            "half": not case.full,
            "fill": None if not case.strands else case.strands["fill_factor"],
            "strand_mm": None if not case.strands else case.strands["strand_diameter"] * 1e3,
            "n_strands": None if not case.strands else case.strands["n_strands"],
        },
    }


class Job:
    def __init__(self, argv, case, np, strand_materials):
        self._argv = argv
        self.case = case
        self.np = int(np)
        self.strand_materials = strand_materials or ""

    def to_argv(self):
        return list(self._argv)


def backend() -> Backend:
    return Backend(ROOT, DEFAULT_WSL_DISTRO, DEFAULT_WSL_WORKDIR, DEFAULT_WSL_OF_BASHRC)


def guard_case(name: str):
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_\-]*$", name or ""):
        raise RuntimeError("Case name: letters, digits, _ and - only.")
    if PROTECTED.search(name) or PROTECTED_CASE_RE.search(name):
        raise RuntimeError(
            f"'{name}' is a protected or already-running production case. Pick a new name."
        )


def launch(model: dict, steps: str) -> str:
    from app import expand_user_wsl
    name = str(model.get("case") or "").strip()
    guard_case(name)
    argv = argv_from_model(model)
    job = Job(argv, name, int(model.get("np") or 8), str(model.get("strand_materials") or ""))
    be = backend()
    be.sync_project_to_wsl()
    if steps == "generate":
        args = " ".join(shlex.quote(x) for x in argv)
        wd = expand_user_wsl(be.wsl_workdir)
        cmd = f"cd {shlex.quote(wd)} && python3 generate_case.py {args} && echo GENERATED_OK"
        return be.run_wsl(cmd, check=True, timeout=120)
    script = be.make_pipeline_script(job, "generate_mesh" if steps == "mesh" else ("all" if steps == "all" else "solve"))
    log_path = GUI / "jobs" / f"{name}.out"
    be.launch_detached(script, log_path)
    return f"Started {steps} for {name}.\nLog: {log_path}"


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        sys.stderr.write("%s - %s\n" % (self.address_string(), fmt % args))

    def _send(self, code, body, content="application/json"):
        data = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _read_json(self):
        n = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(n) if n else b"{}"
        return json.loads(raw.decode("utf-8") or "{}")

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/status":
            qs = parse_qs(url.query)
            case = (qs.get("case") or [""])[0]
            try:
                data = backend().probe_status(case, True)
            except Exception as exc:
                data = {"ok": False, "error": str(exc)}
            self._send(200, json.dumps(data))
            return
        if url.path == "/api/materials":
            names = sorted(gc.MATERIALS)
            brief = {
                n: {
                    "Tsol": gc.MATERIALS[n]["Tsol"],
                    "Tliq": gc.MATERIALS[n]["Tliq"],
                    "absorptivity": gc.MATERIALS[n]["absorptivity"],
                }
                for n in names
            }
            self._send(200, json.dumps({"names": names, "brief": brief}))
            return
        path = url.path
        if path in ("/", ""):
            path = "/index.html"
        file = (STATIC / path.lstrip("/")).resolve()
        if not str(file).startswith(str(STATIC.resolve())) or not file.is_file():
            self._send(404, "not found", "text/plain")
            return
        kind = {
            ".html": "text/html; charset=utf-8",
            ".css": "text/css; charset=utf-8",
            ".js": "text/javascript; charset=utf-8",
        }.get(file.suffix, "application/octet-stream")
        self._send(200, file.read_bytes(), kind)

    def do_POST(self):
        url = urlparse(self.path)
        try:
            model = self._read_json()
            if url.path == "/api/preview":
                self._send(200, json.dumps(build_scene(model)))
                return
            if url.path == "/api/launch":
                steps = str(model.get("steps") or "generate")
                if steps not in ("generate", "mesh", "solve", "all"):
                    raise RuntimeError("Unknown action.")
                text = launch(model.get("model") or model, steps)
                self._send(200, json.dumps({"ok": True, "text": text}))
                return
            self._send(404, json.dumps({"ok": False, "error": "unknown path"}))
        except Exception as exc:
            self._send(200, json.dumps({"ok": False, "error": str(exc), "trace": traceback.format_exc()[-800:]}))


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-browser", action="store_true")
    flags, _ = ap.parse_known_args()
    try:
        server = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    except OSError as exc:
        print(f"Port {PORT} is already in use ({exc}). Close the other studio window and try again.")
        raise SystemExit(1)
    url = f"http://127.0.0.1:{PORT}"
    print(f"Model studio: {url}", flush=True)
    print("Leave this window open. Closing it closes the studio. The solver keeps running.", flush=True)
    if not flags.no_browser:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStudio closed.")


if __name__ == "__main__":
    main()
