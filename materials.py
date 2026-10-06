"""Material presets for laser wire DED (constant-property approximations).

rho is a single effective (solid/liquid average) density because both VOF phases are
incompressible; cp is an effective average over the solid/liquid range; k is given for
solid (effective, high-temperature average) and liquid.

Sources
-------
Invar36 (Fe-36Ni):
  * density 8050 kg/m3, cp 515 J/kg/K, k 10.15 W/m/K (room temperature), melting point
    ~1427 C (1700 K): Carpenter Technology, "Invar 36 alloy" technical datasheet; also
    Special Metals / Aperam Invar 36 datasheets. Effective high-temperature values (k_s 15,
    cp 600) are our estimates from the Fe-Ni trend; please verify against your wire supplier.
  * solidus/liquidus 1700/1725 K: Fe-Ni binary phase diagram at 36 wt.% Ni (narrow
    freezing range ~20-30 K) - approximate.
  * latent heat 2.65e5 J/kg: rule of mixtures of Fe (2.47e5) and Ni (2.98e5).
  * surface tension 1.84 N/m at liquidus, dsigma/dT = -3.5e-4 N/m/K: Fe-Ni liquid alloys,
    J. Brillo & I. Egry, J. Mater. Sci. 40 (2005) 2213-2216 (oscillating drop, Fe-Ni series)
    - interpolated at 36 wt.% Ni; very sensitive to S/O content.
  * viscosity ~5e-3 Pa s (Fe 5.5, Ni 4.9 mPa s at Tm); Tboil, Lv, M: mole-fraction mixture of Fe/Ni.
SS304 (AISI 304 stainless steel, substrate):
  * K.C. Mills, "Recommended values of thermophysical properties for selected commercial
    alloys", Woodhead (2002), 304 stainless chapter: Tsol 1670-1673 K, Tliq 1727 K,
    L 2.6e5 J/kg, rho 7900 (RT) -> 6900 (liquid), k 14.9 (RT) -> ~30 (near Tm), cp 500 -> 800;
    surface tension ~1.8 N/m, dsigma/dT ~ -4e-4 N/m/K (S-dependent).
IN718:
  * as in Gao et al., Int. J. Mach. Tools Manuf. 194 (2024) 104089, Table 1 (Flow-3D database):
    rho 8190 (298 K) / 7160 (1873 K), cp 435 (298 K), k 8.9 (298 K), Tsol 1533 K, Tliq 1609 K,
    L 2.4e5 J/kg, sigma 1.827 N/m (1628 K), dsigma/dT -4.43e-4 N/m/K, mu 4.42e-3 Pa s,
    absorptivity 0.42 (calibrated, three diode lasers). Effective cp/k: our averages.
316L, Ti6Al4V: Mills (2002) and typical melt-pool CFD values.
Pure Fe and pure Ni (strand materials of the Fe/Ni multi-strand wire, multi-component model):
  * melting points 1811 K (Fe), 1728 K (Ni); latent heats 13.81 kJ/mol = 2.47e5 J/kg (Fe) and
    17.48 kJ/mol = 2.98e5 J/kg (Ni); boiling points 3134 K / 3186 K, Lv 340 / 375 kJ/mol
    (6.09e6 / 6.38e6 J/kg): NIST-JANAF Thermochemical Tables, 4th ed. (M.W. Chase, J. Phys. Chem.
    Ref. Data Monograph 9, 1998); CRC Handbook of Chemistry and Physics.
  * cp: effective mean of the solid from 300 K to Tm incl. the Curie/alpha-gamma-delta peaks,
    Fe ~700 J/kg/K (liquid 824), Ni ~600 J/kg/K (liquid ~730): from the JANAF enthalpy
    H(Tm) - H(298) / (Tm - 298) (our averaging).
  * thermal conductivity, solid effective high-T mean: Fe ~30 W/m/K (k(1000 K) = 32.6,
    k(1200 K) = 28.2), Ni ~75 W/m/K (k(1000 K) = 71.8, k(1400 K) = 82.6): C.Y. Ho, R.W. Powell,
    P.E. Liley, "Thermal conductivity of the elements", J. Phys. Chem. Ref. Data 1 (1972) 279;
    liquid at Tm: Fe ~38, Ni ~60 W/m/K (P.N. Quested, ASM Handbook Vol. 15 (2008),
    "Thermophysical properties of metals"; K.C. Mills, B.J. Monaghan, B.J. Keene, Int. Mater.
    Rev. 41 (1996) 209).
  * density RT 7874 / 8908, liquid at Tm 7030 / 7810 kg/m3; viscosity at Tm 5.5 / 4.9 mPa s:
    M.J. Assael et al., J. Phys. Chem. Ref. Data 35 (2006) 285 (Fe) and 41 (2012) 033101 (Ni).
  * surface tension, oscillating drop: sigma = (2450 - 0.2927 T) x_Fe + (2180 - 0.2381 T) x_Ni
    (+ excess term) mN/m: J. Brillo & I. Egry, J. Mater. Sci. 40 (2005) 2213 ->
    Fe 1.920 N/m at 1811 K, dsigma/dT = -2.93e-4; Ni 1.769 N/m at 1728 K, dsigma/dT = -2.38e-4.
  * absorptivity: flat-surface normal-incidence values at ~1 um are Ni 0.27 and stainless 0.34
    (C.D. Boley, S.A. Khairallah, A.M. Rubenchik, Appl. Opt. 54 (2015) 2477); Fe is close to
    stainless. We scale the model's calibrated 0.42 (IN718, Gao et al. 2024) by these ratios:
    Fe 0.42, Ni 0.34 (estimates; not measured for this diode wavelength / surface state).
  * pure metals melt isothermally; the model needs a finite freezing range, so a 10 K
    numerical range below Tm is used (Fe 1801-1811 K, Ni 1718-1728 K).
Fe-Ni phase diagram (liquidus / solidus vs. wt.% Ni, FE_NI_LIQUIDUS):
  * L.J. Swartzendruber, V.P. Itkin, C.B. Alcock, "The Fe-Ni (iron-nickel) system",
    J. Phase Equilib. 12 (1991) 288 (peritectic L + delta -> gamma at 1514 C, ~4.5 wt.% Ni;
    shallow liquidus minimum ~1436 C near 60-68 wt.% Ni);
  * DSC solidus/liquidus [C] of 10/20/40/60/80/90 wt.% Ni: 1498/1504, 1479/1489, 1445/1452,
    1437/1439, 1443/1445, 1448/1450 (thermodynamic re-assessment of Fe-Ni, Tetsu-to-Hagane
    112(6) (2026), TETSU-2025-072, with data of M.-K. Paek et al., JOM 73 (2021) 679).
  * the table imposes a minimum 8 K freezing range (numerical); Invar 36 (36 wt.% Ni) falls
    at ~1724/1731 K, close to the datasheet range used for the Invar36 preset (1700/1725 K).
Absorptivity: default 0.42 for the paper's diode-laser configuration (calibrated for IN718 in
Gao et al. 2024); no measured values for Invar/304 at that wavelength were available - adjust.
"""

MATERIALS = {
    "Invar36": dict(
        rho=7700.0, cp=600.0, k_solid=15.0, k_liquid=30.0,
        Tsol=1700.0, Tliq=1725.0, L=2.65e5, mu=5.0e-3,
        sigma=1.84, dsigma_dT=-3.5e-4,
        Tboil=3150.0, Lv=6.2e6, M=0.0569, beta=1.0e-4, emissivity=0.4,
        absorptivity=0.42, Ni_wt=36.0, rho_rt=8050.0,
    ),
    "SS304": dict(
        rho=7500.0, cp=650.0, k_solid=22.0, k_liquid=30.0,
        Tsol=1673.0, Tliq=1727.0, L=2.6e5, mu=6.0e-3,
        sigma=1.80, dsigma_dT=-4.0e-4,
        Tboil=3090.0, Lv=7.45e6, M=0.0558, beta=1.5e-4, emissivity=0.4,
        absorptivity=0.42,
    ),
    "316L": dict(
        rho=7300.0, cp=650.0, k_solid=22.0, k_liquid=30.0,
        Tsol=1658.0, Tliq=1723.0, L=2.7e5, mu=6.0e-3,
        sigma=1.75, dsigma_dT=-4.3e-4,
        Tboil=3090.0, Lv=7.45e6, M=0.0558, beta=1.5e-4, emissivity=0.4,
        absorptivity=0.35,
    ),
    "Ti6Al4V": dict(
        rho=4200.0, cp=750.0, k_solid=18.0, k_liquid=30.0,
        Tsol=1878.0, Tliq=1928.0, L=2.86e5, mu=4.0e-3,
        sigma=1.52, dsigma_dT=-2.8e-4,
        Tboil=3315.0, Lv=9.83e6, M=0.0446, beta=1.1e-4, emissivity=0.4,
        absorptivity=0.40,
    ),
    "IN718": dict(
        rho=7600.0, cp=600.0, k_solid=20.0, k_liquid=28.0,
        Tsol=1533.0, Tliq=1609.0, L=2.4e5, mu=4.42e-3,
        sigma=1.827, dsigma_dT=-4.43e-4,
        Tboil=3190.0, Lv=6.4e6, M=0.0587, beta=1.3e-4, emissivity=0.4,
        absorptivity=0.42,
    ),
    # pure elements for the multi-strand Fe/Ni wire (multi-component model); 'Ni_wt' = Ni content [wt.%]
    "Fe": dict(
        rho=7450.0, rho_rt=7874.0, cp=700.0, k_solid=30.0, k_liquid=38.0,
        Tsol=1801.0, Tliq=1811.0, L=2.47e5, mu=5.5e-3,
        sigma=1.920, dsigma_dT=-2.93e-4,
        Tboil=3134.0, Lv=6.09e6, M=0.05585, beta=1.2e-4, emissivity=0.4,
        absorptivity=0.42, Ni_wt=0.0,
    ),
    "Ni": dict(
        rho=8360.0, rho_rt=8908.0, cp=600.0, k_solid=75.0, k_liquid=60.0,
        Tsol=1718.0, Tliq=1728.0, L=2.98e5, mu=4.9e-3,
        sigma=1.769, dsigma_dT=-2.38e-4,
        Tboil=3186.0, Lv=6.38e6, M=0.05869, beta=1.2e-4, emissivity=0.4,
        absorptivity=0.34, Ni_wt=100.0,
    ),
}

ARGON = dict(rho=1.623, mu=2.27e-5, cp=520.3, k=0.0177)

# Gao et al., Nat. Commun. (2026), PMC13385772, Table S1 (uPrinter, Additec; triple diode lasers,
# 0.9 mm wire fed coaxially, substrate translated). '+' = two laser spots in front of the wire,
# one behind; '-' (reverse, "R") = one in front, two behind.
PAPER_CONFIGS = {
    "normal":         dict(power=600.0, scan_speed=6.7e-3, wire_feed_speed=11.4e-3, direction="+"),
    "lof":            dict(power=400.0, scan_speed=10.0e-3, wire_feed_speed=17.0e-3, direction="+"),
    "transitional_r": dict(power=600.0, scan_speed=5.8e-3, wire_feed_speed=29.0e-3, direction="-"),
}

# Fe-Ni binary liquidus/solidus [K] vs. wt.% Ni (see sources above); (wtNi, Tsolidus, Tliquidus)
FE_NI_LIQUIDUS = [
    (0.0, 1801.0, 1811.0),     # pure Fe (Tm 1811 K; 10 K numerical range)
    (4.5, 1784.0, 1789.0),     # peritectic L + delta -> gamma, 1514 C
    (10.0, 1771.0, 1777.0),    # DSC 1498 / 1504 C
    (20.0, 1752.0, 1762.0),    # DSC 1479 / 1489 C
    (40.0, 1718.0, 1725.0),    # DSC 1445 / 1452 C
    (60.0, 1704.0, 1712.0),    # DSC 1437 / 1439 C (minimum), widened to 8 K
    (80.0, 1710.0, 1718.0),    # DSC 1443 / 1445 C, widened
    (90.0, 1715.0, 1723.0),    # DSC 1448 / 1450 C, widened
    (100.0, 1718.0, 1728.0),   # pure Ni (Tm 1728 K; 10 K numerical range)
]
