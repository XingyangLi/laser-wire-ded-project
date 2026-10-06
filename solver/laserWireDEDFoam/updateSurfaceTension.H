// Update sigma(T), the liquid weight and the CSF face force (after TEqn.H)
{
    if (sigmaTdep)
    {
        sigmaT.primitiveFieldRef() =
            max
            (
                matSigma.primitiveField()
              + matDSigma.primitiveField()
               *(max(T.primitiveField(), matTliq.primitiveField()) - matTliq.primitiveField()),
                sigmaMin
            );
        sigmaT.correctBoundaryConditions();
    }

    surfaceScalarField sigmaKf(fvc::interpolate(sigmaT*(-fvc::div(mixture.nHatf()))));

    if (stLiquidOnly)
    {
        const surfaceScalarField alphaf(fvc::interpolate(alpha1));
        const surfaceScalarField alphaFlf(fvc::interpolate(alphaFl));
        stWeightf =
            min
            (
                max
                (
                    alphaFlf/max(alphaf, dimensionedScalar(dimless, stAlphaMin)),
                    dimensionedScalar(dimless, 0.0)
                ),
                dimensionedScalar(dimless, 1.0)
            );
        stWeight = fvc::average(stWeightf);
        sigmaKf *= stWeightf;
    }

    stForcef = sigmaKf*fvc::snGrad(alpha1);
}
