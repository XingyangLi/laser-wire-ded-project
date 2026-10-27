// ---------------------------------------------------------------------------
// Oxide skin on the trailing wire face (meltProperties/oxideSkin, default OFF).
//
// A thin oxide film is treated as a membrane on the metal/gas surface of the
// gap, so the two faces resist being squeezed together. Two terms, both zero
// outside the trailing shell (the +x side, within gapThreshold of the wire,
// between zMin and zMax):
//
//   * interfacial viscosity, -laplacian(muOxide, U), on cells where
//     |grad alpha| * h > 0.25 (the smeared interface);
//   * a Bingham-like damper of the velocity normal to the gap,
//     Sp(Koxide, U) == Koxide * U_tangential, with
//     U_tangential = U - (U·n) n and n the radial unit vector from the wire
//     axis. A scalar Sp coefficient has no cross-component coupling, so the
//     tangential velocity is held at that projection as well: with Kskin at
//     the default the shell does not drift. The damper covers every cell in
//     the shell (both metal faces and the gas between them), so the face
//     flux from a free neighbour cannot squeeze the film. The wire feed
//     still wins inside unmelted wire, where the mushy sink is larger.
//
// The shell is the thin-gap region: a cell is inside it only while its
// centre lies within gapThreshold of the wire face. A gap that opens past
// that thickness leaves the outer cells undamped.
//
// Strength is min(chamberOxygenPpm/ppmRef, 1) when Sahoo-Belton oxygen is
// on, so the ppm sets the skin, and 0 ppm leaves it off. Enabled with the
// oxygen model off, the skin is at full strength. Settle does not scale it:
// the membrane is already there at t = 0.
//
// Defaults (muSkin 20 Pa·s, Kskin 1e14 kg/m^3/s, gapThreshold 0.10 mm) are
// the pair that held a painted 0.05 mm film on the 19 um neck. Kskin 1e12
// lets the crown open by 4 ms, and 1e13 still lets the lip recede. The
// viscosity is implicit. At 200 Pa·s the step collapsed under spurious
// Courant; 20 Pa·s leaves the capillary limit in charge.
// ---------------------------------------------------------------------------

const dictionary oxideSkinDict(meltProperties.subOrEmptyDict("oxideSkin"));
const bool oxideSkinEnabled = oxideSkinDict.getOrDefault<bool>("enabled", false);
const scalar oxideSkinMu0 = oxideSkinDict.getOrDefault<scalar>("muSkin", 20.0);
const scalar oxideSkinK0 = oxideSkinDict.getOrDefault<scalar>("Kskin", 1.0e14);
const scalar oxideSkinGap = oxideSkinDict.getOrDefault<scalar>("gapThreshold", 0.10e-3);
const scalar oxideSkinZ0 = oxideSkinDict.getOrDefault<scalar>("zMin", 0.30e-3);
const scalar oxideSkinZ1 = oxideSkinDict.getOrDefault<scalar>("zMax", 1.55e-3);
const scalar oxideSkinPpmRef = max
(
    oxideSkinDict.getOrDefault<scalar>("ppmRef", 300.0),
    SMALL
);
const scalar oxideSkinAlphaGas = oxideSkinDict.getOrDefault<scalar>("alphaGas", 0.98);
const label oxideSkinInterval = oxideSkinDict.getOrDefault<label>
(
    "interval",
    contactInterval
);
label oxideSkinLogIndex = -1;

scalar oxideSkinStrength = 0;
if (oxideSkinEnabled)
{
    oxideSkinStrength =
        oxygenDependent
      ? min(max(chamberOxygenPpm/oxideSkinPpmRef, scalar(0)), scalar(1))
      : scalar(1);
}

volScalarField muOxide
(
    IOobject
    (
        "muOxide",
        runTime.timeName(),
        mesh,
        IOobject::NO_READ,
        IOobject::NO_WRITE
    ),
    mesh,
    dimensionedScalar(dimDynamicViscosity, Zero)
);

volScalarField Koxide
(
    IOobject
    (
        "Koxide",
        runTime.timeName(),
        mesh,
        IOobject::NO_READ,
        IOobject::NO_WRITE
    ),
    mesh,
    dimensionedScalar(dimDensity/dimTime, Zero)
);

// Tangential velocity kept by the damper. Equals U where the skin is off,
// so Sp(Koxide, U) - Koxide*Ukeep is zero in that cell.
volVectorField Ukeep
(
    IOobject
    (
        "Ukeep",
        runTime.timeName(),
        mesh,
        IOobject::NO_READ,
        IOobject::NO_WRITE
    ),
    U
);

if (oxideSkinEnabled)
{
    Info<< "OxideSkin: "
        << (oxideSkinStrength > SMALL ? "on" : "off (zero strength)")
        << " strength " << oxideSkinStrength
        << " mu " << oxideSkinStrength*oxideSkinMu0 << " Pa.s"
        << " K " << oxideSkinStrength*oxideSkinK0
        << " gap " << oxideSkinGap << " m"
        << " z " << oxideSkinZ0 << " " << oxideSkinZ1
        << " ppmRef " << oxideSkinPpmRef
        << " alphaGas " << oxideSkinAlphaGas
        << nl << endl;
}
