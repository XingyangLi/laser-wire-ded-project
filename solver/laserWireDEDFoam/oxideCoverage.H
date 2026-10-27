// Move oxide coverage with the volume flux, then grow it on the exposed
// metal/gas surface and let it fade off that surface. The field starts at 0.
// Saturation is the ppm strength (min(ppm/ppmRef, 1)).
{
    const scalar dtOx = runTime.deltaTValue();
    oxideCoverage.correctBoundaryConditions();
    const volScalarField divOx(fvc::div(phi, oxideCoverage));
    scalarField& ox = oxideCoverage.primitiveFieldRef();
    const scalarField& dOx = divOx.primitiveField();
    forAll(ox, celli)
    {
        ox[celli] = max(min(ox[celli] - dtOx*dOx[celli], scalar(1)), scalar(0));
    }

    const volVectorField gradOx(fvc::grad(alpha1));
    const vectorField& gOx = gradOx.primitiveField();
    const scalarField& aOx = alpha1.primitiveField();
    const scalarField& vOx = mesh.V();
    const scalar tauG = max(oxideSkinGenTime, SMALL);
    const scalar tauL = max(oxideSkinLeaveTime, SMALL);
    const scalar sat = oxideSkinStrength;
    forAll(ox, celli)
    {
        const scalar h = Foam::cbrt(max(vOx[celli], SMALL));
        const bool exposed =
            mag(gOx[celli])*h > 0.25
         && aOx[celli] > 0.02
         && aOx[celli] < 0.98;
        if (exposed)
        {
            ox[celli] += dtOx/tauG*(sat - ox[celli]);
        }
        else if (ox[celli] > 0)
        {
            ox[celli] -= dtOx/tauL*ox[celli];
        }
        ox[celli] = max(min(ox[celli], scalar(1)), scalar(0));
    }
    oxideCoverage.correctBoundaryConditions();
}
