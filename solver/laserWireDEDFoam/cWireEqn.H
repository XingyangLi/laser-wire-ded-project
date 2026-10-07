// Composition tracers: conservative explicit transport with the MULES metal
// flux (consistent with the alpha update), c = (alpha c)/alpha in the metal.
// components{conservativeTracers true;} (createComponents.H): face values from a
// gas-cell extension of c (no stale gas values), low-alpha cells take the
// extension value; tracerBudget: global budget -> meltPool/tracerBudget.dat
if (multiComp)
{
    const label nC = compNames.size();
    const scalarField& Vc = mesh.V();
    if (tracerBudget && !trBudgetInit)
    {
        trS0.setSize(nC, 0); trBnd.setSize(nC, 0); trClip.setSize(nC, 0);
        trSkip.setSize(nC, 0); trNorm.setSize(nC, 0);
        for (label i = 0; i < nC; ++i)
        {
            trS0[i] = gSum(alpha1.oldTime().primitiveField()*cComp[i].primitiveField()*Vc);
        }
        trPatchMetal.setSize(mesh.boundary().size(), 0);
        trMetal0 = gSum(alpha1.oldTime().primitiveField()*Vc);
        trBudgetInit = true;
    }
    if (tracerBudget)
    {
        forAll(alphaPhi10.boundaryField(), pi)
        {
            if (!alphaPhi10.boundaryField()[pi].coupled())
            {
                scalar fl = runTime.deltaTValue()*sum(alphaPhi10.boundaryField()[pi]);
                reduce(fl, sumOp<scalar>());
                trPatchMetal[pi] += fl;
            }
        }
    }
    // gas-cell extension weights (shared by all tracers of this step)
    tmp<volScalarField> tAOld(new volScalarField("alphaOldTr", alpha1.oldTime()));
    const volScalarField& aOld = tAOld();
    tmp<volScalarField> tDen;
    if (conservativeTracers)
    {
        tDen = fvc::surfaceSum(mesh.magSf()*fvc::interpolate(max(aOld, scalar(0))));
    }
    // one transport step per tracer (components c_i and unmelted markers u_i)
    auto transportTracer = [&](volScalarField& c, const label k)
    {
        const bool budget = tracerBudget && k >= 0;
        tmp<volScalarField> tcI;
        if (conservativeTracers)
        {
            tcI = tmp<volScalarField>(new volScalarField(c.name() + "Ext", c));
            volScalarField& cE = tcI.ref();
            const volScalarField num
            (
                fvc::surfaceSum(mesh.magSf()*fvc::interpolate(max(aOld, scalar(0))*c))
            );
            const scalarField& den = tDen().primitiveField();
            scalarField& ce = cE.primitiveFieldRef();
            forAll(ce, celli)
            {
                if (aOld[celli] < tracerExtAlpha && den[celli] > VSMALL)
                {
                    ce[celli] = max(min(num[celli]/den[celli], 1.0), 0.0);
                }
            }
            cE.correctBoundaryConditions();
        }
        const volScalarField& cI = conservativeTracers ? tcI() : c;
        const volScalarField alphaC0(aOld*c);
        const surfaceScalarField cFlux
        (
            fvc::flux(alphaPhi10, cI, "div(alphaPhi,cComp)")
        );
        const volScalarField alphaC(alphaC0 - runTime.deltaT()*fvc::div(cFlux));
        scalar dClip = 0, dSkip = 0, dBnd = 0;
        if (budget)
        {
            forAll(cFlux.boundaryField(), pi)
            {
                if (!cFlux.boundaryField()[pi].coupled())
                {
                    dBnd -= runTime.deltaTValue()*sum(cFlux.boundaryField()[pi]);
                }
            }
        }
        scalarField& cf = c.primitiveFieldRef();
        forAll(cf, celli)
        {
            const scalar a = alpha1[celli];
            if (a > tracerAlphaMin)
            {
                const scalar cn = alphaC[celli]/a;
                const scalar cc = max(min(cn, 1.0), 0.0);
                if (budget) dClip += (cc - cn)*a*Vc[celli];
                cf[celli] = cc;
            }
            else
            {
                const scalar cc = conservativeTracers ? cI[celli] : cf[celli];
                if (budget) dSkip += (a*cc - alphaC[celli])*Vc[celli];
                cf[celli] = cc;
            }
        }
        if (budget)
        {
            reduce(dClip, sumOp<scalar>());
            reduce(dSkip, sumOp<scalar>());
            reduce(dBnd, sumOp<scalar>());
            trClip[k] += dClip; trSkip[k] += dSkip; trBnd[k] += dBnd;
        }
    };
    for (label i = 0; i < nC; ++i)
    {
        transportTracer(cComp[i], i);
        transportTracer(uComp[i], -1);
    }
    // consistency: sum(c_i) <= 1, u_i <= c_i; cWire = sum(c_i)
    scalarList dNorm(nC, 0);
    scalarField& cw = cWire.primitiveFieldRef();
    forAll(cw, celli)
    {
        scalar s = 0;
        for (label i = 0; i < nC; ++i) s += cComp[i][celli];
        if (s > 1.0)
        {
            for (label i = 0; i < nC; ++i)
            {
                if (tracerBudget)
                {
                    dNorm[i] += (cComp[i][celli]/s - cComp[i][celli])*alpha1[celli]*Vc[celli];
                }
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
    if (tracerBudget)
    {
        for (label i = 0; i < nC; ++i)
        {
            reduce(dNorm[i], sumOp<scalar>());
            trNorm[i] += dNorm[i];
        }
        const dictionary& stDictTB = meltProperties.subOrEmptyDict("statistics");
        const label everyTB = stDictTB.getOrDefault<label>("interval", 10);
        if (runTime.timeIndex() % max(everyTB, 1) == 0 || runTime.writeTime())
        {
            const scalar metalNow = gSum(alpha1.primitiveField()*Vc);
            scalarList sNow(nC, 0);
            for (label i = 0; i < nC; ++i)
            {
                sNow[i] = gSum(alpha1.primitiveField()*cComp[i].primitiveField()*Vc);
            }
            if (Pstream::master())
            {
                const fileName dir(runTime.globalPath()/"postProcessing"/"meltPool");
                mkDir(dir);
                const fileName fn(dir/"tracerBudget.dat");
                std::ofstream os(fn.c_str(), std::ios::app);
                if (!trHeaderDone)
                {
                    trHeaderDone = true;
                    os << "# tracer budget per component [m3 of metal]: S = sum(alpha c V) now, S0 at the"
                       << " (re)start, cumulative boundary net inflow, clipping, low-alpha skip, sum>1"
                       << " normalisation; resid = S - S0 - bnd - clip - skip - norm (should be ~0);"
                       << " metal = sum(alpha V), metal0 at the (re)start, out_<patch> = cumulative metal"
                       << " OUTflow through each patch (negative = inflow, e.g. wireInlet)\n";
                    os << "# time[s]";
                    for (label i = 0; i < nC; ++i)
                    {
                        const word& n = compNames[i];
                        os << " S_" << n << " S0_" << n << " bnd_" << n << " clip_" << n
                           << " skip_" << n << " norm_" << n << " resid_" << n;
                    }
                    os << " metal metal0";
                    forAll(mesh.boundary(), pi)
                    {
                        if (!mesh.boundary()[pi].coupled())
                        {
                            os << " out_" << mesh.boundary()[pi].name();
                        }
                    }
                    os << "\n";
                }
                os.precision(9);
                os << runTime.value();
                for (label i = 0; i < nC; ++i)
                {
                    os << ' ' << sNow[i] << ' ' << trS0[i] << ' ' << trBnd[i] << ' ' << trClip[i]
                       << ' ' << trSkip[i] << ' ' << trNorm[i] << ' '
                       << sNow[i] - trS0[i] - trBnd[i] - trClip[i] - trSkip[i] - trNorm[i];
                }
                os << ' ' << metalNow << ' ' << trMetal0;
                forAll(mesh.boundary(), pi)
                {
                    if (!mesh.boundary()[pi].coupled()) os << ' ' << trPatchMetal[pi];
                }
                os << '\n';
            }
        }
    }
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
