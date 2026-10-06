// Multi-component statistics -> postProcessing/meltPool/components.dat
//  per component: metal volume in the domain outside the wire zone ("deposited",
//  incl. the pool), the part of it that never melted, and the same two numbers
//  in the solidified track behind the pool tail (x > poolTail + offset)
if (multiComp)
{
    const dictionary& stDictC = meltProperties.subOrEmptyDict("statistics");
    const label everyC = stDictC.getOrDefault<label>("interval", 10);
    const scalar offC = stDictC.getOrDefault<scalar>("beadProbeOffset", 3e-4);
    if (runTime.timeIndex() % max(everyC, 1) == 0 || runTime.writeTime())
    {
        const vectorField& C = mesh.C().primitiveField();
        const scalarField& V = mesh.V();
        scalar xTail = -GREAT;
        forAll(C, i)
        {
            if (alpha1[i] > 0.5 && liquidFraction[i] > 0.5) xTail = max(xTail, C[i].x());
        }
        reduce(xTail, maxOp<scalar>());
        const label nC = compNames.size();
        scalarList vDep(nC, 0), uDep(nC, 0), vTrk(nC, 0), uTrk(nC, 0), vWire(nC, 0), uWire(nC, 0);
        forAll(C, i)
        {
            const scalar a = max(min(alpha1[i], 1.0), 0.0);
            if (a < 1e-6) continue;
            const bool trk = (xTail > -GREAT) && (C[i].x() > xTail + offC);
            for (label k = 0; k < nC; ++k)
            {
                const scalar vc = a*cComp[k][i]*V[i];
                const scalar vu = a*uComp[k][i]*V[i];
                if (inWireZone[i] && meltHistory[i] < 0.5) { vWire[k] += vc; uWire[k] += vu; }
                else { vDep[k] += vc; uDep[k] += vu; }
                if (trk) { vTrk[k] += vc; uTrk[k] += vu; }
            }
        }
        for (label k = 0; k < nC; ++k)
        {
            reduce(vDep[k], sumOp<scalar>()); reduce(uDep[k], sumOp<scalar>());
            reduce(vTrk[k], sumOp<scalar>()); reduce(uTrk[k], sumOp<scalar>());
            reduce(vWire[k], sumOp<scalar>()); reduce(uWire[k], sumOp<scalar>());
        }
        Info<< "Components:";
        for (label k = 0; k < nC; ++k)
        {
            Info<< "  " << compNames[k] << " unmelted frac: deposit "
                << (vDep[k] > SMALL ? uDep[k]/vDep[k] : 0) << ", track "
                << (vTrk[k] > SMALL ? uTrk[k]/vTrk[k] : 0);
        }
        Info<< endl;
        if (Pstream::master())
        {
            const fileName dir(runTime.globalPath()/"postProcessing"/"meltPool");
            mkDir(dir);
            const fileName fn(dir/"components.dat");
            const bool isNew = !isFile(fn);
            std::ofstream os(fn.c_str(), std::ios::app);
            if (isNew)
            {
                os << "# time[s] poolTailX[m]";
                for (label k = 0; k < nC; ++k)
                {
                    const word& n = compNames[k];
                    os << " V" << n << "_wire[m3] U" << n << "_wire[m3]"
                       << " V" << n << "_dep[m3] U" << n << "_dep[m3]"
                       << " V" << n << "_track[m3] U" << n << "_track[m3]";
                }
                os << "\n";
            }
            os.precision(8);
            os << runTime.value() << ' ' << (xTail > -GREAT ? xTail : 0);
            for (label k = 0; k < nC; ++k)
            {
                os << ' ' << vWire[k] << ' ' << uWire[k] << ' ' << vDep[k] << ' ' << uDep[k]
                   << ' ' << vTrk[k] << ' ' << uTrk[k];
            }
            os << '\n';
        }
    }
}
