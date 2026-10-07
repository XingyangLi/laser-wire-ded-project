#!/usr/bin/env python3
"""Generate the wire-substrate gap case study (gap_study_<n>mm) from the val3mm_fe_ni_v2 baseline.

Every generator option is taken from the baseline case_params.json (so the cases are exactly
val3mm_fe_ni_v2), then only the initial wire gap, the stubbing model and the write interval change.

    python3 scripts/pc/gap_study_generate.py                       # 1, 2, 3 mm into ~/laser_wire_ded_stranded
    python3 scripts/pc/gap_study_generate.py --gaps 1.5 --root /tmp/x --no-repo-copy
    python3 scripts/pc/gap_study_generate.py --verify-baseline     # regenerate v2 (gap 0, no stubbing) and diff

Setup files (no mesh / results) are copied to <repo>/cases/gap_study_<n>mm.
"""
import argparse
import difflib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
import generate_case as G  # noqa: E402

# case_params keys that are derived / informational (not generator inputs)
SKIP = {"case", "print", "material", "wire_material", "wire_diameter", "strands", "lay_length",
        "feed_reference_diameter", "record_interval", "wire_feed_speed", "strand_materials"}


def baseline_argv(prm, parser):
    argv = []
    for act in parser._actions:
        d = act.dest
        if d in SKIP or d == "help" or d not in prm or not act.option_strings:
            continue
        v = prm[d]
        opt = act.option_strings[0]
        if act.nargs == 0:                      # store_true flags
            if v:
                argv.append(opt)
            continue
        if v is None:
            continue
        argv.append(f"{opt}={v}")
    st = prm.get("strands")
    argv.append(f"--strands={st['n_strands'] if isinstance(st, dict) else st}")
    argv.append(f"--wire-feed-speed={prm['wire_feed_speed_nominal']}")   # nominal; metal basis -> 18.2 mm/s
    if prm.get("strand_materials"):
        argv.append("--strand-materials=" + ",".join(prm["strand_materials"]))
    return argv


def copy_setup(src: Path, dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for name in ("0.orig", "system", "constant"):
        shutil.copytree(src / name, dst / name, ignore=shutil.ignore_patterns("polyMesh"))
    for name in ("Allrun", "Allclean", "case.foam", "case_params.json", "FIXES.md"):
        if (src / name).exists():
            shutil.copy2(src / name, dst / name)


def fixes_md(n, prm, gg):
    b = gg["beams"][0] if gg.get("beams") else {}
    return f"""# gap_study_{n}mm: initial wire-substrate gap {n} mm (val3mm_fe_ni_v2 + gap + stubbing)

Everything as `cases/val3mm_fe_ni_v2` (600 W, 160 mm/min, WFS 18.2 mm/s metal basis, Fe/Ni 5-strand ring
wire on Invar, focus -1.5 mm, zR 1.2 mm, A 0.25/0.35, rigid substrate x100, stub floor, 3 mm track,
end 1.1249 s, 120/60 um mesh) except:

| item | value |
|---|---|
| `--wire-gap` | {gg['wire_gap_m']*1e3:.2f} mm: lowest point of the (flat-cut) wire tip at z = {gg['wire_tip_lowest_z_m']*1e3:.2f} mm above the plate top at t = 0 |
| feed | starts at t = 0 at {prm['wire_feed_speed']*1e3:.2f} mm/s along the (vertical) wire axis; an unmelted tip would reach the plate at t ~ {gg['time_to_close_gap_if_unmelted_s']*1e3:.0f} ms |
| `--stubbing` | ON: rigid-wire stall while solid unmelted wire rests on solid support, `postProcessing/wireTransfer/wireTransfer.dat` |
| gas layer | {gg['gas_height_m']*1e3:.2f} mm (uniform 120 um cells up to {gg['gas_uniform_height_m']*1e3:.2f} mm) |
| cells | {prm['cells']} ({prm['cells_xyz'][0]} x {prm['cells_xyz'][1]} x ({prm['cells_xyz'][2]}+{prm['cells_xyz'][3]}) block, wire box refined) |
| `--write-interval` | {prm['write_interval']} s (v2: 0.02 s) to see the early transfer |
| beams vs tip | coaxial: the wire axis is the axis of the 3-beam cone (focus 1.5 mm below the plate on that axis). At the tip height each beam axis is {b.get('axis_offset_at_tip_m', 0)*1e3:.2f} mm from the wire axis ({b.get('axis_to_wire_surface_at_tip_in_w', 0):.2f} beam radii w = {b.get('model_radius_m', 0)*1e3:.2f} mm from the wire surface, relative intensity {b.get('rel_intensity_at_wire_surface_at_tip', 0):.3f}); at the plate {b.get('axis_offset_at_plate_m', 0)*1e3:.2f} mm |

See `cases/gap_study/README.md` for what is measured and how to compare the three cases.
"""


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gaps", default="1,2,3", help="gaps in mm (comma list)")
    ap.add_argument("--baseline", default=str(REPO / "cases" / "val3mm_fe_ni_v2" / "case_params.json"))
    ap.add_argument("--root", default=os.path.expanduser("~/laser_wire_ded_stranded"),
                    help="run directory root (WSL); cases go to <root>/gap_study_<n>mm")
    ap.add_argument("--prefix", default="gap_study_")
    ap.add_argument("--no-stubbing", action="store_true")
    ap.add_argument("--write-interval", type=float, default=0.01)
    ap.add_argument("--np", type=int, default=None)
    ap.add_argument("--no-repo-copy", action="store_true")
    ap.add_argument("--verify-baseline", action="store_true",
                    help="regenerate the baseline (gap 0, no stubbing) into a temp dir and diff against the repo copy")
    ap.add_argument("extra", nargs="*", help="extra generate_case.py options (after --)")
    a = ap.parse_args()

    prm = json.load(open(a.baseline))
    base = baseline_argv(prm, G.build_parser())

    if a.verify_baseline:
        tmp = Path(tempfile.mkdtemp()) / "v2"
        G.main(base + [f"--case={tmp}"])
        ref = Path(a.baseline).parent
        ndiff = 0
        for f in sorted(p for p in tmp.rglob("*") if p.is_file()):
            rel = f.relative_to(tmp)
            r = ref / rel
            if rel.name == "case_params.json" or not r.exists():
                continue
            A, B = r.read_text().splitlines(), f.read_text().splitlines()
            d = [l for l in difflib.unified_diff(A, B, str(r), str(f), n=0, lineterm="")
                 if l.startswith(("+", "-")) and not l.startswith(("+++", "---"))]
            if d:
                ndiff += 1
                print(f"--- {rel}:"); print("\n".join(d[:12]))
        print(f"[verify] {ndiff} file(s) differ from {ref}")
        return 0

    for g in [float(x) for x in a.gaps.split(",") if x.strip()]:
        n = f"{g:g}"
        case = Path(a.root) / f"{a.prefix}{n}mm"
        argv = base + [f"--case={case}", f"--wire-gap={g*1e-3}", f"--write-interval={a.write_interval}"]
        if not a.no_stubbing:
            argv.append("--stubbing")
        if a.np:
            argv.append(f"--np={a.np}")
        argv += a.extra
        print(f"\n=== {case.name}: gap {g} mm")
        G.main(argv)
        cp = json.load(open(case / "case_params.json"))
        (case / "FIXES.md").write_text(fixes_md(n, cp, cp["gap_geometry"]), newline="\n") \
            if sys.version_info >= (3, 10) else open(case / "FIXES.md", "w", newline="\n").write(
                fixes_md(n, cp, cp["gap_geometry"]))
        if not a.no_repo_copy:
            dst = REPO / "cases" / case.name
            copy_setup(case, dst)
            print(f"[gap_study] setup copied to {dst}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
