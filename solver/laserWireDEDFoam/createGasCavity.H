// ---------------------------------------------------------------------------
// Gas cavity on the trailing wire face (meltProperties/gasCavity, default OFF).
//
// Two optional terms, both scaled by min(chamberOxygenPpm/ppmRef, 1):
//
//   * pSupport: a recoil-style face force p * snGrad(alpha) on interfaces
//     whose gas side faces the wire, and only while that gas is within
//     gapMax of the wire. A few kPa pushes the metal faces apart. The
//     force drops out once the gap is wider than gapMax.
//   * qRef: a gas volume flux (m/s) at the trailing triple line, times
//     (feed/feedRef). It is a volume source in the pressure equation and
//     a sink of metal fraction, so shielding gas / vapour is added at the
//     wire and the cavity can grow until surface tension vents it.
//
// The z window is only a cap. It is not the slit depth.
// ---------------------------------------------------------------------------

const dictionary gasCavityDict(meltProperties.subOrEmptyDict("gasCavity"));
const bool gasCavityEnabled = gasCavityDict.getOrDefault<bool>("enabled", false);
const scalar gasCavityP0 = gasCavityDict.getOrDefault<scalar>("pSupport", 0.0);
const scalar gasCavityQ0 = gasCavityDict.getOrDefault<scalar>("qRef", 0.0);
const scalar gasCavityGap = gasCavityDict.getOrDefault<scalar>("gapMax", 0.10e-3);
const scalar gasCavityZ0 = gasCavityDict.getOrDefault<scalar>("zMin", 0.20e-3);
const scalar gasCavityZ1 = gasCavityDict.getOrDefault<scalar>("zMax", 1.80e-3);
const scalar gasCavityPpmRef = max
(
    gasCavityDict.getOrDefault<scalar>("ppmRef", 300.0),
    SMALL
);
const scalar gasCavityFeedRef = max
(
    gasCavityDict.getOrDefault<scalar>("feedRef", 0.020),
    SMALL
);
const scalar gasCavityBand = gasCavityDict.getOrDefault<scalar>("band", 0.20e-3);
const label gasCavityInterval = gasCavityDict.getOrDefault<label>
(
    "interval",
    contactInterval
);
label gasCavityLogIndex = -1;

scalar gasCavityStrength = 0;
if (gasCavityEnabled)
{
    gasCavityStrength =
        oxygenDependent
      ? min(max(chamberOxygenPpm/gasCavityPpmRef, scalar(0)), scalar(1))
      : scalar(1);
}

volScalarField pGasCavity
(
    IOobject
    (
        "pGasCavity",
        runTime.timeName(),
        mesh,
        IOobject::NO_READ,
        IOobject::NO_WRITE
    ),
    mesh,
    dimensionedScalar(dimPressure, Zero)
);

volScalarField gasVolumeSource
(
    IOobject
    (
        "gasVolumeSource",
        runTime.timeName(),
        mesh,
        IOobject::NO_READ,
        IOobject::NO_WRITE
    ),
    mesh,
    dimensionedScalar(dimless/dimTime, Zero)
);

if (gasCavityEnabled)
{
    Info<< "GasCavity: "
        << (gasCavityStrength > SMALL ? "on" : "off (zero strength)")
        << " strength " << gasCavityStrength
        << " p " << gasCavityStrength*gasCavityP0 << " Pa"
        << " q " << gasCavityStrength*gasCavityQ0 << " m/s"
        << " gapMax " << gasCavityGap
        << " band " << gasCavityBand
        << " z " << gasCavityZ0 << " " << gasCavityZ1
        << nl << endl;
}
