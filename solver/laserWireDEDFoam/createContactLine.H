// ---------------------------------------------------------------------------
// Substrate contact-line pinning (meltProperties/contactLine, default OFF).
//
// The plate is meshed metal, not a wall patch, so the bead/pool triple line
// is an internal metal/gas/solid intersection. A wall contact-angle BC on
// `bottom` would not see it. This model acts on that internal line:
//
//   * While the metal at the line is liquid, the apparent contact angle
//     (through the metal) is free inside [thetaReceding, thetaAdvancing].
//     Inside that window the unbalanced Young force is zero and a momentum
//     sink holds the line on the substrate velocity (pinning / hysteresis).
//     Outside it, a localised Young force restores the angle to the nearer
//     limit (advance at thetaAdvancing, recede at thetaReceding).
//   * As the metal at the line freezes, the window opens linearly toward
//     [0, 180 deg]. Fully solid metal is pinned at whatever angle it froze
//     at, and is carried with the substrate. That is the deposited-bead pin.
//
// Unmelted wire is not a solid support, so the feed is left alone.
// Nothing is added to the momentum equation unless enabled = true.
// ---------------------------------------------------------------------------

const dictionary contactDict(meltProperties.subOrEmptyDict("contactLine"));
const bool contactEnabled = contactDict.getOrDefault<bool>("enabled", false);
const scalar contactDeg =
    constant::mathematical::pi/180.0;
const scalar contactThetaR0 =
    contactDict.getOrDefault<scalar>("thetaReceding", 20.0)*contactDeg;
const scalar contactThetaA0 =
    contactDict.getOrDefault<scalar>("thetaAdvancing", 90.0)*contactDeg;
const scalar contactFlPin = contactDict.getOrDefault<scalar>("flPin", 0.15);
const scalar contactFlFree = contactDict.getOrDefault<scalar>("flFree", 0.60);
const scalar contactFlSolid = contactDict.getOrDefault<scalar>("flSolid", 0.20);
const scalar contactKpin = contactDict.getOrDefault<scalar>("Kpin", 1e7);
const scalar contactGradMin = contactDict.getOrDefault<scalar>("gradMin", 0.25);
const scalar contactForceFactor = contactDict.getOrDefault<scalar>("forceFactor", 1.0);
const scalar contactZSub = contactDict.getOrDefault<scalar>("zSubstrate", 0.0);
const label contactInterval = contactDict.getOrDefault<label>
(
    "interval",
    meltProperties.subOrEmptyDict("statistics").getOrDefault<label>("interval", 10)
);

volScalarField Kcontact
(
    IOobject
    (
        "Kcontact",
        runTime.timeName(),
        mesh,
        IOobject::NO_READ,
        IOobject::NO_WRITE
    ),
    mesh,
    dimensionedScalar(dimDensity/dimTime, Zero)
);

volVectorField Fcontact
(
    IOobject
    (
        "Fcontact",
        runTime.timeName(),
        mesh,
        IOobject::NO_READ,
        IOobject::NO_WRITE
    ),
    mesh,
    dimensionedVector(dimForce/dimVolume, Zero)
);

// 0 none, 1 hysteresis pin, 2 solidification pin, 3 advancing, 4 receding
volScalarField contactState
(
    IOobject
    (
        "contactState",
        runTime.timeName(),
        mesh,
        IOobject::READ_IF_PRESENT,
        IOobject::AUTO_WRITE
    ),
    mesh,
    dimensionedScalar(dimless, Zero)
);

Info<< "Contact-line pinning (hysteresis + solidification): "
    << (contactEnabled ? "on" : "off");
if (contactEnabled)
{
    Info<< "  thetaR " << contactThetaR0/contactDeg
        << " deg  thetaA " << contactThetaA0/contactDeg
        << " deg  Kpin " << contactKpin
        << "  flPin/flFree " << contactFlPin << "/" << contactFlFree;
}
Info<< nl << endl;
