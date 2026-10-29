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
scalar oxideSkinMu0 = oxideSkinDict.getOrDefault<scalar>("muSkin", 20.0);
scalar oxideSkinK0 = oxideSkinDict.getOrDefault<scalar>("Kskin", 1.0e14);
const scalar oxideSkinGap = oxideSkinDict.getOrDefault<scalar>("gapThreshold", 0.10e-3);
const scalar oxideSkinZ0 = oxideSkinDict.getOrDefault<scalar>("zMin", 0.30e-3);
const scalar oxideSkinZ1 = oxideSkinDict.getOrDefault<scalar>("zMax", 1.55e-3);
const scalar oxideSkinPpmRef = max
(
    oxideSkinDict.getOrDefault<scalar>("ppmRef", 300.0),
    SMALL
);
const scalar oxideSkinAlphaGas = oxideSkinDict.getOrDefault<scalar>("alphaGas", 0.98);
// dynamic: coverage is a scalar carried on the free surface. It starts at 0
// (nothing painted) and grows where the surface is exposed. The geometric
// shell below is not used. genTime is the rise toward the ppm strength;
// leaveTime is how fast coverage fades once the surface has moved on.
const bool oxideSkinDynamic = oxideSkinDict.getOrDefault<bool>("dynamic", false);
const scalar oxideSkinGenTime = oxideSkinDict.getOrDefault<scalar>("genTime", 1e-3);
const scalar oxideSkinLeaveTime = oxideSkinDict.getOrDefault<scalar>("leaveTime", 2e-4);
const label oxideSkinInterval = oxideSkinDict.getOrDefault<label>
(
    "interval",
    contactInterval
);
label oxideSkinLogIndex = -1;

scalar oxideSkinStrength = 0;
// Extra tension (N/m) per unit coverage. 0 leaves the alloy sigma alone.
// Imposed numerical stiffness of the skin, not a change of the alloy.
scalar oxideSkinSigma = 0;
// Non-wetting window written into the log. The wall BC carries the same
// angles (thetaRox / thetaAox) so a skinned wall face does not wet.
scalar oxideSkinThetaR = 0;
scalar oxideSkinThetaA = 0;
// Elastic membrane. Imposed numerical model. E is the in-plane modulus
// (N/m) at saturation, bend is the length over which the membrane force
// fades as the gap opens, epsRup is the stretch at which the skin breaks
// and the surface is free again. aCap limits the elastic acceleration.
scalar oxideSkinE = 0;
scalar oxideSkinBend = 8e-5;
scalar oxideSkinEpsRup = 1.2;
scalar oxideSkinACap = oxideSkinDict.getOrDefault<scalar>("aCap", 150);
if (oxideSkinEnabled)
{
    oxideSkinStrength =
        oxygenDependent
      ? min(max(chamberOxygenPpm/oxideSkinPpmRef, scalar(0)), scalar(1))
      : scalar(1);

    // ppm strength mu[Pa.s] sigmaExtra[N/m] thetaRox[deg] thetaAox[deg]
    // Model assumption. Higher ppm: more skin, stiffer film, less wetting.
    const List<scalarList> oxTable
    (
        oxideSkinDict.getOrDefault<List<scalarList>>
        (
            "oxygenTable",
            List<scalarList>()
        )
    );
    if (oxTable.size())
    {
        const scalar ppm = oxideSkinDict.getOrDefault<scalar>
        (
            "ppm",
            oxygenDependent ? chamberOxygenPpm : 300
        );
        for (const scalarList& row : oxTable)
        {
            if (row.size() < 6)
            {
                FatalErrorInFunction
                    << "oxideSkin/oxygenTable rows are ppm strength mu "
                    << "sigmaExtra thetaRox thetaAox, got " << row << nl
                    << exit(FatalError);
            }
        }
        label iLo = 0;
        label iHi = oxTable.size() - 1;
        for (label i = 0; i < oxTable.size(); ++i)
        {
            if (oxTable[i][0] <= ppm) iLo = i;
        }
        for (label i = 0; i < oxTable.size(); ++i)
        {
            if (oxTable[i][0] >= ppm)
            {
                iHi = i;
                break;
            }
        }
        const scalar x0 = oxTable[iLo][0];
        const scalar x1 = oxTable[iHi][0];
        const scalar f =
            (iLo == iHi) ? 0 : (ppm - x0)/max(x1 - x0, SMALL);
        const scalar sat = oxTable[iLo][1] + f*(oxTable[iHi][1] - oxTable[iLo][1]);
        const scalar muRow = oxTable[iLo][2] + f*(oxTable[iHi][2] - oxTable[iLo][2]);
        const scalar sigRow = oxTable[iLo][3] + f*(oxTable[iHi][3] - oxTable[iLo][3]);
        oxideSkinThetaR = oxTable[iLo][4] + f*(oxTable[iHi][4] - oxTable[iLo][4]);
        oxideSkinThetaA = oxTable[iLo][5] + f*(oxTable[iHi][5] - oxTable[iLo][5]);
        oxideSkinStrength = max(sat, scalar(0));
        // Coverage saturates at `sat`, and mu/sigma are the values at that
        // saturation. The damper K stays 0: stiffness is the extra tension,
        // not a 1e14 sink.
        const scalar satSafe = max(oxideSkinStrength, scalar(0.05));
        oxideSkinMu0 = max(muRow, scalar(0))/satSafe;
        oxideSkinSigma = max(sigRow, scalar(0))/satSafe;
        oxideSkinK0 = 0;
        oxideSkinE = 2.5*oxideSkinStrength;
        if (oxTable[iLo].size() >= 9 && oxTable[iHi].size() >= 9)
        {
            oxideSkinE =
                oxTable[iLo][6] + f*(oxTable[iHi][6] - oxTable[iLo][6]);
            oxideSkinBend =
                oxTable[iLo][7] + f*(oxTable[iHi][7] - oxTable[iLo][7]);
            oxideSkinEpsRup =
                oxTable[iLo][8] + f*(oxTable[iHi][8] - oxTable[iLo][8]);
        }
        oxideSkinE = max(oxideSkinE, scalar(0));
        oxideSkinBend = max(oxideSkinBend, scalar(1e-5));
        oxideSkinEpsRup = max(oxideSkinEpsRup, scalar(0.05));
        Info<< "OxideSkin table: ppm " << ppm
            << " sat " << oxideSkinStrength
            << " mu " << muRow << " Pa.s"
            << " sigmaExtra " << sigRow << " N/m"
            << " thetaOx " << oxideSkinThetaR << "/" << oxideSkinThetaA
            << " deg  E " << oxideSkinE << " N/m"
            << " bend " << oxideSkinBend*1e3 << " mm"
            << " epsRup " << oxideSkinEpsRup
            << " (imposed elastic membrane)" << nl;
    }
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

// Elastic membrane force. Zero when the skin is off.
volVectorField Fskin
(
    IOobject
    (
        "Fskin",
        runTime.timeName(),
        mesh,
        IOobject::NO_READ,
        IOobject::NO_WRITE
    ),
    mesh,
    dimensionedVector(dimForce/dimVolume, Zero)
);

// Surface stretch. Missing file -> 0, same unpainted start as coverage.
volScalarField skinStrain
(
    IOobject
    (
        "skinStrain",
        runTime.timeName(),
        mesh,
        IOobject::READ_IF_PRESENT,
        (oxideSkinEnabled && oxideSkinDynamic)
      ? IOobject::AUTO_WRITE
      : IOobject::NO_WRITE
    ),
    mesh,
    dimensionedScalar(dimless, Zero),
    "zeroGradient"
);

// Coverage in [0, 1]. Missing file -> 0, so a restarted neck is unpainted.
volScalarField oxideCoverage
(
    IOobject
    (
        "oxideCoverage",
        runTime.timeName(),
        mesh,
        IOobject::READ_IF_PRESENT,
        (oxideSkinEnabled && oxideSkinDynamic)
      ? IOobject::AUTO_WRITE
      : IOobject::NO_WRITE
    ),
    mesh,
    dimensionedScalar(dimless, Zero),
    "zeroGradient"
);

if (oxideSkinEnabled)
{
    Info<< "OxideSkin: "
        << (oxideSkinStrength > SMALL ? "on" : "off (zero strength)")
        << " strength " << oxideSkinStrength
        << " mu " << oxideSkinStrength*oxideSkinMu0 << " Pa.s"
        << " K " << oxideSkinStrength*oxideSkinK0;
    if (oxideSkinDynamic)
    {
        Info<< " dynamic"
            << " genTime " << oxideSkinGenTime
            << " leaveTime " << oxideSkinLeaveTime
            << " coverage0 " << gMax(oxideCoverage.primitiveField())
            << " (generated on the exposed surface, nothing painted)";
    }
    else
    {
        Info<< " gap " << oxideSkinGap << " m"
            << " z " << oxideSkinZ0 << " " << oxideSkinZ1
            << " ppmRef " << oxideSkinPpmRef
            << " alphaGas " << oxideSkinAlphaGas;
    }
    Info<< nl << endl;
}
