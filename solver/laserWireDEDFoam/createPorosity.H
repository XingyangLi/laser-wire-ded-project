// ---------------------------------------------------------------------------
// Porosity (meltProperties/porosity, default OFF).
//
// The VOF field already carries shielding gas. A pore is gas that has lost
// its connection to the atmosphere (top, far-field, outlet, wire inlet):
//
//   * gasEntrapment  — enclosed gas whose shell is not a near-surface
//                      lack-of-fusion gap and not a hot keyhole cavity
//                      (surface fold-over, a collapsed depression that is
//                      no longer hot, a subsurface bubble).
//   * lackOfFusion   — enclosed gas sitting on the substrate surface and
//                      covered by deposited / above-plate metal. This is
//                      the gap left when the contact line pins before the
//                      bead wets the plate.
//   * keyhole        — enclosed gas under a metal cap whose neighbourhood
//                      is still near boiling or carries recoil pressure.
//                      Recoil in this solver depresses the surface but does
//                      not remove mass; a pore is tagged keyhole only when
//                      that hot cavity has actually closed over.
//
// The shell liquid fraction is the mean liquid fraction of the metal cells
// that share a face with the gas. Below flLock the pore is locked: alpha is
// held at or below alphaLock so numerical diffusion cannot fill it. A shell
// that remelts (mean fl >= flLock) is released and the VOF may vent it.
// Evaporation still does not remove mass; keyhole tagging does not invent
// vapour. Multi-wire cases are unchanged unless the dictionary is enabled.
// ---------------------------------------------------------------------------

const dictionary porosityDict(meltProperties.subOrEmptyDict("porosity"));
const bool porosityEnabled = porosityDict.getOrDefault<bool>("enabled", false);
const scalar porAlphaOpen = porosityDict.getOrDefault<scalar>("alphaOpen", 0.50);
const scalar porAlphaLock = porosityDict.getOrDefault<scalar>("alphaLock", 0.05);
const scalar porFlLock = porosityDict.getOrDefault<scalar>("flLock", 0.35);
const scalar porLofBand = porosityDict.getOrDefault<scalar>("lofBand", 5e-4);
const scalar porKeyholeTfrac = porosityDict.getOrDefault<scalar>("keyholeTfrac", 0.85);
const scalar porKeyholeDepth = porosityDict.getOrDefault<scalar>("keyholeDepth", 2e-4);
const scalar porKeyholeRecoil = porosityDict.getOrDefault<scalar>("keyholeRecoil", 5000.0);
const label porMinCells = porosityDict.getOrDefault<label>("minCells", 1);
const scalar porZSub = porosityDict.getOrDefault<scalar>("zSubstrate", 0.0);
const scalar porTboil = porosityDict.getOrDefault<scalar>
(
    "Tboil",
    meltProperties.subOrEmptyDict("vaporisation").getOrDefault<scalar>("Tboil", 3090.0)
);
const label porInterval = porosityDict.getOrDefault<label>
(
    "interval",
    meltProperties.subOrEmptyDict("statistics").getOrDefault<label>("interval", 10)
);

// poreMarker: 1 = solidification-locked pore. poreType: 1 entrapment,
// 2 lack-of-fusion, 3 keyhole (0 = not a locked pore).
volScalarField poreMarker
(
    IOobject
    (
        "poreMarker",
        runTime.timeName(),
        mesh,
        IOobject::READ_IF_PRESENT,
        IOobject::AUTO_WRITE
    ),
    mesh,
    dimensionedScalar(dimless, Zero)
);

volScalarField poreType
(
    IOobject
    (
        "poreType",
        runTime.timeName(),
        mesh,
        IOobject::READ_IF_PRESENT,
        IOobject::AUTO_WRITE
    ),
    mesh,
    dimensionedScalar(dimless, Zero)
);

Info<< "Porosity (enclosed-gas lock): " << (porosityEnabled ? "on" : "off");
if (porosityEnabled)
{
    Info<< "  alphaOpen " << porAlphaOpen
        << "  alphaLock " << porAlphaLock
        << "  flLock " << porFlLock
        << "  lofBand " << porLofBand << " m"
        << "  keyhole T/Tboil " << porKeyholeTfrac
        << " or pRecoil " << porKeyholeRecoil << " Pa";
}
Info<< nl << endl;
