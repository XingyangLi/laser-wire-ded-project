// Trailing oxide on the wire surface (meltProperties/oxideAngle, default OFF).
//
// Coverage is a scalar in the cells, not a painted film and not a fixed
// alpha. It grows toward sCap = min(ppm/ppmRef, 1) on the trailing wire
// surface: the first cell outside the wire, and exposed or interfacial
// cells (alpha < 0.9) out to nCells. Buried metal farther out relaxes
// back to 0. There is no advection. The timescale is tau.
//
// That coverage is the generated field. The map from coverage to the wall
// angle, to sigma, and to the no-slip fraction is the imposed law:
//   * pinnedAlphaContactAngle blends [thetaR, thetaA] toward
//     [thetaRox, thetaAox] with the adjacent-cell coverage;
//   * sigma is multiplied by max(1 - sigmaDrop*coverage, sigmaFloor);
//   * partialSlip valueFraction on trailing wireWall faces equals coverage,
//     so a covered face moves at the feed. Kcontact is not set.
// The free surface, including whether a slit opens, is generated.
const dictionary oxideAngleDict(meltProperties.subOrEmptyDict("oxideAngle"));
const bool oxideAngleEnabled = oxideAngleDict.getOrDefault<bool>("enabled", false);
const scalar oxideAngleNCells = oxideAngleDict.getOrDefault<scalar>("nCells", 3);
const scalar oxideAngleTau = max
(
    oxideAngleDict.getOrDefault<scalar>("tau", 1e-3),
    SMALL
);
const scalar oxideAnglePpmRef = max
(
    oxideAngleDict.getOrDefault<scalar>("ppmRef", 300),
    SMALL
);
const scalar oxideAngleSigmaDrop = oxideAngleDict.getOrDefault<scalar>("sigmaDrop", 0.5);
const scalar oxideAngleSigmaFloor = oxideAngleDict.getOrDefault<scalar>("sigmaFloor", 0.1);
const scalar oxideAngleZMin = oxideAngleDict.getOrDefault<scalar>("zMin", 0.30e-3);
if (oxideAngleEnabled)
{
    Info<< "Oxide angle: coverage on the trailing wire, tau " << oxideAngleTau
        << " s, ppmRef " << oxideAnglePpmRef
        << ", sigmaDrop " << oxideAngleSigmaDrop
        << ", floor " << oxideAngleSigmaFloor
        << ", " << oxideAngleNCells << " cells" << nl;
}

volScalarField oxideCoverage
(
    IOobject
    (
        "oxideCoverage",
        runTime.timeName(),
        mesh,
        IOobject::NO_READ,
        oxideAngleEnabled ? IOobject::AUTO_WRITE : IOobject::NO_WRITE
    ),
    mesh,
    dimensionedScalar(dimless, Zero)
);
