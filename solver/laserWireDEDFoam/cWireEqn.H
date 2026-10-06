// Composition tracers: conservative explicit transport with the MULES metal
// flux (consistent with the alpha update), c = (alpha c)/alpha in the metal.
if (multiComp)
{
    // one transport step per tracer (components c_i and unmelted markers u_i)
    auto transportTracer = [&](volScalarField& c)
    {
        const volScalarField alphaC0(alpha1.oldTime()*c);
        const surfaceScalarField cFlux
        (
            fvc::flux(alphaPhi10, c, "div(alphaPhi,cComp)")
        );
        const volScalarField alphaC(alphaC0 - runTime.deltaT()*fvc::div(cFlux));
        scalarField& cf = c.primitiveFieldRef();
        forAll(cf, celli)
        {
            if (alpha1[celli] > 1e-3)
            {
                cf[celli] = max(min(alphaC[celli]/alpha1[celli], 1.0), 0.0);
            }
        }
    };
    const label nC = compNames.size();
    for (label i = 0; i < nC; ++i)
    {
        transportTracer(cComp[i]);
        transportTracer(uComp[i]);
    }
    // consistency: sum(c_i) <= 1, u_i <= c_i; cWire = sum(c_i)
    scalarField& cw = cWire.primitiveFieldRef();
    forAll(cw, celli)
    {
        scalar s = 0;
        for (label i = 0; i < nC; ++i) s += cComp[i][celli];
        if (s > 1.0)
        {
            for (label i = 0; i < nC; ++i)
            {
                cComp[i].primitiveFieldRef()[celli] /= s;
                uComp[i].primitiveFieldRef()[celli] /= s;
            }
            s = 1.0;
        }
        for (label i = 0; i < nC; ++i)
        {
            uComp[i].primitiveFieldRef()[celli] =
                min(uComp[i][celli], cComp[i][celli]);
        }
        cw[celli] = s;
    }
    for (label i = 0; i < nC; ++i)
    {
        cComp[i].correctBoundaryConditions();
        uComp[i].correctBoundaryConditions();
    }
    cWire.correctBoundaryConditions();
    #include "updateMaterial.H"
}
else if (twoMetals)
{
    const volScalarField alphaC0(alpha1.oldTime()*cWire);
    const surfaceScalarField cFlux
    (
        fvc::flux(alphaPhi10, cWire, "div(alphaPhi,cWire)")
    );
    const volScalarField alphaC(alphaC0 - runTime.deltaT()*fvc::div(cFlux));
    scalarField& c = cWire.primitiveFieldRef();
    forAll(c, celli)
    {
        if (alpha1[celli] > 1e-3)
        {
            c[celli] = max(min(alphaC[celli]/alpha1[celli], 1.0), 0.0);
        }
    }
    cWire.correctBoundaryConditions();
    #include "updateMaterial.H"
}
