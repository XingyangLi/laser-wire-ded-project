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
// Unmelted wire is not a solid support unless pinWire is true. With pinWire,
// the melt/gas/unmelted-wire line has its own hysteresis window
// (thetaRecedingWire, thetaAdvancingWire). Inside that window the line is
// held in the head frame (wireVelocity head, the default: the kink stays at
// a fixed height while the wire feeds through it) or on the feed velocity
// (wireVelocity wire: stuck to a material point of the wire). Freezing the
// meniscus hands the line to the substrate velocity. Nothing is added to
// the momentum equation unless enabled = true.
// ---------------------------------------------------------------------------

const dictionary contactDict(meltProperties.subOrEmptyDict("contactLine"));
const bool contactEnabled = contactDict.getOrDefault<bool>("enabled", false);
const scalar contactDeg =
    constant::mathematical::pi/180.0;
scalar contactThetaR0 =
    contactDict.getOrDefault<scalar>("thetaReceding", 20.0)*contactDeg;
scalar contactThetaA0 =
    contactDict.getOrDefault<scalar>("thetaAdvancing", 90.0)*contactDeg;
const scalar contactFlPin = contactDict.getOrDefault<scalar>("flPin", 0.15);
const scalar contactFlFree = contactDict.getOrDefault<scalar>("flFree", 0.60);
const scalar contactFlSolid = contactDict.getOrDefault<scalar>("flSolid", 0.20);
const scalar contactKpin = contactDict.getOrDefault<scalar>("Kpin", 1e7);
const scalar contactGradMin = contactDict.getOrDefault<scalar>("gradMin", 0.25);
const scalar contactForceFactor = contactDict.getOrDefault<scalar>("forceFactor", 1.0);
const scalar contactZSub = contactDict.getOrDefault<scalar>("zSubstrate", 0.0);
const bool contactPinWire = contactDict.getOrDefault<bool>("pinWire", false);
scalar contactThetaRwire =
    contactDict.getOrDefault<scalar>("thetaRecedingWire", 25.0)*contactDeg;
scalar contactThetaAwire =
    contactDict.getOrDefault<scalar>("thetaAdvancingWire", 70.0)*contactDeg;

// Oxygen / oxide hysteresis. oxygenAngleTable rows are
// (ppm  thetaReceding  thetaAdvancing  thetaRecedingWire  thetaAdvancingWire)
// in degrees, linearly interpolated in ppm and clamped outside the table.
// Used only when surfaceTension/oxygenDependent is true, so the linear-sigma
// cases keep the scalar angles. The default table is a placeholder, not a
// sessile-drop measurement (see generate_case.py / README).
scalarListList contactOxygenAngles;
contactDict.readIfPresent("oxygenAngleTable", contactOxygenAngles);
auto lwdOxygenAngle = [&](const label col, const scalar fallbackDeg) -> scalar
{
    if (!oxygenDependent || contactOxygenAngles.empty()) return fallbackDeg;
    scalarList xs(contactOxygenAngles.size());
    scalarList ys(contactOxygenAngles.size());
    label nRow = 0;
    for (const scalarList& row : contactOxygenAngles)
    {
        if (row.size() <= col)
        {
            FatalErrorInFunction
                << "contactLine/oxygenAngleTable rows need 5 numbers: "
                << "ppm thetaReceding thetaAdvancing thetaRecedingWire "
                << "thetaAdvancingWire" << nl
                << "got " << row << exit(FatalError);
        }
        xs[nRow] = row[0];
        ys[nRow] = row[col];
        ++nRow;
    }
    for (label i = 1; i < nRow; ++i)
    {
        const scalar xv = xs[i];
        const scalar yv = ys[i];
        label j = i;
        while (j > 0 && xs[j - 1] > xv)
        {
            xs[j] = xs[j - 1];
            ys[j] = ys[j - 1];
            --j;
        }
        xs[j] = xv;
        ys[j] = yv;
    }
    const scalar x = chamberOxygenPpm;
    if (x <= xs[0]) return ys[0];
    if (x >= xs[nRow - 1]) return ys[nRow - 1];
    for (label i = 1; i < nRow; ++i)
    {
        if (x <= xs[i])
        {
            const scalar den = max(xs[i] - xs[i - 1], SMALL);
            const scalar f = (x - xs[i - 1])/den;
            return ys[i - 1] + f*(ys[i] - ys[i - 1]);
        }
    }
    return ys[nRow - 1];
};
if (oxygenDependent && contactOxygenAngles.size())
{
    contactThetaR0 = lwdOxygenAngle(1, contactThetaR0/contactDeg)*contactDeg;
    contactThetaA0 = lwdOxygenAngle(2, contactThetaA0/contactDeg)*contactDeg;
    contactThetaRwire = lwdOxygenAngle(3, contactThetaRwire/contactDeg)*contactDeg;
    contactThetaAwire = lwdOxygenAngle(4, contactThetaAwire/contactDeg)*contactDeg;
}
const word contactWireVelocity(contactDict.getOrDefault<word>("wireVelocity", "head"));
// head: pinned wire line is stationary in the lab/head frame (default).
// wire: pinned wire line moves at the instantaneous feed velocity.
const bool contactWireHeadFrame = (contactWireVelocity != "wire");
// Highest / lowest wire-line cell this step (-GREAT / GREAT if there is none).
// The cavity report reads these after the contact-line pass.
scalar contactWireZMax = -GREAT;
scalar contactWireZMin = GREAT;
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

// Velocity the contact sink drives toward. Equals Usolid except on a molten
// wire line (see contactLine.H). Unused while Kcontact is zero.
volVectorField Ucontact
(
    IOobject
    (
        "Ucontact",
        runTime.timeName(),
        mesh,
        IOobject::NO_READ,
        IOobject::NO_WRITE
    ),
    Usolid
);

// 0 none, 1 hysteresis pin, 2 solidification pin, 3 advancing, 4 receding
// wire line: 5 hysteresis pin, 6 solidification pin, 7 advancing, 8 receding
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

// 0 none, 1 substrate or deposit, 2 unmelted wire
volScalarField contactSupport
(
    IOobject
    (
        "contactSupport",
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
    if (contactPinWire)
    {
        Info<< nl << "    wire line: thetaR " << contactThetaRwire/contactDeg
            << " deg  thetaA " << contactThetaAwire/contactDeg
            << " deg  velocity " << (contactWireHeadFrame ? "head" : "wire");
    }
    else
    {
        Info<< "  (unmelted wire is not a support)";
    }
    if (oxygenDependent && contactOxygenAngles.size())
    {
        Info<< nl << "    oxygen angles at " << chamberOxygenPpm
            << " ppm from oxygenAngleTable (placeholder unless you replaced it)";
    }
    else if (oxygenDependent)
    {
        Info<< nl << "    oxygen model on, no oxygenAngleTable: scalar angles kept";
    }
}
Info<< nl << endl;
