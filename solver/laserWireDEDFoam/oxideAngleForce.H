// Tangential force from the oxide part of grad(sigma) only. Thermal
// Marangoni stays in Fmarangoni and is still multiplied by settleScale.
// Liquid is driven toward higher sigma, away from covered cells.
// Off leaves a zero field.
volVectorField Foxide
(
    IOobject
    (
        "Foxide",
        runTime.timeName(),
        mesh,
        IOobject::NO_READ,
        IOobject::NO_WRITE
    ),
    mesh,
    dimensionedVector(dimForce/dimVolume, Zero)
);
if (oxideAngleEnabled)
{
    volScalarField oxideFactor
    (
        IOobject
        (
            "oxideFactor",
            runTime.timeName(),
            mesh,
            IOobject::NO_READ,
            IOobject::NO_WRITE
        ),
        max
        (
            scalar(1) - oxideAngleSigmaDrop*oxideCoverage,
            dimensionedScalar(dimless, oxideAngleSigmaFloor)
        )
    );
    volScalarField dSigmadCoverage
    (
        IOobject
        (
            "dSigmadCoverage",
            runTime.timeName(),
            mesh,
            IOobject::NO_READ,
            IOobject::NO_WRITE
        ),
        mesh,
        dimensionedScalar(dimForce/dimLength, Zero)
    );
    {
        const scalarField& fac = oxideFactor.primitiveField();
        const scalarField& sig = sigmaT.primitiveField();
        scalarField& ds = dSigmadCoverage.primitiveFieldRef();
        forAll(ds, celli)
        {
            if (fac[celli] > oxideAngleSigmaFloor + 1e-4)
            {
                ds[celli] =
                    -oxideAngleSigmaDrop*sig[celli]/max(fac[celli], SMALL);
            }
        }
    }

    const volVectorField gradAlpha(fvc::grad(alpha1));
    const volScalarField magGradAlpha(mag(gradAlpha));
    const dimensionedScalar nSmall
    (
        dimless/dimLength,
        1e-8/Foam::cbrt(average(mesh.V()).value())
    );
    const volVectorField nHat(gradAlpha/(magGradAlpha + nSmall));
    const volVectorField gradC(fvc::grad(oxideCoverage));
    const volVectorField gradCs(gradC - nHat*(nHat & gradC));
    Foxide =
        (2.0*rho/(rho1 + rho2))*stWeight*dSigmadCoverage*gradCs*magGradAlpha;
}
