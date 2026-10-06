# Validation metrics: experiment vs simulation

Simulations below were **not** at experimental scan/WFS. Fair comparison requires `val_exp_*` cases.

| metric | Experiment | Sim 7-strand contact | Sim Fe+Ni 5-strand |
|---|---|---|---|
| scan speed [mm/s] | 2.67 (160 mm/min) | 5.8 | 5.8 |
| power [W] | 600 | 600 | 600 |
| line energy [J/mm] | 225 | 103 | 103 |
| WFS [mm/s] | ~15.6 (bead-vol.) / "40 g" unclear | 44.9 | 52.2 |
| bead height [mm] | 1.32 ± 0.20 (X-ray); EDS 0.94 | 1.57 | 1.65 |
| penetration [mm] | 0.08 ± 0.03 (auto); guide 0.25–0.45; EDS ~0 | 0.55 | ~0.02 |
| pool length [mm] | 3.33 ± 0.18 (3.5 W) | 3.17 | ~4.8 (tail) |
| unmelted Fe | 5–12% area; d~190 µm | n/a | 13.7% build |
| unmelted location | along whole ~10 mm track | n/a | start-up only (~1.5 mm) |
| feed angle | 90° vertical | 90° | 90° |
| mode | conduction; tip in pool; no ball | conduction | conduction |

## Experimental measurements

- X-ray bead height: **1.32 ± 0.20 mm** (1.51 W), n=7 steady frames
- X-ray pool length: **3.33 ± 0.18 mm** (3.53 W)
- X-ray penetration (auto bright-line): **0.08 ± 0.03 mm**; parent visual guide **0.25–0.45 W = 0.23–0.45 mm**; EDS interface **~0**
- EDS bead height (long. midplane): **0.94 ± 0.10 mm** (may be below peak crest)
- EDS unmelted Fe area fraction: **4.8%** (bright-core dilated; abs threshold 160–180 → 8–12%); n=13 groups; median d_eq **189 µm**
- Unmelted distribution: **along whole track** (6/10 bins), not start-up only
- Video slowdown: **~5.3×** (19.75 s video / 3.75 s real)

## Parameter interpretation ("40 g")

- 40 g/min → WFS_metal ≈ 200 mm/s → bead area ≈ 31 mm² — **ruled out** (X-ray bead ~2.4 mm²).
- 40 g/h → WFS ≈ 3.3 mm/s → bead too small — unlikely.
- 40 g total for 10 mm track → absurd mass.
- **Adopted:** WFS_metal ≈ **15.6 mm/s** (nominal 10.1 mm/s on 0.9 mm solid-eq metal basis) from volume match to H≈1.32 mm × width≈2.6 mm bead. "40 g" likely a batch/spool label or unit mistranslation — **confirm with user**.

## Ready cases (generated, not run)

- `/workspace/laser_wire_ded/val_exp_600W_160mmpm_stranded` — 7-strand Invar on Invar, 600 W, 2.67 mm/s, WFS 15.6 mm/s, 10 mm track, feed 90°, focus 0, A=0.42, ~185k cells
- `/workspace/laser_wire_ded/val_exp_600W_160mmpm_fe_ni` — Fe+Ni 5-strand on Invar, same process, WFS 18.2 mm/s metal, ~166k cells

### Wall-time estimates (8 cores)

- Scaling from fe_ni box run: 7.4 h for 0.86 s sim → **~32 h on box** for 3.75 s
- Scaling from PC GPU-bench rate (~10.4 h / 0.86 s): **~45 h on PC**
- ±30% depending on time-step and I/O; Fe+Ni slightly different mesh

## Proposed model changes

1. **Run at experimental settings first** (ready cases) — current sims are 2.2× lower line energy and ~3× higher WFS.
2. **Lower wire absorptivity** (try 0.20–0.30 vs 0.42): experiment keeps unmelted Fe despite *longer* pool residence (1.2 s vs 0.55 s) → model over-heats strands.
3. **Keep/enforce beam shadowing** on inner strands: outer wires shield Fe cores in the bundle.
4. **Reduce strand-strand contact conductance** so Fe cores stay thermally isolated.
5. **Fe liquidus 1811 K**: ensure mixture liquidus does not melt pure-Fe cores too early in Ni-rich liquid; consider higher mushy resistance for solid Fe.
6. **Shallower pool:** lower substrate absorptivity and/or larger defocus/spot; experiment E_L is higher yet pen is smaller → coupling to plate overestimated in sim (A_sub=0.42, focus=0).
7. **Gentle feed start** already helps start-up lumps; will not fix mid-track unmelted Fe.