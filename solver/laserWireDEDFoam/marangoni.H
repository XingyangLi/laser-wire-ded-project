// Thermocapillary (Marangoni) body force, CSF form, liquid metal only:
//   F_M = w * dSigma/dT * ( grad T - n (n . grad T) ) * |grad alpha|
// w = stWeight (liquid weight, see createSurfaceTension.H). dSigma/dT is
// dSigmadTField: the constant alloy slope, or the Sahoo-Belton derivative
// when oxygenDependent is true (positive at high oxygen, so the stress reverses).
// Only acts where sigma is not clipped (T > Tliq and sigma > sigmaMin).
// Returned as a volVectorField 'Fmarangoni' [N/m3].
volVectorField Fmarangoni
(
    IOobject("Fmarangoni", runTime.timeName(), mesh),
    mesh,
    dimensionedVector(dimForce/dimVolume, Zero)
);
if (marangoniOn && (oxygenDependent || mag(subP.dsig) > 0 || mag(wireP.dsig) > 0))
{
    const volVectorField gradAlpha(fvc::grad(alpha1));
    const volScalarField magGradAlpha(mag(gradAlpha));
    const volVectorField nHat
    (
        gradAlpha/(magGradAlpha + dimensionedScalar(dimless/dimLength, 1e-8/Foam::cbrt(average(mesh.V()).value())))
    );
    const volVectorField gradT(fvc::grad(T));
    volScalarField active(stWeight);
    if (sigmaTdep || oxygenDependent)
    {
        forAll(active, celli)
        {
            if (T[celli] <= matTliq[celli] || sigmaT[celli] <= sigmaMin) active[celli] = 0;
        }
    }
    // density scaling 2 rho/(rho1+rho2): moves the CSF force onto the metal side so
    // that the light gas next to the interface is not accelerated (parasitic currents)
    Fmarangoni = (2.0*rho/(rho1 + rho2))*active*dSigmadTField*dimensionedScalar(dimForce/dimLength/dimTemperature, 1.0)*(gradT - nHat*(nHat & gradT))*magGradAlpha;
}

// Optional Boussinesq buoyancy of the liquid metal:
//   F_b = -alpha fl rho_m beta (T - Tliquidus) g
volVectorField Fbuoy
(
    IOobject("Fbuoy", runTime.timeName(), mesh),
    mesh,
    dimensionedVector(dimForce/dimVolume, Zero)
);
{
    const dictionary& bDict = meltProperties.subOrEmptyDict("buoyancy");
    if (bDict.getOrDefault<bool>("enabled", false))
    {
        const dimensionedScalar beta
        (
            "beta", dimless/dimTemperature, bDict.getOrDefault<scalar>("beta", 1e-4)
        );
        Fbuoy = -alpha1*liquidFraction*rho1*beta*(T - Tliq)*g;
    }
}
