#!/usr/bin/env python3
"""Compare wire-cavity runs at several oxygen levels.

    python3 scripts/compare_oxygen_sweep.py
    python3 scripts/compare_oxygen_sweep.py --cases cases/wire_cavity_ox10 cases/wire_cavity_ox1000
    python3 scripts/compare_oxygen_sweep.py --print-model

Reads, from each case:

    postProcessing/wireCavity/wireCavity.dat   cavity volume and open/closed status
    postProcessing/porosity/porosity.dat       nEntrapment (bubble count)
    postProcessing/wireCavity/events.dat       pinch-off and closure events
    postProcessing/oxygen/sigma.dat            sigma(T, a_O) samples
    constant/meltProperties                    chamberOxygenPpm

Writes a CSV and, if matplotlib is installed, a PNG with cavity volume and
bubble count against time. Bubble count is the existing entrapment counter.
"""
from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

# Fe-O adsorption (Sahoo, DebRoy, McNallan, Metall. Trans. B 19B (1988) 483)
# on the 316L linear law used by this case (sigma_m = 1.75 N/m at 1723 K,
# A = 4.3e-4 N/m/K). a_O [wt%] = ppm * 1e-4.
R = 8.314462618
GAMMA = 2.03e-5
K1 = 0.0138
DH = -1.463e5
A_CLEAN = 4.3e-4
SIGMA_M = 1.75
T_M = 1723.0
SIGMA_MIN = 0.3 * SIGMA_M


def sahoo(T: float, ppm: float, sig_m: float = SIGMA_M, Acoef: float = A_CLEAN, Tm: float = T_M):
    """Return (sigma [N/m], dsigma/dT [N/m/K]) at temperature T."""
    activity = ppm * 1.0e-4
    Te = max(T, Tm, 300.0)
    K = K1 * math.exp(-DH / (R * Te))
    Ka = K * activity
    ln_term = math.log(1.0 + Ka)
    sig_raw = sig_m - Acoef * (Te - Tm) - R * Te * GAMMA * ln_term
    sig = max(sig_raw, SIGMA_MIN)
    coverage = Ka / (1.0 + Ka)
    dsdT = -Acoef - R * GAMMA * ln_term - GAMMA * coverage * (DH / Te)
    if T < Tm or sig_raw <= SIGMA_MIN:
        dsdT = 0.0
    return sig, dsdT


def print_model() -> None:
    print("Sahoo-Belton reference at the 316L liquidus anchor (not a solver run)")
    print(f"  sigma_m={SIGMA_M} N/m  A={A_CLEAN} N/m/K  Tm={T_M} K")
    print(f"  Gamma_s={GAMMA} mol/m^2  k1={K1}  dH0={DH} J/mol  R={R}")
    print(f"  {'ppm':>8} {'T':>8} {'sigma':>12} {'dsigma/dT':>14}")
    for ppm in (0, 10, 100, 500, 1000):
        for T in (T_M, T_M + 200.0, 2200.0):
            sig, dsdT = sahoo(T, ppm)
            print(f"  {ppm:8.0f} {T:8.0f} {sig:12.6f} {dsdT:14.6e}")


def _rows(path: Path):
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.append(line.split())
    return out


def _ppm_from_case(case: Path) -> str:
    sig = _rows(case / "postProcessing" / "oxygen" / "sigma.dat")
    if sig and len(sig[0]) >= 2:
        return sig[0][1]
    props = case / "constant" / "meltProperties"
    if props.is_file():
        for line in props.read_text(errors="replace").splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[0] == "chamberOxygenPpm":
                return parts[1].rstrip(";")
    name = case.name
    if "_ox" in name:
        return name.split("_ox", 1)[1]
    return name


def _series(case: Path):
    cav = _rows(case / "postProcessing" / "wireCavity" / "wireCavity.dat")
    por = _rows(case / "postProcessing" / "porosity" / "porosity.dat")
    events = _rows(case / "postProcessing" / "wireCavity" / "events.dat")
    # wireCavity: time status ... cavityVolume is column 4
    vol = [(float(r[0]), float(r[4]), int(float(r[1]))) for r in cav if len(r) >= 5]
    # porosity: time nPores nLocked nEntrapment is column 3
    bubbles = [(float(r[0]), float(r[3])) for r in por if len(r) >= 4]
    return vol, bubbles, events


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cases", nargs="*", default=None,
                    help="case directories (default: cases/wire_cavity_ox* and smoke_ox*)")
    ap.add_argument("--out", default="results/oxygen_sweep", help="directory for the CSV and PNG")
    ap.add_argument("--print-model", action="store_true",
                    help="print the reference sigma(T, a_O) table and exit")
    a = ap.parse_args(argv)
    if a.print_model:
        print_model()
        return 0

    root = Path(__file__).resolve().parents[1]
    if a.cases:
        cases = [Path(c) if Path(c).is_absolute() else root / c for c in a.cases]
    else:
        base = root / "cases"
        cases = sorted(base.glob("wire_cavity_ox*")) + sorted(base.glob("wire_cavity_smoke_ox*"))
    cases = [c for c in cases if c.is_dir()]
    if not cases:
        print("no oxygen cases found. Pass --cases, or run scripts/sweep_wire_cavity_oxygen.sh")
        return 1

    out = Path(a.out)
    if not out.is_absolute():
        out = root / out
    out.mkdir(parents=True, exist_ok=True)

    summary_path = out / "summary.csv"
    series = []
    with summary_path.open("w", newline="\n") as fh:
        fh.write("case,ppm,nSamples,tLast_s,cavityVolumeLast_m3,statusLast,"
                 "bubbleCountLast,nPinchoff,nClosure,sigmaLiqMeanLast\n")
        for case in cases:
            ppm = _ppm_from_case(case)
            vol, bubbles, events = _series(case)
            sig = _rows(case / "postProcessing" / "oxygen" / "sigma.dat")
            status = {0: "none", 1: "open", 2: "closed", 3: "mixed"}
            if vol:
                t_last, v_last, st = vol[-1]
                st_name = status.get(st, str(st))
            else:
                t_last, v_last, st_name = float("nan"), float("nan"), ""
            b_last = bubbles[-1][1] if bubbles else float("nan")
            n_pinch = sum(1 for r in events if len(r) >= 2 and r[1] == "pinchoff")
            n_close = sum(1 for r in events if len(r) >= 2 and r[1] == "closure")
            sig_last = float(sig[-1][3]) if sig and len(sig[-1]) >= 4 else float("nan")
            fh.write(f"{case.name},{ppm},{len(vol)},{t_last},{v_last},{st_name},"
                     f"{b_last},{n_pinch},{n_close},{sig_last}\n")
            series.append((ppm, case.name, vol, bubbles))
            print(f"{case.name}: ppm={ppm}  samples={len(vol)}  "
                  f"V_last={v_last} m3  status={st_name or 'n/a'}  "
                  f"bubbles={b_last}  pinchoff={n_pinch}  closure={n_close}  "
                  f"sigmaLiqMean={sig_last}")

    print(f"wrote {summary_path}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib is not installed; CSV only, no PNG")
        return 0

    fig, axes = plt.subplots(2, 1, sharex=True, figsize=(8.0, 6.5))
    for ppm, name, vol, bubbles in series:
        label = f"{ppm} ppm"
        if vol:
            axes[0].plot([t for t, _, _ in vol], [v * 1e9 for _, v, _ in vol], label=label)
        if bubbles:
            axes[1].plot([t for t, _ in bubbles], [b for _, b in bubbles], label=label)
    axes[0].set_ylabel("cavity volume [mm³]")
    axes[1].set_ylabel("bubble count (entrapment)")
    axes[1].set_xlabel("time [s]")
    axes[0].set_title("Wire cavity vs dissolved oxygen")
    axes[0].legend(loc="best", fontsize=8)
    axes[1].legend(loc="best", fontsize=8)
    axes[0].grid(True, alpha=0.3)
    axes[1].grid(True, alpha=0.3)
    fig.tight_layout()
    png = out / "cavity_bubbles_vs_time.png"
    fig.savefig(png, dpi=120)
    print(f"wrote {png}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
