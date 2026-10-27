// Update sigma(T) or sigma(T, a_O), the liquid weight and the CSF face force
// (after TEqn.H). dSigmadTField feeds the Marangoni term.
{
    if (oxygenDependent)
    {
        scalarField& sig = sigmaT.primitiveFieldRef();
        scalarField& dsv = dSigmadTField.primitiveFieldRef();
        const scalarField& Tc = T.primitiveField();
        const scalarField& sigM = matSigma.primitiveField();
        const scalarField& dsm = matDSigma.primitiveField();
        const scalarField& Tm = matTliq.primitiveField();
        forAll(sig, celli)
        {
            const scalar sigBase = oxygenSigmaMSet ? oxygenSigmaM : sigM[celli];
            const scalar Aval = oxygenASet ? oxygenA : max(-dsm[celli], scalar(0));
            const scalar TmCell = oxygenTmSet ? oxygenTm : Tm[celli];
            lwdSahooSigma(Tc[celli], sigBase, Aval, TmCell, sig[celli], dsv[celli]);
        }
        sigmaT.correctBoundaryConditions();
        dSigmadTField.correctBoundaryConditions();
    }
    else
    {
        dSigmadTField.primitiveFieldRef() = matDSigma.primitiveField();
        dSigmadTField.correctBoundaryConditions();
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
    }

    #include "oxideAngleSigma.H"

    if
    (
        oxygenDependent
     && (
            runTime.timeIndex() == 0
         || (
                pimple.finalIter()
             && (
                    runTime.timeIndex() % 10 == 0
                 || runTime.writeTime()
                )
            )
        )
    )
    {
        scalar sigSum = 0, dsSum = 0, nLiq = 0;
        scalar sigLo = GREAT, sigHi = -GREAT;
        const scalarField& sig = sigmaT.primitiveField();
        const scalarField& dsv = dSigmadTField.primitiveField();
        const scalarField& al = alpha1.primitiveField();
        const scalarField& Tc = T.primitiveField();
        const scalarField& Tm = matTliq.primitiveField();
        forAll(sig, celli)
        {
            if (al[celli] > 0.3 && Tc[celli] >= Tm[celli])
            {
                sigSum += sig[celli];
                dsSum += dsv[celli];
                nLiq += 1;
                sigLo = min(sigLo, sig[celli]);
                sigHi = max(sigHi, sig[celli]);
            }
        }
        reduce(sigSum, sumOp<scalar>());
        reduce(dsSum, sumOp<scalar>());
        reduce(nLiq, sumOp<scalar>());
        reduce(sigLo, minOp<scalar>());
        reduce(sigHi, maxOp<scalar>());
        if (Pstream::master())
        {
            scalar sigMean = 0, dsMean = 0;
            if (nLiq > 0)
            {
                sigMean = sigSum/nLiq;
                dsMean = dsSum/nLiq;
            }
            else if (sig.size())
            {
                sigMean = sig[0];
                dsMean = dsv[0];
                sigLo = sigMean;
                sigHi = sigMean;
            }
            Info<< "OxygenSigma: ppm = " << chamberOxygenPpm
                << "  t = " << runTime.value()
                << "  sigmaLiqMean = " << sigMean
                << "  dsigdTLiqMean = " << dsMean
                << "  sigmaLiqMin = " << sigLo
                << "  sigmaLiqMax = " << sigHi
                << "  nLiq = " << label(nLiq)
                << endl;

            const fileName dir(runTime.globalPath()/"postProcessing"/"oxygen");
            mkDir(dir);
            const fileName fn(dir/"sigma.dat");
            const bool isNew = !isFile(fn);
            std::ofstream os(fn.c_str(), std::ios::app);
            if (isNew)
            {
                os << "# time[s] chamberOxygenPpm aO_wt% "
                   << "sigmaLiqMean[N/m] dsigdTLiqMean[N/m/K] "
                   << "sigmaLiqMin[N/m] sigmaLiqMax[N/m] nLiquidCells\n"
                   << "# a_O = chamberOxygenPpm * 1e-4 (wt%, Sahoo 1 wt% standard state).\n"
                   << "# Means are over cells with alpha>0.3 and T>=Tliquidus. "
                   << "nLiquidCells = 0: cell 0 on the master "
                   << "(below the liquidus sigma is frozen at Tm).\n";
            }
            os.setf(std::ios::scientific);
            os.precision(8);
            os << runTime.value() << ' '
               << chamberOxygenPpm << ' ' << oxygenActivity << ' '
               << sigMean << ' ' << dsMean << ' '
               << sigLo << ' ' << sigHi << ' '
               << label(nLiq) << '\n';
        }
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
