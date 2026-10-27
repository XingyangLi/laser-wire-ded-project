// Scale sigma by the trailing-oxide coverage. Runs after sigma(T) or
// Sahoo–Belton has been recomputed, so the factor is applied once.
// Off leaves sigmaT unchanged.
if (oxideAngleEnabled)
{
    scalarField& sig = sigmaT.primitiveFieldRef();
    const scalarField& cov = oxideCoverage.primitiveField();
    forAll(sig, celli)
    {
        const scalar factor = max
        (
            scalar(1) - oxideAngleSigmaDrop*cov[celli],
            oxideAngleSigmaFloor
        );
        sig[celli] = max(sig[celli]*factor, sigmaMin);
    }
    sigmaT.correctBoundaryConditions();
}
