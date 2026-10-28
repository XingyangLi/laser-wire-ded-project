# laser_wire_ded: open-source single-track laser wire-feed DED in OpenFOAM

This is a FLOW-3D AM/WELD-style melt-pool simulation of **laser wire-feed directed energy deposition**
(LW-DED, also called wire-laser additive manufacturing, WLAM). It is built on
**OpenFOAM.com (v2406/v2412)** and a custom solver, `laserWireDEDFoam`, which extends interFoam.
It was developed from the `ded_wire_melt/wireMeltFoam` solver (same VOF + enthalpy-porosity core).

```
laser_wire_ded/
  solver/laserWireDEDFoam/   C++ solver (wmake)       solver/Allwmake
  generate_case.py           writes a complete case (all parameters on the command line)
  materials.py               Invar36 / SS304 / 316L / Ti6Al4V / IN718 presets + paper configs
  run_case.py                mesh -> decompose -> run -> render
  visualize.py               3D renders, sections, track profile, time series, mp4/gif, wire close-up
  compare_runs.py            side-by-side images + metrics table of two rendered runs
  visualize_multicomp.py     multi-component (Fe/Ni strands) renders: composition, never-melted wire, build sections
  box_ofenv.sh               box: source OpenFOAM v2412 (mamba env) incl. the conda compilers for wmake
  launch_wsl_job.ps1         Windows: detached, keep-awake launcher for WSL jobs
  run_production.sh          WSL: production run + automatic rendering
  pc/run_stranded.sh         WSL: stranded-wire Transitional-R production run (+ pc/status_stranded.sh)
```

## Paper basis: Gao et al., Nat. Commun. 2026 (PMC13385772)

The default case reproduces the process in **Gao, Mumm, Ren, Yu, Li, Chuang, Sun, "Operando X-ray scattering
reveals ordering-mediated solidification in additive manufacturing", Nat. Commun. (2026),
doi:10.1038/s41467-026-73647-3**. The setup is described in its SI (Sect. 1, 8, Table S1) and in ref. 14,
Gao et al., Int. J. Mach. Tools Manuf. 194 (2024) 104089.

| Paper (wire-laser DED, Additec μPrinter) | This model |
|---|---|
| 3 diode lasers at 120°, each ≈1 mm diameter, near-Gaussian, focused on the wire | 3 inclined ray-traced Gaussian beams, 1/e² radius 0.5 mm (`--beam-radius`), azimuths 120° apart |
| Coaxial wire, 0.9 mm, fed vertically through the centre | vertical wire inlet patch (0.9 mm) at the top of the domain, fed at the WFS |
| Substrate translates; head fixed | lab (Eulerian) frame: solid substrate is driven at +v_scan by the Carman–Kozeny sink; the wire is driven at the WFS |
| "+" direction: 2 lasers in front of the wire, 1 behind; "–": 1 in front, 2 behind (SI Sect. 8) | `--beam-direction +/-` (set automatically per config) |
| Table S1: **Normal** 600 W, 6.7 mm/s, WFS 11.4 mm/s, "+" | `--laser-config normal` |
| Table S1: **Lack-of-Fusion** 400 W, 10 mm/s, WFS 17 mm/s, "+" | `--laser-config lof` |
| Table S1: **Transitional-R** 600 W, 5.8 mm/s, WFS 29 mm/s, "–" | `--laser-config transitional_r` |
| FLOW-3D AM: mesh 0.15 mm global, 0.075 mm in the pool; adiabatic walls; phase change, gravity, Marangoni, surface tension, conduction, laser absorption, viscosity | uniform 150 / 100 / 75 µm (`--resolution coarse/medium/fine`); adiabatic solid walls; the same physics, plus recoil pressure, evaporation and radiation losses (can be switched off) |
| IN718, absorptivity 0.42 (calibrated in ref. 14) | A = 0.42 for both metals (`--absorptivity`) |

**Not given in the paper (assumed, all CLI options):**
- beam incidence angle 25° from vertical (`--beam-angle`);
- beam focus 0.5 mm above the substrate on the wire axis (`--focus-height`);
- beam radius 0.5 mm.

The paper's material is IN718 on IN718 (also 316L and Ni on 316L). **Invar 36 wire on SS304 is the user's
choice.** The three configurations therefore use the paper's IN718 process windows with a different alloy pair.
`--material IN718` reproduces the paper's material exactly.

## Protected baseline: Transitional-R with the solid wire

The user wants to keep the solid-wire Transitional-R result. Its renders stay in
`C:\Users\dukyo\laser_wire_ded\viz\full_transitional_r`. A full backup is in
`C:\Users\dukyo\laser_wire_ded\results_keep\transitional_r_solid_wire\`, holding the renders, case_params.json,
the regenerated case settings, the exact code bundle and REPRODUCE.md. It was made with:
```bash
python3 generate_case.py --laser-config transitional_r --case full_transitional_r --resolution medium --np 4
```
(Its raw OpenFOAM time folders were lost when `~/laser_wire_ded` in WSL was reused on Oct 2. Only the renders and
summary.json survive.) The solid wire is still the default (`--wire-type solid`), so that command produces the
same case as before.

## Stranded wire (`--wire-type stranded`)

The wire can be a twisted multi-strand wire instead of a solid rod. Its strands are real geometry in the VOF field.
```bash
python3 generate_case.py --laser-config transitional_r --wire-type stranded --case full_transitional_r_stranded --np 8
cd full_transitional_r_stranded && ./Allrun 8
```
| Option | Default | Meaning |
|---|---|---|
| `--wire-type` | solid | `stranded` = 1 centre strand + a ring of strands, twisted |
| `--strands` | 7 | 1 + 6 (the standard 7-wire strand); 2-3 = ring only, >7 = larger ring |
| `--lay-length` | 10 x diameter = 9 mm | length of one full twist of the outer strands |
| `--lay-direction` | right | right (Z) or left (S) hand |
| `--strand-gap` | 0.04 mm | gas gap between neighbouring strands (centre-ring and ring-ring) |
| `--strand-feed-basis` | metal | `metal`: feed speed raised by A_solid/A_strands so the metal fed per second equals the solid wire; `wfs`: keep the nominal feed speed |
| `--wire-refine` | 1 (stranded) | number of times the cells in a vertical box around the wire are halved in x and y |
| `--refine-halfwidth` | wire radius + 0.3 mm | half width of that box |
| `--domain-y` | auto | `full` for stranded (a helix has no mirror symmetry), `half` (symmetry plane) otherwise |

**Geometry (defaults, 0.9 mm wire).** There are 7 equal strands of 0.273 mm. The ring strand centres sit at a radius
of 0.313 mm, so the outer envelope is exactly 0.9 mm, with 0.04 mm gas gaps between neighbouring strands. Metal fills
0.646 of the 0.9 mm circle (touching strands would fill 7/9 = 0.78). The rest is the gas in the gaps and in the outer grooves.

The **lay length of 9 mm (10 x d)** sits inside the 8-16 x d range used for concentric-lay stranded conductors
(e.g. ASTM B8 / IEC 60228 practice) and for 1x7 stranded welding and spray wires. It gives the outer strands a helix
angle of 12.3 deg, which is a tight, "well stranded" twist that is still clearly a strand and not a coil.
It is also short enough that the pattern turns visibly in the 2.5 mm of wire inside the domain (100 deg) and at the
inlet (about 1800 deg/s, or about 4 turns in the run).

**Same metal feed.** With the default `metal` basis, the feed speed is raised from 29.0 to 44.9 mm/s
(29 / 0.646). The metal volume fed per second is then the same as the solid 0.9 mm wire (18.4 mm^3/s), and so is
the expected bead area (3.18 mm^2). Everything else is identical to Transitional-R: the laser, beams, travel speed,
materials, domain size and the 100 um base mesh.

**How the strands are made.**
- The initial wire (`system/setExprFieldsDict`, run by `setExprFields`) is a frozen helix. Each strand is a disc in every
  cross-section, centred on the ring at the angle `phi_k = 2 pi k/6 + 2 pi z / lay`. The metal fraction is anti-aliased
  over one cell, so the discrete metal area equals the true strand area.
- The wire inlet (`0/alpha.metal`, patch `wireInlet`, `exprFixedValue`) uses the same formula, with the axial
  coordinate shifted by the length already fed, `s(t)`. As the wire moves down, the strand pattern on the inlet
  therefore rotates exactly as a real twisted wire's cross-section does when it passes a fixed plane. Gas flows in
  through the gaps at the feed speed.
- Inside the domain, the wire is carried down rigidly by the solid-velocity (Carman-Kozeny) term. The strands then
  heat, melt and merge individually: the beams hit the strand surfaces, the gaps cut conduction between the strands,
  and the grooves let light reach the inner strand.

**Mesh.** A 0.3 mm strand needs about 5 cells or more. The cells in a vertical box of +-0.75 mm around the wire
(the whole height, from the bottom of the plate to the top of the gas) are halved in x and y (`topoSet` + `refineMesh`,
x-y directions only), from 100 to 50 um. That gives 5.5 cells per strand diameter. Only x and y are split, so every
cell still belongs to a complete vertical column of cells, which the laser columns and the bead measurement rely on.
The rest of the domain is exactly the baseline mesh. The full width (no symmetry plane) doubles the base mesh to
158,340 cells, and the refinement brings it to **181,842 cells**. The 50 um cells lower the capillary time-step limit
from about 1.5e-5 s to about 5.1e-6 s, so a stranded run costs about 6 times as much as the solid-wire run.

### Wire-pool contact fix (`full_transitional_r_stranded_contact`)
The first stranded run (default geometry) failed. The beams focus 0.5 mm up the wire axis and are 25 deg from vertical,
so their centre rays hit the side of the 0.9 mm wire about 1.5 mm above the plate. During the 20 ms preheat (wire held
still), they melted a neck through the stranded wire there. The wire tip melted back into a ball at 1-2 mm that never
reached the pool, so the bead was 0.05 mm high, against 1.4 mm for the solid wire.
The fix is `--focus-height 0 --feed-start 0`:
- the 3 beams cross the wire axis at the substrate surface, so they hit the wire side about 1 mm up and the pool next to it;
- the wire is fed from t = 0 (no stationary preheat).
In 0.22 s box tests (150/75 um mesh), the wire stays bridged into one continuous pool, the plate melts under it and a deposit
trails behind. A focus of -0.5 mm also bridged, but left voids in the deposit.
With the default (0.5 mm focus) but feeding from t = 0, the liquid still sat higher on the wire (1.2-1.7 mm).
The run therefore differs from the solid-wire baseline in beam focus and feed start, as well as wire geometry and feed speed.
A coarse solid-wire test with the same fix also bridges, and builds its bead faster than the coarse solid baseline
(0.68 vs about 0.3 mm high at 0.25 s).

`visualize.py` also writes `wire_closeup.png`, a 3D close-up of the wire and cross-sections of the metal fraction at
5 heights (cell values, unsmoothed). Use `--wire-closeup-times 0,0.05,...` for given times, where 0 is the initial field.

## Fe/Ni 5-strand wire on Invar 36 (`fe_ni_5strand_invar`, multi-component model)

User case: a wire made of **3 pure-Fe + 2 pure-Ni strands, each 0.3 mm**, on an **Invar 36** substrate,
**3 x 200 W = 600 W** (Transitional-R beam arrangement '-'), **5 mm track**. Question: can the model show the iron
strands only partly melting and **unmelted wire fragments** ending up in the build?

```bash
ARGS="--laser-config transitional_r --wire-type stranded --strands 5 --strand-layout ring --strand-diameter 0.3e-3 \
      --strand-materials Fe,Ni,Fe,Ni,Fe --substrate-material Invar36 --focus-height 0 --feed-start 0 --track-length 5e-3"
python3 generate_case.py $ARGS --dx 1.2e-4 --refine-downstream 3e-3 --refine-halfwidth-y 1.3e-3 \
        --uniform-downstream 5.6e-3 --write-interval 0.02 --np 8 --case fe_ni_5strand_invar      # full run
python3 generate_case.py $ARGS --dx 1.5e-4 ... --case coarse_fe_ni_5strand_invar                  # coarse check
cd fe_ni_5strand_invar && ./Allrun 8
/workspace/vizenv/bin/python visualize_multicomp.py --case fe_ni_5strand_invar --out <viz dir>
```

**Wire.** All 5 strands sit on one ring around a small central gas gap (`--strand-layout ring`), order
Fe, Ni, Fe, Ni, Fe (with an odd count two Fe strands are neighbours). With the 0.04 mm strand gap the ring radius is
0.289 mm, the envelope 0.878 mm (close to the 0.9 mm paper wire) and the central gap 0.278 mm. Lay length
10 x envelope = 8.78 mm, right hand, helix angle 11.7 deg. Metal fills 58 % of the envelope.
Fe:Ni = 60:40 by area/volume, **57:43 by mass (Fe-43Ni wt%)** using room-temperature densities 7874 / 8908 kg/m3,
so the fully mixed wire is a high-Ni Invar-type alloy.

**Feed.** Same metal volume feed as Transitional-R: 29 mm/s x (0.9 mm solid wire, 0.636 mm^2) = 18.4 mm^3/s. The
5 strands have 0.353 mm^2 of metal, so **WFS = 52.2 mm/s** (below the 100 mm/s cap, `--max-wfs`). Expected bead
area 3.18 mm^2, as for Transitional-R. Travel speed 5.8 mm/s (TR); both are CLI options (`--scan-speed`,
`--wire-feed-speed`). Beam focus on the substrate surface and feed from t = 0 (the contact fix of the 7-strand run).

**Track length and domain.** 5 mm at 5.8 mm/s = 0.862 s (`--track-length 5e-3` sets the end time). The frame is
still the laboratory frame (fixed laser and wire, substrate moving +x), so the domain does not need to "contain" the
track: the deposit leaves through x-max. The default domain (x = -3.5 ... +6.5 mm, y = +-3 mm, z = -2 ... +2.5 mm)
already holds the whole 5 mm track at the end time (material laid down at t = 0 is then at x = 5.0 mm, 1.5 mm from
the outlet). To keep the track readable, the uniform-cell region is extended to x = +5.6 mm
(`--uniform-downstream`).

**Mesh.** Base 120 um, refined once in x and y (60 um, **5 cells per 0.3 mm strand**) in a vertical box
x = -0.74 ... +3.74 mm, y = +-1.3 mm (`--refine-downstream 3e-3 --refine-halfwidth-y 1.3e-3`), so any strand piece
carried out of the pool stays resolved until it passes the recording planes. **165,822 cells**; capillary time step
about 6.8e-6 s. The coarse check uses 150 / 75 um (4 cells per strand, 87,768 cells).

**Recording planes (full-length build at fine resolution).** Four y-z planes behind the pool (x = 1.97, 2.93, 4.01,
4.97 mm) write the cell values (alpha, cFe, cNi, uFe, uNi, T, ...) every half fine cell of travel (5.2 ms).
`visualize_multicomp.py` stacks the first plane that lies behind the pool tail into a 3D build volume with the part
coordinate xi = v t - x_plane. That gives cross-sections at any position along the 5 mm build, taken after the track
has solidified, and the never-melted fractions and fragment sizes.

### Multi-component model (solver `components{}` block)
- Tracers `cFe`, `cNi` (fraction of the cell's metal that is strand Fe / Ni). The substrate is the rest:
  c_Invar = 1 - cFe - cNi. They are transported conservatively with the MULES metal flux, like `cWire`, but with
  a bounded TVD (vanLeer) face value instead of upwind so strand fragments stay sharp. `cWire` = cFe + cNi is kept
  for the old dilution statistics.
- Properties per cell by rule of mixtures over (Invar, Fe, Ni): cp, k_s, k_l, L, sigma, dsigma/dT, absorptivity.
- **Solidus/liquidus from the local composition** through the Fe-Ni phase diagram: local Ni content
  w_Ni = 36 c_Invar + 100 cNi [wt%], interpolated in a table built from Swartzendruber et al. (1991) and recent
  DSC data (`materials.FE_NI_LIQUIDUS`): pure Fe 1811 K, Fe-10Ni 1777 K, Fe-40Ni 1725 K, minimum about 1712 K near
  60 % Ni, pure Ni 1728 K. So mixed Fe-Ni melt freezes around 1720-1730 K, while a pure Fe strand only melts at 1811 K.
  `--liquidus mixture` uses the linear rule of mixtures instead.
- **Unmelted-wire markers** `uFe`, `uNi`: start equal to cFe / cNi in the fed wire, are transported the same way,
  and are set to 0 for good once the cell's liquid fraction exceeds 0.5. A pure-Fe cell only reaches that above
  Fe's own liquidus. Any metal with u > 0 in the build is wire that **never melted** (an unmelted fragment).
- **Solid motion.** The Carman-Kozeny sink drives solid metal to `Usolid`. Inside the wire zone (a cylinder of
  1.5 wire radii above z = 0.06 mm) never-molten metal moves at the feed velocity. New (`meltedFollowsSubstrate`,
  on by default for this case): metal in that zone that has already melted (re-solidified deposit) moves with the
  substrate instead of being pushed down at the feed speed. Outside the zone all solid moves with the substrate. So a
  solid strand piece that is pushed into the pool and then carried behind the wire zone **freezes into the deposit
  and travels with it**. It does not vanish, and it keeps u = c until it is heated above its liquidus.
- `wireStubbing` (on by default, `--no-wire-stubbing`): wire-zone cells in the first cell above the solid,
  non-wire metal of their column are dragged with the substrate, not pushed into it. In practice this does the same
  as the wire-zone floor `zoneMinZ` (0.5 dx). Tests showed that it does **not** stop over-fed solid strands from
  being forced into the hot, still-solid substrate. That penetration is driven by mass conservation: the inlet
  keeps feeding 52 mm/s of incompressible wire, and the Carman-Kozeny "solid" is only a velocity penalty that
  pressure can overcome. See the limits below.
- **`rigidSubstrate{}` and `stubFloorZ` (2026-10-06, default off; `--rigid-substrate 100 --stub-floor`).**
  The defocus validation run showed that the cold wire tip is pushed into the *solid* plate during
  the first ~0.3 s (fl = 0 in those cells, 0.75 mm3 of never-melted wire down to z = -0.51 mm by 0.2 s,
  later trailing behind the pool as "unmelted strands below the plate line", also the source of the
  unmelted Ni). Cause: plate and wire carry the same Carman-Kozeny stiffness, so the pressure needed to
  keep feeding incompressible wire indents the plate as easily as it deflects the wire.
  `rigidSubstrate { enabled true; zTop 0; KFactor 100; flMax 0.05; }` multiplies K by KFactor in cells
  with centre z < zTop and fl < flMax (solid plate and solid deposit below the original surface;
  the pool and its mushy rim are unchanged). The fed wire metal then spreads along the plate and is
  dragged with the substrate (stub), as a real wire would deflect. `components{ stubFloorZ z; }` makes
  the stubbing support of every column at least z (generator: -dx/2, the top substrate cell centre), so
  never-molten solid strands within `stubContactDist` of the original surface follow the substrate even
  when the plate under the tip is molten. Implementation: `createMeltFields.H`, `TEqn.H` (K),
  `createComponents.H`, `updateWireZone.H` (floor).
- Pressure solver (multi-component cases): GAMG without the cheap coarsest-level solve and with a 10-cycle cap.
  With the extended refined box the cheap coarsest solve made GAMG stall (1000 cycles per solve, 10x slower).
- `postProcessing/meltPool/components.dat` logs, per component, the metal volume and the never-melted volume in the
  wire, in the deposit + pool, and in the solid track behind the pool tail.

Property sources (details and values in `materials.py`): JANAF / CRC (Tm, L, Tb, Lv), Ho, Powell & Liley 1972
(k of solid Fe, Ni), Quested ASM Hb. 15 2008 / Mills et al. 1996 (liquid k), Assael et al. 2006 / 2012 (density,
viscosity), Brillo & Egry 2005 (sigma(T) of Fe-Ni melts), Boley et al. 2015 (relative absorptivity Ni vs steel),
Swartzendruber et al. 1991 + Tetsu-to-Hagane 2026 DSC data (Fe-Ni liquidus/solidus).

### Limits of this model (please read)
- No grain-scale or dissolution kinetics. "Melting" of a strand is decided only by the cell temperature against
  the cell's liquidus. Mixing is VOF/tracer mixing at the cell level, with numerical diffusion over about 1-2 cells
  at strand/melt boundaries. A strand surface cell that mixes with Ni-rich melt gets a lower liquidus, which
  mimics dissolution only crudely.
- Liquidus/solidus by rule of mixtures in the Ni content (binary Fe-Ni table). Invar's Mn/Si/C are ignored, and no
  solute partitioning or microsegregation is modelled.
- One density for all metals (incompressible VOF). A Fe fragment neither sinks nor floats in the melt, and a solid
  fragment in the pool is pinned to the substrate velocity once outside the wire zone, instead of being moved by the
  flow.
- Pure metals melt isothermally in reality; the model uses a 10 K numerical freezing range (8 K minimum in the table).
- Absorptivities of Fe (0.42) and Ni (0.34) are estimates scaled from the calibrated 0.42.
- **Over-feeding / stubbing.** If the beams cannot melt the wire as fast as it is fed (the case here: about 240 W
  absorbed against about 180 W needed just to melt 18.4 mm^3/s of wire), the unmelted strand tips pile up under the
  wire. Because the feed is imposed and the metal is incompressible, they get pushed into the softened substrate
  (seen down to z = -0.4 mm in the coarse run). A real wire would buckle, stub or lift the nozzle instead. The fact
  that unmelted Fe/Ni ends up in the deposit is a real consequence of the energy balance. The exact location and
  depth of those pieces is not reliable.
  `--rigid-substrate 100 --stub-floor` (above) removes the push into the solid plate; strands can still be
  pushed into liquid pool. `--stubbing` (below) additionally stops the feed when the solid wire stands on
  solid support.
- The end of the track (laser switch-off, crater) is not simulated; the run stops when 5 mm have been deposited.

### Wire stubbing model (`--stubbing`, solver `stubbing{}`, 2026-10-06, default off)

Why: with a gap between the wire tip and the plate the cold wire is fed down at 18 mm/s. If the beams
have not melted it by the time it arrives and the plate under it is still solid, a real wire stubs:
it cannot go through the plate, so it stops (and the feeder slips / the wire buckles or lifts the
torch). The old rules (`wireStubbing`, `rigidSubstrate`, `stubFloorZ`) only stop the *tip cells*;
the inlet keeps feeding incompressible metal, so the wire is squeezed sideways or into the plate.

What the solver does each time step (`updateWireZone.H`, state in `createStubbing.H`):

1. For every vertical cell column inside the wire zone it finds the **solid support**: the
   contiguous solid metal (liquid fraction < `supportFlMax` 0.5) rising from the bottom of the plate,
   not counting never-molten wire (so a molten plate under the tip is *not* a support; `useFloor`
   would also count the original plate line).
2. **Contact cells**: metal cells (alpha > 0.5) of *never-molten* wire (unmelted Fe/Ni markers or
   wire tracer without melt history) with fl < `wireFlMax`, within `contactDist` (1.5 dx) above that
   support, inside 1.5 wire radii of the axis, with at least `minLength` (1.9 dx) of solid unmelted
   wire directly above them, i.e. a rod of solid wire standing on solid metal.
3. If at least `minContactCells` such cells exist anywhere (summed over all processors) the wire
   is **stubbed**: the feed factor relaxes to 0 with time constant `responseTime` (0.5 ms); when the
   contact is gone (tip melted, plate melted, contact moved away) it relaxes back to 1. The whole
   wire is a rigid rod: the feed velocity of every wire-zone cell **and** of the `wireInlet`
   boundary is multiplied by the factor, so no metal is pushed in while the wire stands. Feed that
   could not enter is lost (not caught up later) and reported as stalled feed.
4. With `dragContact` (default) the contact cells move with the plate (+x, 2.67 mm/s), i.e. the
   tip slides tangentially with the part instead of being pinned.

Logged in `postProcessing/wireTransfer/wireTransfer.dat` (every statistics interval and at write
times): `stubbed`, `stallFactor`, `nContactCells`, `contactArea`, `supportZ`, `nStubEvents`,
`contactTime` (total time in contact), `firstStubTime`, `stalledLength/Volume`, `fedLength/Volume`,
plus wire-transfer diagnostics for the gap study: `tipZ` (lowest solid never-molten wire),
`hangMinZ`, `gapMin`, `bridged`, `nBridgedCols`, `bridgedArea`, and the hanging liquid "ball"
(`ballVolume`, `ballDiamEq`, `ballWidthX/Y`, `ballHeight`, `ballBottomZ/TopZ`). The log prints
`Stubbing: ...` when a contact starts/ends and a `WireTransfer:` summary line. On restart the
counters are read back from the .dat file. Without a `stubbing{}` block nothing changes
(`--wire-transfer-stats` writes the file but never stalls the feed).

Smoke test (`scripts/pc/smoke_stubbing.sh`, 16k cells, 0.3 mm gap, 1 W so nothing melts): the solid
tip landed on the plate at 21.0 ms; with `--stubbing` the feed factor fell to 4e-4 within 4 ms and the
fed volume stayed at 0.130 mm3 (stalled 0.086 mm3 by 35 ms); diagnostics-only and stubbing-off runs
kept feeding (0.216 mm3) and were identical to each other.

Limits: no feeder slip dynamics (instant rigid stop with a 0.5 ms ramp; buckling of the stalled
column: optional, next section); the
stall applies to the whole wire, also to strands not touching; the helical strand pattern at the
inlet is a function of time, so after a stall it is offset from the wire already in the domain
(far above the tip); contact detection is cell based (needs ~2 solid cells of wire on solid metal).

### Wire buckling under the stall (`--wire-buckling`, solver `stubbing{ buckling{} }`, 2026-10-06, default off)

Why: with `--stubbing` alone a stalled wire simply stops; the feed the drive could not push in is
only counted. A real stalled wire is a slender column under displacement-controlled compression: the
free length between the contact tube and the stub tip bows sideways (and, off-model, the drive rolls
slip). The buckling option lets the solid, never-molten wire column bend inside the domain, using the
same machinery that feeds it (target velocity of the solid metal in the Carman-Kozeny sink), not a
solid-mechanics solver.

Each time step while the stubbing model reports solid-solid contact (`updateWireZone.H`, parameters
and state in `createStubbing.H`):

1. **Column.** Pinned end = lowest contact cell along the wire axis (`sTip`), clamped end = the
   `wireInlet` (highest wire-zone cell, `sIn`, the wire is guided in the nozzle above the domain).
   Free length `L = sIn - sTip` (~2.4 / 3.4 / 4.4 mm in the 1 / 2 / 3 mm gap cases once the tip
   is on the plate).
2. **Compression** `S` = stalled feed of the current contact (integral of `(1 - stallFactor) x feed`
   while in contact; it decays with `releaseTime` 1 ms after the contact is lost).
3. **Euler threshold.** Axial force of the shortened wire `P = E A S / (pathFactor L)` reaches
   `P_cr = pi^2 E I / (K L)^2` at the critical stall
   `S_cr = pi^2 r_g^2 pathFactor / (K^2 L)` with `r_g = R/2` (solid round section, R = 0.473 mm
   envelope radius of the 5-strand wire) and `K = 0.70` (clamped-pinned): ~0.47 / 0.33 / 0.26 mm
   for L = 2.4 / 3.4 / 4.4 mm, i.e. 26 / 18 / 14 ms of stalled feed at 18.18 mm/s. E cancels.
   `criticalStall` overrides it; `pathFactor > 1` (compressed wire longer than the free column,
   e.g. the conduit) delays it.
4. **Bow amplitude.** Beyond `S_cr` the column bends in its first clamped-pinned mode
   `phi(xi) = [sin(b xi) - xi sin b] / max` (xi = 0 at the stub, 1 at the inlet, tan b = b,
   b = 4.493; peak at xi = 0.40) with the inextensible-elastica amplitude that takes up the excess
   feed: `A_target = sqrt(absorbFraction (S - S_cr) L / c)`, `c = 1/2 int phi'^2 = 2.58`
   (a 3.4 mm column takes up 0.1 mm of extra feed with a 0.36 mm bow). Caps:
   `A <= min(maxAmplitude x 2R, maxSlope x L)` = min(1.5 diameters = 1.42 mm, 0.2 L) = 0.48 / 0.68 /
   0.88 mm for L = 2.4 / 3.4 / 4.4 mm (axis slope at the stub ~4 A/L <= 0.8), and no
   buckling for `L < minColumnLength` (4R). The commanded amplitude follows the target with
   `responseTime` 0.5 ms and `|dA/dt| <= maxLateralSpeed` (2 x feed = 36 mm/s).
5. **Motion.** Every wire-zone cell at height xi gets the extra target velocity
   `dA/dt phi(xi) e_b` (a pure shear field, divergence free); the wire zone itself follows the bent
   axis (union of the straight and the bent cylinder), so the solid never-molten metal is moved
   sideways by the Carman-Kozeny sink exactly like it is fed. Contact cells keep sliding with the
   plate, melted / liquid metal is unaffected (VOF + melting own the tip once it is liquid).
6. **Plane.** `plane auto`: an inclined wire bows in its own vertical plane, away from the plate
   (e_b = the upward normal of the axis in that plane); a vertical / coaxial wire (the gap cases)
   bows horizontally, normal to the scan direction (e_b = axis x scan = +y). `direction (x y z)`
   overrides. The sign is fixed (+), a real wire picks it from its imperfections.
7. **Release.** When the contact is lost (tip or plate melted, tip slid off) `S` decays and the bow
   springs back elastically at the same capped rate (`springBack true`); with `springBack false`
   the bent strand stays where it is (plastic) until it melts.

Logged in `wireTransfer.dat` (same file, new columns; an old file gets a new header block):
`buckled`, `bkStall` (S), `bkCritical` (S_cr), `bkLength` (L), `bkAmp` / `bkAmpTarget` (commanded
bow), `bkLatSpeed` (dA/dt), `bkTipS`, `bkEvents`, `bkMaxAmp`, and **measured** from the solid
never-molten wire metal (volume-weighted centreline in 24 axial bins from the stub to the inlet):
`bkTipOffB` / `bkTipOffT` (offset of the lowest bin from the original axis along e_b and along
axis x e_b, i.e. y and -x for the vertical wire: the tip drag with the plate shows in -bkTipOffT),
`bkBow` (largest offset along e_b from the tip-inlet chord = measured midspan bow), `bkBowXi`
(where), `bkSeverity` (= bkBow / wire diameter), `bkDirX/Y/Z` (e_b; the buckling plane is axis +
e_b). The log prints `Buckling: ... buckles` / `... released` and a `WireBuckling:` line with the
statistics. The measured columns are also written with buckling off (reference). Restart: S, A,
the pinned end, events and max amplitude are read back from the file.

Generator: `--wire-buckling` (needs `--stubbing`), `--buckle-max-amplitude` (1.5 diameters),
`--buckle-critical-stall` (-1 = Euler), `--buckle-path-factor` (1), `--buckle-plane auto|feed|lateral`,
`--buckle-no-springback`. `scripts/pc/gap_study_generate.py` adds `--wire-buckling` to every gap
case (`--no-buckling` to leave it out).

Smoke test (`scripts/pc/smoke_buckling.sh`, 26.7k cells at 200/100 um, 0.3 mm gap, 3.5 mm gas layer,
1 W so nothing melts, 70 ms, serial, ~17 min each; results `~/lwded_gap/smoke_buckle/summary.txt`):
both runs stub at t = 10 ms (tip z 0.10 mm, stall factor 0.02 at 12 ms, 1e-7 at 18 ms), free column
L = 3.18 mm, Euler S_cr = 0.355 mm. **on** (`--stubbing --wire-buckling`): `Buckling: stalled wire
column buckles at t = 30.0 ms` (S = 0.355 mm); commanded / measured bow 0.096 / 0.092 mm at 32.7 ms,
0.283 / 0.271 mm at 37.8 ms, 0.471 / 0.450 mm at 43.0 ms, cap 0.636 mm (0.2 L) reached at ~49 ms,
measured 0.62-0.645 mm until 70 ms, peak at xi = 0.38-0.43 (mode peak 0.40), along +y (e_b = (0 1 0));
stub tip offset +0.01-0.04 mm in y. **off** (`--stubbing` only): same stub, same stalled feed
(0.378 mm3 by 70 ms), measured |bow| <= 0.06 mm throughout (strand / cell noise). In both the
stub tip slid ~0.2 mm in +x with the plate (bkTipOffT -0.20 mm). No errors; max Courant
after 31 ms 0.007 (off: 0.0007), same 4907 time steps (capillary-limited).

Limits (this is **not** beam FEA): one prescribed mode shape whose amplitude is a kinematic
function of the stalled feed (no bending stress, no axial wire stress, no dynamics / inertia of the
wire, no higher modes, no snap-through); the bent wire does not feel other metal (it is the sink
that moves it, so it would push through liquid; the bow is directed away from the plate or
sideways); the bow does not let wire in: the inlet stays stalled and the bow is made by shearing
the wire already in the domain sideways (volume conserved; the section normal to the bent axis
thins by cos(slope), >= 0.78 at the cap; a real bowing column would draw in the excess feed); r_g of a solid round
section is used for the twisted 5-strand bundle (loose strands would buckle earlier: r_g of one
0.3 mm strand = 75 um, S_cr 9x smaller); plasticity only as the `springBack` switch; the column
ends are idealised (clamped inlet at the domain top, pinned stub).

### Wire-substrate gap study (`gap_study_1mm/2mm/3mm`)

Same as `val3mm_fe_ni_v2` (600 W in 3 beams at 25 deg, focus 1.5 mm below the plate, zR 1.2 mm,
2.67 mm/s, Fe/Ni 5-strand wire fed at 18.18 mm/s, Invar plate, rigid substrate x100, stub floor)
but the tip starts 1, 2 or 3 mm above the plate and `--stubbing` + `--wire-buckling` are on. Geometry: the wire is on the
axis of the beam cone; each beam axis is (z + 1.5 mm) tan 25 deg from the wire axis at height z, and
the rays have 0.85 mm radius, so the tip at 1 mm is in the flank of the beams (beam axis 1.17 mm from
the wire axis), at 2 mm hardly lit (1.63 mm), at 3 mm practically dark (2.10 mm). The feed is
continuous: an unmelted tip would reach the plate after 56 / 111 / 166 ms. The question is whether
it bridges into the pool, balls up and drips, or stubs. Metrics and outputs: `cases/gap_study/README.md`.

## Two-metal model (Invar 36 wire on SS304)

A passive composition tracer `cWire` (1 = wire metal, 0 = substrate) is transported conservatively with the VOF
flux. Every thermophysical property is mixed per cell by the rule of mixtures:
cp, k_s, k_l, L, T_sol, T_liq, σ, dσ/dT and A.

The liquid fraction uses the local T_sol/T_liq, and the Marangoni stress uses local σ(T) and dσ/dT.
Density and viscosity are single-valued in the VOF (the mean of the wire and substrate values is used; Invar and 304 differ by about 3%).
Composition-driven (solutal) Marangoni is not included.

| Property (effective, used in the model) | Invar 36 (Fe-36Ni) | SS304 |
|---|---|---|
| ρ [kg/m³] (solid/liquid mean; single VOF density) | 7700 (RT 8050) | 7500 (RT 7900) |
| cp [J/kg K] (effective high-T) | 600 (est.; RT 515) | 650 |
| k solid / liquid [W/m K] | 15 (est.; RT 10.15) / 30 | 22 / 30 |
| T_sol / T_liq [K] | 1700 / 1725 (approx.) | 1673 / 1727 |
| L [J/kg] | 2.65e5 (Fe/Ni mixture) | 2.6e5 |
| σ(T_liq) [N/m], dσ/dT [N/m K] | 1.84, −3.5e-4 | 1.80, −4.0e-4 |
| μ [Pa s] | 5e-3 | 6e-3 |
| absorptivity | 0.42 (assumed, as calibrated for IN718) | 0.42 |

Values are taken from `materials.py`, which is authoritative. Sources are listed in its docstring:
- Carpenter Invar 36 technical datasheet (ρ, cp, k, melting range);
- Brillo & Egry, J. Mater. Sci. 40 (2005) 2213 (surface tension of Fe-Ni melts);
- Mills, *Recommended Values of Thermophysical Properties for Selected Commercial Alloys* (2002) (304; Fe-Ni liquid estimates);
- ref. 14 Table 1 (IN718).

Values marked "est." are estimates and the main source of property uncertainty for Invar.

**Track metrics** (`postProcessing/meltPool/meltPool.dat`, `viz/summary.json`) are measured in a y–z slab
behind the pool tail, i.e. in solidified track:
- bead height above the original substrate (z = 0);
- bead width at z = 0;
- bead area above z = 0;
- fused area below z = 0 and penetration depth;
- geometric dilution = fused/(fused + bead);
- compositional dilution = 1 − (mean cWire in the track).

## Quick start (Linux / WSL, OpenFOAM.com sourced)

```bash
cd ~/laser_wire_ded
(cd solver && ./Allwmake)                                     # build the solver once
python3 generate_case.py --case case_lwded --laser-config normal --np 8   # paper 'Normal' case, Invar36 on SS304
# also: --laser-config lof | transitional_r | single (legacy single inclined beam + side-fed wire)
python3 run_case.py --case case_lwded --np 8                  # mesh + run + render (case_lwded/viz)
# or by hand:  cd case_lwded && ./Allrun 8
~/vizenv/bin/python visualize.py --case case_lwded --out case_lwded/viz     # re-render anytime
```

Open `case_lwded/case.foam` in ParaView. Use "Decomposed Case" while the run is going, or after `reconstructPar`.

Examples:
```bash
python3 generate_case.py --case p2500 --power 2500 --scan-speed 0.008 --wire-feed-speed 0.03
python3 generate_case.py --case ti64 --material Ti6Al4V --feed-angle 35 --wire-diameter 1.2e-3
python3 generate_case.py --case tophat --profile tophat --spot-radius 1.0e-3
python3 generate_case.py --case q2d --dim 2d --np 4           # quasi-2D longitudinal section (minutes)
python3 generate_case.py --case quick --resolution coarse --end-time 0.2
python3 generate_case.py --print                              # derived numbers only
python3 generate_case.py -h                                   # all options
```

## Model

### Frame of reference (motion approach)
The simulation uses a **laboratory frame: the laser and the wire nozzle are fixed, and the substrate moves**
through the domain in +x at the scan speed. This is option (a) in the design brief. Cold substrate
enters through `inletSubstrate` (x-min, alpha = 1, U = v_scan, T = T0), and the solidified bead and substrate
leave through `outlet` (x-max). Solid metal is forced to move rigidly by the Carman–Kozeny momentum sink
`-K(fl)(U - U_solid)`, with `U_solid = (v_scan, 0, 0)` everywhere except inside the wire, where
`U_solid = wire feed velocity`. The wire enters through a fixed `wireInlet` patch cut out of the top boundary
(topoSet `cylinderToFace` + createPatch).

Why this approach:
* The **wire inlet and the laser never move** relative to the mesh, so there's no moving inlet, no
  mesh motion, and no remeshing. Fine cells are needed only around one fixed spot.
* The melt pool becomes **truly steady** in a short domain. The track length that can be simulated is
  limited only by simulated time, not by domain length: 0.6 s at 10 mm/s gives 6 mm of track.
* The enthalpy-porosity sink already exists for the wire, so the substrate needs the same mechanism with a
  different target velocity, and nothing new is needed for robustness.
* A moving-source frame (option b) would need a long domain, refinement along the whole track, and a wire
  inlet that moves along the top boundary. All of those are fragile or expensive in OpenFOAM.

Consequences: the material and bead travel through the mesh, so their shape is carried by VOF advection
(MULES with interface compression). Velocities in the plots are shown relative to the substrate.
The ambient gas also moves at v_scan, which is physically consistent: the gas is at rest relative to the part.

### Laser (ray-traced surface heat flux)
The beam is vertical (−z). Its profile is Gaussian `I = 2P/(πw²) exp(−2r²/w²)` (w = 1/e² radius) or top-hat.
Every vertical column of cells is a ray bundle carrying `P_col = I(x,y)·A_col`. Marching down the column,
energy is absorbed where the running maximum of the metal fraction increases:
`dE = A_abs · P_col · (α_cell − max α above)⁺`. So the energy goes **into the first metal surface the beam
hits**, whatever its shape: wire, droplet, pool, or bead. Anything below is **shadowed**, including the
substrate under the wire. `--no-shadowing` lets the beam pass through the solid wire.
This is the same idea as FLOW-3D's single-reflection ray tracing with constant absorptivity.
It needs a structured blockMesh mesh and a decomposition without cuts in z (`simple`, n = (nx ny 1)),
and the generator ensures both. Incident and absorbed power are logged every step for a power balance check.

### Physics included
| Phenomenon | Implementation |
|---|---|
| Free surface | VOF (alpha.metal), MULES, interface compression (interFoam) |
| Melting / solidification | Enthalpy-porosity (Voller–Prakash), linear fl(T) between Tsolidus–Tliquidus, latent heat source with iterative fl update |
| Solid behaviour | Carman–Kozeny sink to U_solid (substrate: v_scan, wire: feed velocity) |
| Surface tension | CSF on liquid metal only, σ(T) = σ0 + dσ/dT (T − Tliq) |
| Marangoni | Tangential thermocapillary stress dσ/dT ∇_sT \|∇α\|, density-scaled to the metal side |
| Recoil pressure | Clausius–Clapeyron, p_r = 0.54 p0 exp[L_v M/R (1/T_b − 1/T)], added to the balanced CSF face force (`--no-recoil`) |
| Evaporative cooling | q = L_v · 0.82 p_sat(T) √(M/2πRT) (Hertz–Knudsen–Langmuir, β_r = 0.18) (`--no-evaporation`) |
| Radiation, convection | εσ(T⁴ − T0⁴) + h(T − T0) at the free surface (`--no-radiation`, `--no-convection`) |
| Gravity | yes; Boussinesq buoyancy in the liquid optional (`--buoyancy`) |
| Conductivity | k_solid → k_liquid with the liquid fraction; argon conduction in the gas |
| T clipping | T in [250 K, T_boil + 400 K] (evaporation keeps T near T_boil anyway) |
| Fusion zone | Advected melt-history marker (`meltHistory` = 1 where metal has been liquid) |

Free-surface source terms use the area density `2α|∇α|`. All losses are linearised implicitly,
so T stays positive.

Numerical choices: the argon viscosity is multiplied by 20 by default (`--gas-viscosity-factor`). This damps
parasitic gas currents next to the interface, which would otherwise control the time step. The gas shear on
the pool is still negligible next to the Marangoni stress. The time step is set by the Brackbill capillary
limit `dt ≤ 0.8 √(ρ̄ dx³ / 2πσ)` and by Co ≤ 0.4.

### Legacy single-beam process (`--laser-config single`, 316L)
| Parameter | Default | Option |
|---|---|---|
| Laser power | 2000 W | `--power` |
| Spot radius (1/e²) | 1.2 mm | `--spot-radius`, `--profile gaussian/tophat` |
| Absorptivity | 0.35 | `--absorptivity` |
| Scan speed | 10 mm/s | `--scan-speed` |
| Wire | 1.0 mm, 25 mm/s (1.5 m/min) | `--wire-diameter`, `--wire-feed-speed` |
| Feed | 45°, front feed, aimed at the laser centre | `--feed-angle`, `--feed-side`, `--wire-aim` |
| Wire start | 20 ms after the laser (pre-heat) | `--feed-start` |
| Domain (half, y ≥ 0 symmetry) | x −4.5…+7 mm, y 0…4 mm, z −2.5…+2.5 mm | `--upstream`, `--downstream`, `--half-width`, `--substrate-thickness`, `--gas-height` |
| Mesh | coarse 150 µm (36k cells), medium 100 µm (117k), fine 75 µm (271k) | `--resolution`, `--dx` |
| End time | 0.6 s (6 mm of track) | `--end-time` |

The expected bead cross-section from mass balance is A_wire·v_wire/v_scan = 1.96 mm².

### Quasi-2D option (`--dim 2d`)
This is a longitudinal x–z section, one cell thick. The wire becomes a slab whose thickness gives the same
bead height for a bead width of 2w. The laser power per unit depth is P/(2w). There's no lateral conduction or
lateral flow, so the pool is hotter and longer than in 3D. Use it for trends and debugging only;
`--power-2d-factor` can recalibrate the power.

## Outputs
* `postProcessing/meltPool/meltPool.dat`: time, pool length, width, depth, pool top, T_max, molten and metal
  volume, incident, absorbed and lost power (full-beam equivalent), wire-tip height, bead height and width
  at the probe x, and Δt.
* Fields: `alpha.metal T liquidFraction U p_rgh Qheat zSurface pRecoil meltHistory`.
* `visualize.py` writes `viz/`:
  * `frames/` and `animation.mp4` / `.gif`
  * `latest_3d.png` (free surface coloured by T, liquidus line, beam)
  * `latest_top.png` (top view)
  * `latest_section_long.png` (y = 0 section: T in metal, surface, liquid, fusion line, melt velocity)
  * `latest_cross_section.png` (x = const sections: bead + fusion line)
  * `track_profile.png/.csv` (centreline height z(x) and bead cross-section z(y))
  * `timeseries.png`, `summary.json`

## Comparison with FLOW-3D AM / FLOW-3D WELD
| Feature | FLOW-3D AM/WELD | laser_wire_ded |
|---|---|---|
| Free surface | TruVOF, gas as void (pressure/thermal BC) | Two-phase VOF (MULES), argon resolved |
| Melting/solidification | enthalpy, solid fraction, drag | same (enthalpy-porosity, Carman–Kozeny) |
| Laser | ray tracing with multiple reflections, Fresnel absorption | single-hit vertical ray march, constant absorptivity (no Fresnel, no multiple reflections, no inclined beam) |
| Surface tension, Marangoni | yes | yes (σ(T), liquid-only CSF) |
| Recoil, evaporation | yes (incl. evaporative mass loss) | recoil + evaporative cooling (no mass loss) |
| Wire feeding | moving solid component / mass source | wire inflow patch + Carman–Kozeny feed velocity |
| Moving heat source | moving laser on a fixed part | fixed laser, moving substrate (equivalent kinematics) |
| Shielding gas flow | usually not resolved | resolved (incompressible); no nozzle jet by default |
| Temperature-dependent properties | full tables | constant ρ, cp; k(fl), σ(T) |
| Multi-track, multi-layer | yes | single track (multi-track/layer not implemented) |
| Microstructure (G, R, cooling rate) | built-in outputs | not yet (T, fl and the fusion zone are available to derive them) |
| Mesh | FAVOR structured, adaptive | structured blockMesh; refinement by grading, optional x-y refinement box around the wire |
| Parallel | SMP / MPI | MPI (decomposePar), Linux/WSL |
| Cost | license | free (GPL) |

Main limitations to keep in mind:
* Incompressible phases with one metal density mean there is no shrinkage.
* Constant cp (latent heat is handled separately).
* Evaporation removes heat but not mass.
* The vertical beam has no keyhole multiple reflections. LW-DED normally runs in conduction mode, so this is acceptable.
* The wire is only "rigid" through the Carman–Kozeny sink, so a wire that hits the substrate unmelted bends
  instead of stubbing.
* The VOF bead shape diffuses slightly while it is advected to the outlet.

## Contact-line pinning and porosity (single-wire track)

Both models are off unless `constant/meltProperties` contains `contactLine{ enabled true; }` or
`porosity{ enabled true; }`. `generate_case.py --contact-pinning` and `--porosity` write those
blocks. Existing stranded-wire cases do not have the blocks, so their behaviour is unchanged.
The dedicated setups are `cases/single_wire` (3-D solid wire, no planted pores) and
`cases/single_wire_demo` (short 2-D run with `--pore-seed`). See the README section
"Single-wire track: contact-line pinning and porosity".

### Why not a wall contact-angle boundary condition

The substrate is a block of metal cells (`alpha.metal = 1` for z < 0), not a wall. The bottom
patch is the underside of the plate. The triple line of the bead is the curve where liquid metal,
shielding gas and solid metal meet *inside* the mesh. `constantAlphaContactAngle` on `bottom`
would never see it. The model therefore finds that internal line from the VOF field.

### Contact-angle hysteresis, closed by solidification

At each interface cell that touches solid support (substrate or metal that has already been
molten; never unmelted wire) and also touches gas:

- Apparent angle through the metal: `theta = acos( clamp( -n_alpha · n_solid, -1, 1 ) )`,
  with `n_alpha = grad(alpha)/|grad(alpha)|` (into the metal) and `n_solid` the direction from
  the solid neighbour toward the interface cell (out of the solid).
- Liquid fraction of the metal at the line, `fl_m`, sets a pinning factor
  `s = 0` above `flFree` (0.60), `s = 1` at or below `flPin` (0.15), linear between.
  A frozen deposit with no liquid neighbour is `s = 1`.
- The allowed window is `[(1-s) theta_R, (1-s) theta_A + s π]`. Defaults `theta_R = 20°`,
  `theta_A = 90°` (a wide hysteresis band used for liquid steel on solid steel; not a
  measured value for a specific pair).
- Inside the window the Young force is zero and a Darcy sink `Kpin (U - U_substrate)`
  (`Kpin = 1e7 kg/m³/s`) holds the line on the plate velocity. That is the pin.
- Outside the window a volumetric Young force
  `σ (cos theta_limit - cos theta_app) |grad alpha| / dx`, directed in the wall plane from
  metal toward gas, restores the angle. `theta_limit` is the advancing angle when the apparent
  angle is larger, and the receding angle when it is smaller.

So a molten toe can spread only by reaching 90°, can pull back only by reaching 20°, and a toe
that freezes is stuck and travels with the substrate. That is the deposited-bead pin.

### Porosity

Gas connectivity is a flood fill through cells with `alpha < alphaOpen` (0.5), seeded from the
open boundaries (`top`, `inletGas`, `outlet`, `side`, `wireInlet`) and from every column that
is gas all the way to the top of the domain. What the flood does not reach is enclosed.

- **Lack of fusion** if that gas is within `lofBand` of the plate and a cell above it in the
  same column is deposited metal (`meltHistory > 0.5` or cell centre above the plate). This is
  the gap left when pinning stops the bead wetting the substrate.
- **Keyhole** if the cavity is capped, lies more than `keyholeDepth` below the metal-column
  height, and a neighbour is hotter than `keyholeTfrac * Tboil` or carries recoil pressure
  above `keyholeRecoil`. Recoil here only depresses the surface; it does not remove mass.
  An open keyhole is atmosphere, not a pore. The tag means "this closed pore was still a hot
  cavity when it was counted".
- **Gas entrapment** otherwise (a fold-over bubble, or a cold closed cavity).

The shell liquid fraction is the mean `liquidFraction` of metal face-neighbours. Below `flLock`
(0.35) the component is locked: `poreMarker = 1` and `alpha` is reset to at most `alphaLock`
(0.05) so MULES cannot fill it. Remelting the shell (`fl >= flLock`) drops the lock. The reset
removes whatever metal numerical diffusion had added; that mass error is the diffusion, not a
physical shrinkage model.

`--pore-seed` (demo only) writes two initial gas regions so a sub-millisecond run still exercises
the classifier: a bubble inside the plate (entrapment) and a gap under a `meltHistory = 1` cap
(lack of fusion). Production cases omit it.

Outputs: `postProcessing/porosity/porosity.dat` (counts, volume, volume fraction, diameters) and
`pores.dat` (id, type, locked flag, volume, equivalent diameter `(6V/π)^(1/3)`, centroid).
`scripts/quantify_pores.py` prints the last sample. Half-domain runs are not mirrored.

### Wire-surface pinning and the wake cavity (`--pin-wire`, `--wire-cavity`)

`cases/wire_cavity` turns on a second triple line: liquid metal, argon, and **unmelted** wire. It is off unless `contactLine{ pinWire true; }`, so `cases/single_wire` and the 2-D demo keep the old rule (the feed is not a wall).

The apparent angle uses the same definition as the plate, with the solid normal equal to the outward radial direction of the wire. The window is `thetaRecedingWire` / `thetaAdvancingWire` (defaults 25° / 70°, separate from the plate's 20° / 90°). Inside the window the Young force is zero and the same Darcy sink acts. The target velocity depends on `wireVelocity`:

- `head` (default) — the line is held at zero velocity in the lab frame. The kink stays at a fixed height while the wire, still driven at the feed speed by the Carman–Kozeny term inside the wire, slides through it. That is the quasi-steady shape in the radiograph.
- `wire` — the line is stuck to a material point of the wire and is carried downward at the feed speed. A kink then falls into the pool on the feed timescale (tens of milliseconds at 30 mm/s).

`wireSector` (default off; `--wire-sector`) is a second window on the trailing face of the wire, the +x side that faces the bead trail. It is a stand-in for an oxide film: the line there is pinned over a wide band (defaults 60° receding / 140° advancing) while the front of the wire keeps `thetaRecedingWire` / `thetaAdvancingWire` (25° / 70°). With `--oxygen-wire-angles` those two wire windows come from `WIRE_OXIDE_TABLE` instead: the trailing face is wetting at 0–50 ppm and non-wetting from 100 ppm up (receding 90°–120°, advancing 125°–150°). The plate window is left at its scalar values. The two windows meet through a cosine blend of width `wireSectorBlend` (default 30°) centred on `wireSectorHalfAngle` (default 90°, so the trailing half of the wire). Inside either window the head-frame sink is unchanged, so a pinned kink stays at a fixed height while melt can still flow underneath. Off, or with the entries absent, the wire line uses one window all the way around.

As the metal at the line freezes, the window opens and the target velocity becomes the substrate velocity, so a solidified bead can leave with the plate. Fully solid cells are still owned by the mushy-zone sink; the contact sink does not replace it. `contactState` 5/6/7/8 are the wire line; `contactSupport` is 2 on those cells. The contact-line file appends `nWire`, pin/advance/recede counts, `zWireMax`, `zWireMin` and `thetaMeanWire`.

The wire cavity is not required to be a closed pore. After the atmosphere flood, gas that touches the unmelted wire, lies below `zWireMax`, and sits in the trailing sector (default half-angle 110° about +x, out to `cavityOuter`) is the wake. If every cell of that component is enclosed, the status is closed; if any cell still reaches the atmosphere, it is open; both at once is mixed. Open gas is not locked. Volume, depth below the contact line, and the downstream extent are written to `postProcessing/wireCavity/wireCavity.dat`. `cavityMarker` is 1 (open) or 2 (closed). Half-domain volumes are not mirrored. The report needs a wire contact line, so `--wire-cavity` is tied to `--pin-wire`.

`--laser-config triple` places three beams from lists (`--beam-azimuths`, `--beam-inclinations`, `--beam-powers`, `--beam-radii-each`, `--beam-aim-radii`, `--beam-aim-heights`). Each ray is marched from the top of the domain along the beam. The power goes into the first cell with `alpha >= alphaHit` (default 0.5). Metal further along that ray is shadowed. The hit is therefore the free surface on the ray: a bead that rises into the beam takes the power, and the original plate receives it only while the ray is still clear. The rays are parallel, so a higher surface also meets the ray further toward the source. `LaserHit:` logs the power-weighted hit height of each beam. The baseline track aims the three axes (60°, −60°, 180°) so each meets the plate about 0.70 mm from the wire axis: the 0.26 mm spot is mostly on the substrate, and the inner wing still meets the wire. The Gao et al. configs are unchanged unless those lists are passed. See README section "Running on a workstation".

### Oxygen-dependent surface tension and contact angle

Off unless `surfaceTension { oxygenDependent true; }` (generate with `--oxygen-ppm`). The linear law and the scalar contact angles are then left as they were.

Uniform melt oxygen `chamberOxygenPpm` (ppm by weight) sets the Sahoo activity `a_O = ppm × 10⁻⁴` wt%. There is no Sieverts solve and no separate oxide-phase field: the ppm is a stand-in for the chamber, and the angle table is a stand-in for the oxide film.

```
sigma = sigma_m - A (max(T, T_m) - T_m) - R T Gamma_s ln(1 + k1 a_O exp(-dH0/(R T)))
```

with `T` in the adsorption term also evaluated at `max(T, T_m)`. `sigma_m`, `A` and `T_m` default to the alloy `sigma`, `-dSigmadT` and `Tref` (316L: 1.75 N/m, 4.3×10⁻⁴ N/m/K, 1723 K). Fe–O adsorption defaults are Sahoo, DebRoy and McNallan, Metall. Trans. B 19B (1988) 483–491 (`Gamma_s = 2.03×10⁻⁵ mol/m²`, `k1 = 0.0138`, `dH0 = −1.463×10⁵ J/mol`), the Belton isotherm (Metall. Trans. B 7B (1976) 35). At 1723 K, `dsigma/dT` is still negative at 10 ppm and positive from 100 ppm upward (see README). Marangoni uses that derivative, so the tangential stress reverses with it.

`oxygenAngleTable` is interpolated linearly in ppm for the plate and wire windows. The shipped knots are placeholders (10 ppm recovers 20°/90° and 25°/70°; 1000 ppm is 50°/130° and 58°/130°). Freezing still opens the active window to `[0, π]`.

### Oxide skin (`--oxide-skin`)

Off unless `oxideSkin { enabled true; }`. This is a membrane on the trailing face of the wire (+x, between `zMin` and `zMax`, within `gapThreshold` of the wire radius), separate from the contact-angle table. Oxygen sets the strength: `min(chamberOxygenPpm / ppmRef, 1)` when `oxygenDependent` is true, and full strength when the skin is enabled without that model. At 0 ppm the skin is off. The settle window does not scale it.

Two terms enter the momentum equation. Cells with `|grad alpha| h > 0.25` carry an implicit interfacial viscosity `muSkin` (default 20 Pa·s). Every cell in the shell carries a damper `Kskin` (default 1×10¹⁴ kg/m³/s). The target velocity is the tangential projection `U − (U·n)n`, so the radial part is removed. A scalar implicit coefficient cannot damp one direction alone, and at this `Kskin` the tangential part does not drift either: the shell stays put. Unmelted wire still follows the feed, because the mushy sink there is larger. A gap that opens past `gapThreshold` (default 0.10 mm) is no longer inside the shell. The log line is `OxideSkin:`. On the 19 µm neck those defaults hold a painted 0.05 mm trailing film; `Kskin` of 1×10¹² does not, and 200 Pa·s collapses the time step.

`growth false`, which is what a dictionary does when the key is absent, applies that strength from the first step. `growth true` (what `--oxide-skin` writes when `--oxide-skin-length-tau` is omitted) starts the coverage at 0. Exposed trailing cells, gas or an interface cell, gain coverage at `(ppm/ppmRef) * (feed/feedRef) / tau`, and that coverage is advected with the wire feed. `tau` defaults to 0.5 ms and `feedRef` to 20 mm/s, so 300 ppm at 20 mm/s reaches full strength in 0.5 ms, 50 ppm in about 3 ms, and 28 mm/s in about 0.36 ms. The damper and the viscosity then scale with `min(coverage, 1)` only. The advection scheme is `div(phiOxide,oxideFilm) Gauss upwind`.

`lengthTau` greater than zero turns growth off and limits the membrane to a length `feed × lengthTau` below `zMouth` (default 1.20 mm). The strength is still the ppm factor, on from the first step. The oxidised length is what can change with feed.

`--oxide-skin-surface` writes `surface true` and leaves growth off. Coverage starts at 0, is advected with the mixture flux, and grows at `(ppm/ppmRef)/tau` on free-surface cells (`tau` 1 ms). It is cleared off the interface. The damper and the viscosity then follow that coverage, and only where gas faces the trailing wire, with no fixed z window. A wetted neck has no gas film, so the skin does not lock it.

### Gas cavity (`--gas-cavity`)

Off unless `gasCavity { enabled true; }`. This is separate from the oxide skin. `pSupport` is applied like the recoil force, `p * snGrad(alpha)`, only on interfaces whose gas side faces the wire and only while that gas is within `gapMax` of the wire. `qRef` is a gas volume flux at the trailing triple line, in a band below the contact. It scales with `(ppm/ppmRef) * (feed/feedRef)`, is a metal-fraction sink in those cells, and is a volume source in the pressure equation. The z limits are a cap. The log line is `GasCavity:`.

A pinch-off of the wake is an increase of the entrapment count (`PinchOff:`). The wire cavity itself becoming closed is `CavityClosure:`. Neither is resolved on the 150 µm mesh; `--wire-refine 3 --wire-refine-z` is the optional ~19 µm box, and it is a much longer run (README).

### Wire-wall drag (`wireDrag`, patch `wireWall`)

Off unless `wireDrag { enabled true; }` and the cut-out wire wall carries `pinnedAlphaContactAngle` on `alpha.metal` and `partialSlip` on `U`. The mesh does not move. `partialSlip`'s `refValue` is the feed velocity.

`pinnedAlphaContactAngle` reads `thetaA` and `thetaR` in degrees, through the metal. The apparent angle is `acos(nHat·nf)`. Inside the window the boundary returns that angle, so the contact-angle correction does not rotate the interface normal and there is no Young force. Outside the window the angle is clamped to the nearer limit and the line can slip. This is the hysteresis pin. A fixed `constantAlphaContactAngle` is a different condition: it always drives the line to one angle, so the line slides rather than staying stuck to the wall.

`wireWallDrag` then runs after the internal contact-line pass. The contact is the free-surface line, not the whole wetted wall: the highest trailing face that is still metal, and the 0.20 mm band under it. Inside the window a face in that band is no-slip (`valueFraction` 1) and `Kcontact` (default `1e12` kg/m³/s) holds the interface cell on the feed velocity. Viscous diffusion from the wall does not cross a cell in a capillary step, so the sink is what carries the line down with the wire. Outside the window `valueFraction = Δ/(Δ+slipNear)` (`slipNear` default 50 µm) and `Kcontact` stays 0, so the clamped angle can slide the line. Every other wall face uses `slipFar` (default 1 mm), so the moving wire does not pump the pool. The log line is `WireDrag:` with the pinned-face count, `zWet` and the z range of the pinned band. Oxygen enters by widening that window and, when Sahoo–Belton is on, by lowering `sigma`. The internal `pinWire` model is a different mechanism and stays off for this wall.

### Imposed line pin (`linePin`)

Off unless `linePin { enabled true; }`. This is a prescribed material point, separate from `wireDrag`. On the first step the solver records the highest metal on the trailing face within `nCells` of the wire. After that the contact height is `z0 + feed_z * t`. Inside that shell, from just below the moving line up to `z0`, alpha is restored toward gas above the line and metal below it, and the cell velocity is restored toward the feed. Liquid removed from a shell cell is added to the next cell outward, and liquid added to a shell cell is taken from that neighbour, so the constraint moves the interface without deleting the coating. The first cell outside the gas part of the shell is restored toward metal with the same hold fraction, which keeps that displaced coating beside the line. Cells beyond it, and the pool below the line, are not constrained. `s = min(ppm/ppmRef, 1)` is the fraction of that error removed after every alpha solve, and the fraction of `Kpin`. At `ppmRef` (default 300) the shell is overwritten. The log line is `LinePin:`. Sahoo–Belton `sigma` still depends on ppm when that model is on. The shell and that one neighbouring cell are the imposed pin. Depth of the shell follows the feed. Taper past the neighbouring cell is the free surface. The bare-neck smokes set `nCells` to 2.

### Trailing oxide angle (`oxideAngle`)

Off unless `oxideAngle { enabled true; }`. This is not `oxideSkin` and not `linePin`. Coverage starts at 0. On the trailing side of the wire, above `zMin`, it relaxes toward `sCap = min(ppm/ppmRef, 1)` in the first cell outside the wire and in cells with `alpha < 0.9` out to `nCells`. Buried metal farther from the wire relaxes toward 0. The field is not advected. The timescale is `tau` (default 1 ms).

Coverage is generated by that exposure law. The constitutive map is imposed. `pinnedAlphaContactAngle` reads optional `thetaRox` and `thetaAox` and blends the clean window toward them with the adjacent-cell coverage. `sigma` is multiplied by `max(1 - sigmaDrop*coverage, sigmaFloor)` after the Sahoo–Belton evaluation. The tangential force from that oxide part of `grad(sigma)` is `Foxide`; thermal Marangoni is unchanged and still follows the settle ramp. On trailing `wireWall` faces, `partialSlip` `valueFraction` equals coverage and `refValue` stays the feed, so a covered face moves with the wire. `Kcontact` is not set, and alpha is not overwritten. The free surface is generated. The log line is `OxideAngle:`. The bare-neck smokes use a clean window of 10/40, an oxide window of 40/140, `sigmaDrop` 0.5, `ppmRef` 300 and `nCells` 3. `linePin` and `wireDrag` stay off. Those smokes are in `results/calibration/README.md`: the neck goes bare, and a thin trailing slit does not form.

## Local GUI (Windows)

A tkinter control panel lives in `gui/`. On the PC open:

`C:\Users\dukyo\laser_wire_ded\gui\launch_gui.bat`

See `gui/README.md` for parameters, presets, and how jobs are launched through WSL.
