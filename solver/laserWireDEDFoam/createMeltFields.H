// ---------------------------------------------------------------------------
// laserWireDEDFoam : energy, melting, wire feed, laser, surface physics
// Included from createFields.H after the mixture/rho have been created.
// All model constants are read from constant/meltProperties.
// ---------------------------------------------------------------------------

Info<< "Reading meltProperties\n" << endl;

IOdictionary meltProperties
(
    IOobject
    (
        "meltProperties",
        runTime.constant(),
        mesh,
        IOobject::MUST_READ_IF_MODIFIED,
        IOobject::NO_WRITE
    )
);

// --- Thermal properties (rho comes from transportProperties)
const dictionary& metalThermoDict = meltProperties.subDict("metal");
const dictionary& gasThermoDict   = meltProperties.subDict("gas");

const dimensionedScalar cp1("cp", dimSpecificHeatCapacity, metalThermoDict);
const dimensionedScalar k1("k", dimPower/dimLength/dimTemperature, metalThermoDict);
const scalar k1Liquid = metalThermoDict.getOrDefault<scalar>("kLiquid", k1.value());
const dimensionedScalar cp2("cp", dimSpecificHeatCapacity, gasThermoDict);
const dimensionedScalar k2("k", dimPower/dimLength/dimTemperature, gasThermoDict);

// --- Phase change (enthalpy-porosity, Voller-Prakash)
const dimensionedScalar Tsol("Tsolidus", dimTemperature, meltProperties);
const dimensionedScalar Tliq("Tliquidus", dimTemperature, meltProperties);
const dimensionedScalar Lf("L", dimEnergy/dimMass, meltProperties);

const dictionary& mushyDict = meltProperties.subDict("mushyZone");
const dimensionedScalar Cmushy("C", dimDensity/dimTime, mushyDict);
const scalar epsMushy = mushyDict.getOrDefault<scalar>("eps", 1e-3);

const dictionary& solDict = meltProperties.subDict("solution");
const label nTCorr = solDict.getOrDefault<label>("nTCorr", 3);
const scalar flRelax = solDict.getOrDefault<scalar>("flRelax", 0.9);
const scalar TminClip = solDict.getOrDefault<scalar>("Tmin", 200.0);
const scalar TmaxClip = solDict.getOrDefault<scalar>("Tmax", 5000.0);
const scalar alphaMinFl = solDict.getOrDefault<scalar>("alphaMin", 1e-3);

// --- Velocity of the solid metal outside the wire zone (substrate motion in
//     the laboratory frame: -scan velocity of the laser relative to the part)
const vector solidVelocity
(
    meltProperties.getOrDefault<vector>("solidVelocity", Zero)
);

// --- Wire (feeding) definition
const dictionary& wireDict = meltProperties.subDict("wire");
const point wireOrigin(wireDict.get<point>("origin"));      // point on axis (aim point)
vector wireUp(wireDict.get<vector>("axis"));                // unit vector, tip -> feeder
wireUp /= mag(wireUp) + VSMALL;
const scalar wireRadius = wireDict.get<scalar>("radius");
const scalar wireZoneRadiusFactor =
    wireDict.getOrDefault<scalar>("zoneRadiusFactor", 1.5);
const scalar wireZoneMinHeight =
    wireDict.getOrDefault<scalar>("zoneMinHeight", -GREAT);  // along wireUp from origin
const scalar wireZoneMinZ =
    wireDict.getOrDefault<scalar>("zoneMinZ", -GREAT);       // absolute z (vertical)
const vector wireFeedVelocity(wireDict.get<vector>("feedVelocity"));   // m/s
const scalar wireFeedStart = wireDict.getOrDefault<scalar>("tFeedStart", 0.0);
const scalar wireFeedRamp  = wireDict.getOrDefault<scalar>("tFeedRamp", 0.0);

Info<< "    Tsolidus/Tliquidus  : " << Tsol.value() << " / " << Tliq.value() << " K" << nl
    << "    latent heat         : " << Lf.value() << " J/kg" << nl
    << "    k solid / liquid    : " << k1.value() << " / " << k1Liquid << " W/m/K" << nl
    << "    mushy C, eps        : " << Cmushy.value() << ", " << epsMushy << nl
    << "    solid (substrate) U : " << solidVelocity << nl
    << "    wire radius, feed U : " << wireRadius << " m, " << wireFeedVelocity
    << "  (start " << wireFeedStart << " s)" << nl
    << endl;


// ---------------------------------------------------------------------------
// Two-metal option: wire material != substrate material.
// A wire-material mass fraction cWire (1 = wire alloy, 0 = substrate alloy) is
// advected with the VOF metal flux; metal properties are mixed linearly in
// cWire (rule of mixtures). rho and viscosity stay single (incompressible VOF).
// Substrate values: metal{}, Tsolidus/Tliquidus/L, surfaceTension{}, laser{}.
// Wire values: wireMaterial{} (missing entries fall back to the substrate).
// ---------------------------------------------------------------------------
const dictionary wireMatDict(meltProperties.subOrEmptyDict("wireMaterial"));
const bool twoMetals = wireMatDict.getOrDefault<bool>("enabled", false);
const dictionary stDict0(meltProperties.subOrEmptyDict("surfaceTension"));
const dictionary lDict0(meltProperties.subOrEmptyDict("laser"));
struct metalProps { scalar cp, ks, kl, L, Ts, Tl, sigma, dsig, A; };
const metalProps subP
{
    cp1.value(), k1.value(), k1Liquid, Lf.value(), Tsol.value(), Tliq.value(),
    stDict0.getOrDefault<scalar>("sigma", 1.8),
    stDict0.getOrDefault<scalar>("dSigmadT", 0.0),
    lDict0.getOrDefault<scalar>("absorptivity", 0.35)
};
const metalProps wireP
{
    wireMatDict.getOrDefault<scalar>("cp", subP.cp),
    wireMatDict.getOrDefault<scalar>("k", subP.ks),
    wireMatDict.getOrDefault<scalar>("kLiquid", subP.kl),
    wireMatDict.getOrDefault<scalar>("L", subP.L),
    wireMatDict.getOrDefault<scalar>("Tsolidus", subP.Ts),
    wireMatDict.getOrDefault<scalar>("Tliquidus", subP.Tl),
    wireMatDict.getOrDefault<scalar>("sigma", subP.sigma),
    wireMatDict.getOrDefault<scalar>("dSigmadT", subP.dsig),
    wireMatDict.getOrDefault<scalar>("absorptivity", subP.A)
};
if (twoMetals)
{
    Info<< "Two-metal model (wire / substrate):" << nl
        << "    cp " << wireP.cp << " / " << subP.cp << nl
        << "    k  " << wireP.ks << "," << wireP.kl << " / " << subP.ks << "," << subP.kl << nl
        << "    L  " << wireP.L << " / " << subP.L << nl
        << "    Ts,Tl " << wireP.Ts << "," << wireP.Tl << " / " << subP.Ts << "," << subP.Tl << nl
        << "    sigma, dsig/dT " << wireP.sigma << "," << wireP.dsig << " / "
        << subP.sigma << "," << subP.dsig << nl
        << "    absorptivity " << wireP.A << " / " << subP.A << nl << endl;
}

volScalarField cWire
(
    IOobject("cWire", runTime.timeName(), mesh, IOobject::MUST_READ, IOobject::AUTO_WRITE),
    mesh
);

#define MATFIELD(name, val) \
    volScalarField name \
    ( \
        IOobject(#name, runTime.timeName(), mesh, IOobject::NO_READ, IOobject::NO_WRITE), \
        mesh, dimensionedScalar(dimless, val) \
    );
MATFIELD(matCp, subP.cp)
MATFIELD(matKs, subP.ks)
MATFIELD(matKl, subP.kl)
MATFIELD(matL, subP.L)
MATFIELD(matTsol, subP.Ts)
MATFIELD(matTliq, subP.Tl)
MATFIELD(matSigma, subP.sigma)
MATFIELD(matDSigma, subP.dsig)
MATFIELD(matA, subP.A)
#undef MATFIELD

#include "createComponents.H"
#include "updateMaterial.H"

// --- Temperature
Info<< "Reading field T\n" << endl;
volScalarField T
(
    IOobject("T", runTime.timeName(), mesh, IOobject::MUST_READ, IOobject::AUTO_WRITE),
    mesh
);

// --- Liquid fraction of the metal (0 = solid, 1 = liquid)
volScalarField liquidFraction
(
    IOobject("liquidFraction", runTime.timeName(), mesh, IOobject::MUST_READ, IOobject::AUTO_WRITE),
    mesh
);
{
    liquidFraction.primitiveFieldRef() =
        max(min((T.primitiveField() - matTsol.primitiveField())
               /max(matTliq.primitiveField() - matTsol.primitiveField(), SMALL), 1.0), 0.0);
    liquidFraction.correctBoundaryConditions();
}

// --- Melt history marker (1 = metal that has been molten), advected with U
volScalarField meltHistory
(
    IOobject("meltHistory", runTime.timeName(), mesh, IOobject::MUST_READ, IOobject::AUTO_WRITE),
    mesh
);

volScalarField alphaFl
(
    IOobject("alphaFl", runTime.timeName(), mesh, IOobject::NO_READ, IOobject::NO_WRITE),
    alpha1*liquidFraction
);
alphaFl.oldTime();

volScalarField rhoCp
(
    IOobject("rhoCp", runTime.timeName(), mesh, IOobject::NO_READ, IOobject::NO_WRITE),
    alpha1*rho1*matCp*dimensionedScalar(dimSpecificHeatCapacity, 1.0) + alpha2*rho2*cp2
);
rhoCp.oldTime();

volScalarField Kmushy
(
    IOobject("Kmushy", runTime.timeName(), mesh, IOobject::NO_READ, IOobject::NO_WRITE),
    mesh,
    dimensionedScalar(dimDensity/dimTime, Zero)
);

// --- Optional rigid substrate (anti-indentation, default off):
//     the Carman-Kozeny coefficient is multiplied by KFactor in (nearly) solid
//     metal whose cell centre lies below the original plate surface zTop.
//     The prescribed wire feed then cannot indent / displace the solid plate
//     through the pressure coupling (a cold, never-molten wire tip used to be
//     pushed ~0.5 mm into the solid substrate at start-up); the fed wire metal
//     is deflected along the plate instead (dragged with the substrate).
const dictionary rigidSubDict(meltProperties.subOrEmptyDict("rigidSubstrate"));
const bool rigidSubstrate = rigidSubDict.getOrDefault<bool>("enabled", false);
const scalar rigidSubZTop = rigidSubDict.getOrDefault<scalar>("zTop", 0.0);
const scalar rigidSubKFactor = rigidSubDict.getOrDefault<scalar>("KFactor", 100.0);
const scalar rigidSubFlMax = rigidSubDict.getOrDefault<scalar>("flMax", 0.05);
Info<< "Rigid substrate (Kmushy x KFactor below zTop where fl < flMax): "
    << (rigidSubstrate ? "on" : "off");
if (rigidSubstrate)
{
    Info<< "  zTop " << rigidSubZTop << " KFactor " << rigidSubKFactor
        << " flMax " << rigidSubFlMax;
}
Info<< nl << endl;

volVectorField Usolid
(
    IOobject("Usolid", runTime.timeName(), mesh, IOobject::NO_READ, IOobject::NO_WRITE),
    mesh,
    dimensionedVector(dimVelocity, Zero)
);

// Laser heat source [W/m3]
volScalarField Qheat
(
    IOobject("Qheat", runTime.timeName(), mesh, IOobject::NO_READ, IOobject::AUTO_WRITE),
    mesh,
    dimensionedScalar(dimPower/dimVolume, Zero)
);

// Free-surface height of each vertical column (metal column integral) [m]
volScalarField zSurface
(
    IOobject("zSurface", runTime.timeName(), mesh, IOobject::NO_READ, IOobject::AUTO_WRITE),
    mesh,
    dimensionedScalar(dimLength, Zero)
);

// Recoil pressure [Pa]
volScalarField pRecoil
(
    IOobject("pRecoil", runTime.timeName(), mesh, IOobject::NO_READ, IOobject::AUTO_WRITE),
    mesh,
    dimensionedScalar(dimPressure, Zero)
);

scalar laserAbsorbedPower = 0;     // W in the meshed domain
scalar laserIncidentPower = 0;     // W in the meshed domain (before absorptivity)
scalar surfaceLossPower = 0;       // W (evaporation + radiation + convection)

// ---------------------------------------------------------------------------
// Vertical cell columns for the ray-traced laser.
// Requires a structured (blockMesh) Cartesian mesh whose cells line up in z
// and a decomposition without cuts in z (simple, n = (nx ny 1)), so that each
// column lives on one processor.
// ---------------------------------------------------------------------------
List<labelList> colCells;      // cells of each column, sorted top -> bottom
scalarField colX, colY, colArea, colZbot;
labelList cellColumn(mesh.nCells(), -1);
{
    const vectorField& C = mesh.C().primitiveField();
    const scalarField& V = mesh.V();
    const pointField& pts = mesh.points();
    const labelListList& cPts = mesh.cellPoints();

    const scalar qtol = 1e-8;   // 10 nm key resolution
    std::map<std::pair<long long, long long>, label> keyToCol;
    DynamicList<DynamicList<label>> cols;
    scalarField dz(C.size(), Zero), zlo(C.size(), Zero);

    forAll(C, celli)
    {
        scalar zmin = GREAT, zmax = -GREAT;
        for (const label pi : cPts[celli])
        {
            zmin = min(zmin, pts[pi].z());
            zmax = max(zmax, pts[pi].z());
        }
        dz[celli] = max(zmax - zmin, SMALL);
        zlo[celli] = zmin;

        const std::pair<long long, long long> key
        (
            std::llround(C[celli].x()/qtol),
            std::llround(C[celli].y()/qtol)
        );
        auto it = keyToCol.find(key);
        label ci;
        if (it == keyToCol.end())
        {
            ci = cols.size();
            keyToCol[key] = ci;
            cols.append(DynamicList<label>());
        }
        else
        {
            ci = it->second;
        }
        cols[ci].append(celli);
        cellColumn[celli] = ci;
    }

    colCells.setSize(cols.size());
    colX.setSize(cols.size());
    colY.setSize(cols.size());
    colArea.setSize(cols.size());
    colZbot.setSize(cols.size());
    forAll(cols, ci)
    {
        labelList cl(cols[ci]);
        // sort top -> bottom
        std::sort
        (
            cl.begin(), cl.end(),
            [&](label a, label b){ return C[a].z() > C[b].z(); }
        );
        colCells[ci] = cl;
        const label c0 = cl[0];
        colX[ci] = C[c0].x();
        colY[ci] = C[c0].y();
        colArea[ci] = V[c0]/dz[c0];
        scalar zb = GREAT;
        for (const label c : cl) zb = min(zb, zlo[c]);
        colZbot[ci] = zb;
    }

    Info<< "Laser columns: " << returnReduce(cols.size(), sumOp<label>())
        << " vertical cell columns (cells " << returnReduce(C.size(), sumOp<label>())
        << ")" << nl << endl;
}

boolList inWireZone(mesh.nCells(), false);

#include "updateWireZone.H"

#include "createLaserRays.H"

// --- Surface tension (liquid-only CSF, sigma(T), Marangoni, capillary dt)
#include "createSurfaceTension.H"

mesh.setFluxRequired(T.name());
