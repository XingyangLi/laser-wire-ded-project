// Apply the oxide coverage factor after updateSurfaceTension.H.
// Included from the time loop only. createSurfaceTension.H pulls in
// updateSurfaceTension.H at startup, before the oxide fields exist.
// Coverage in [0, 1] multiplies sigma and dSigma/dT by
// (1 - sigmaDrop*coverage). Off the film the factor is 1.
if (oxideSkinEnabled && oxideSurface)
{
    scalarField& sigOx = sigmaT.primitiveFieldRef();
    scalarField& dsvOx = dSigmadTField.primitiveFieldRef();
    const scalarField& oxS = oxideCoverage.primitiveField();
    forAll(sigOx, celli)
    {
        if (oxS[celli] < 1e-6) continue;
        const scalar fac =
            max(scalar(1) - oxideSigmaDrop*oxS[celli], scalar(0));
        sigOx[celli] = max(sigOx[celli]*fac, sigmaMin);
        dsvOx[celli] *= fac;
        if (sigOx[celli] <= sigmaMin + SMALL)
        {
            dsvOx[celli] = 0;
        }
    }
    sigmaT.correctBoundaryConditions();
    dSigmadTField.correctBoundaryConditions();
}
