// Mix metal properties per cell (rule of mixtures):
//  - multi-component: substrate + components (c<name> fields), Tsol/Tliq from
//    the liquidus table in the local Ni content if given
//  - two-metal: wire-material fraction cWire
if (multiComp)
{
    const label nC = compNames.size();
    scalarField& fCp = matCp.primitiveFieldRef();
    scalarField& fKs = matKs.primitiveFieldRef();
    scalarField& fKl = matKl.primitiveFieldRef();
    scalarField& fL = matL.primitiveFieldRef();
    scalarField& fTs = matTsol.primitiveFieldRef();
    scalarField& fTl = matTliq.primitiveFieldRef();
    scalarField& fSig = matSigma.primitiveFieldRef();
    scalarField& fDs = matDSigma.primitiveFieldRef();
    scalarField& fA = matA.primitiveFieldRef();
    forAll(fCp, celli)
    {
        scalar csum = 0;
        for (label i = 0; i < nC; ++i) csum += max(min(cComp[i][celli], 1.0), 0.0);
        const scalar sc = (csum > 1.0) ? 1.0/csum : 1.0;
        const scalar cs = max(1.0 - csum*sc, 0.0);
        scalar cp = cs*subP.cp, ks = cs*subP.ks, kl = cs*subP.kl, L = cs*subP.L;
        scalar Ts = cs*subP.Ts, Tl = cs*subP.Tl, sg = cs*subP.sigma, ds = cs*subP.dsig;
        scalar A = cs*subP.A, wNi = cs*subNi;
        for (label i = 0; i < nC; ++i)
        {
            const scalar ci = max(min(cComp[i][celli], 1.0), 0.0)*sc;
            const metalProps& p = compP[i];
            cp += ci*p.cp; ks += ci*p.ks; kl += ci*p.kl; L += ci*p.L;
            Ts += ci*p.Ts; Tl += ci*p.Tl; sg += ci*p.sigma; ds += ci*p.dsig;
            A += ci*p.A; wNi += ci*compNi[i];
        }
        // Unmixed strands: keep the dominant component's own melting range
        // (Fe stays at 1811 K) until the cell is actually mixed below threshold.
        bool usedCompLiq = false;
        if (liquidusUnmixedThr < GREAT - 1)
        {
            label iMax = -1;
            scalar cMax = 0;
            for (label i = 0; i < nC; ++i)
            {
                const scalar ci = max(min(cComp[i][celli], 1.0), 0.0)*sc;
                if (ci > cMax) { cMax = ci; iMax = i; }
            }
            if (iMax >= 0 && cMax >= liquidusUnmixedThr)
            {
                Ts = compP[iMax].Ts;
                Tl = compP[iMax].Tl;
                usedCompLiq = true;
            }
        }
        if (useLiqTable && !usedCompLiq)
        {
            const label nT = tabNi.size();
            scalar w = max(min(wNi, tabNi[nT-1]), tabNi[0]);
            label j = 0;
            while (j < nT - 2 && w > tabNi[j+1]) ++j;
            const scalar f = (w - tabNi[j])/max(tabNi[j+1] - tabNi[j], SMALL);
            Ts = tabTs[j] + f*(tabTs[j+1] - tabTs[j]);
            Tl = tabTl[j] + f*(tabTl[j+1] - tabTl[j]);
        }
        // Lower solid conductivity between unmelted strand pieces (contact)
        if (unmeltedKFactor < 1.0 - SMALL)
        {
            scalar uSum = 0;
            for (label i = 0; i < nC; ++i)
            {
                uSum += max(min(uComp[i][celli], 1.0), 0.0);
            }
            // solid, still-unmelted wire metal
            if (uSum > 0.3)
            {
                ks *= unmeltedKFactor;
            }
        }
        fCp[celli] = cp; fKs[celli] = ks; fKl[celli] = kl; fL[celli] = L;
        fTs[celli] = Ts; fTl[celli] = max(Tl, Ts + 1.0); fSig[celli] = sg;
        fDs[celli] = ds; fA[celli] = A;
    }
    matCp.correctBoundaryConditions(); matKs.correctBoundaryConditions();
    matKl.correctBoundaryConditions(); matL.correctBoundaryConditions();
    matTsol.correctBoundaryConditions(); matTliq.correctBoundaryConditions();
    matSigma.correctBoundaryConditions(); matDSigma.correctBoundaryConditions();
    matA.correctBoundaryConditions();
}
else
{
    const scalarField& c = cWire.primitiveField();
    auto mix = [&](volScalarField& f, scalar vs, scalar vw)
    {
        if (twoMetals)
        {
            f.primitiveFieldRef() = vs + max(min(c, 1.0), 0.0)*(vw - vs);
        }
        else
        {
            f.primitiveFieldRef() = vs;
        }
        f.correctBoundaryConditions();
    };
    mix(matCp, subP.cp, wireP.cp);
    mix(matKs, subP.ks, wireP.ks);
    mix(matKl, subP.kl, wireP.kl);
    mix(matL, subP.L, wireP.L);
    mix(matTsol, subP.Ts, wireP.Ts);
    mix(matTliq, subP.Tl, wireP.Tl);
    mix(matSigma, subP.sigma, wireP.sigma);
    mix(matDSigma, subP.dsig, wireP.dsig);
    mix(matA, subP.A, wireP.A);
}
