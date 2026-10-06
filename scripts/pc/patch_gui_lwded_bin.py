from pathlib import Path
p = Path(__file__).resolve().parents[2] / "gui" / "app.py"
t = p.read_text(encoding="utf-8")
old = 'export PATH="$HOME/OpenFOAM/$USER-v2406/platforms/linux64GccDPInt32Opt/bin:$PATH"'
new = 'export PATH="$HOME/lwded_bin:$HOME/OpenFOAM/$USER-v2406/platforms/linux64GccDPInt32Opt/bin:$PATH"  # prefer rebuilt solver'
if "lwded_bin:$HOME/OpenFOAM" in t:
    print("already patched")
elif old in t:
    p.write_text(t.replace(old, new, 1), encoding="utf-8", newline="\n")
    print("patched", p)
else:
    raise SystemExit(f"PATH line not found in {p}")
