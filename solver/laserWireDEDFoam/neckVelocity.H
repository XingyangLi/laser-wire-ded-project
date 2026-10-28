// Numerical speed ceiling on the trailing neck.
//
// At about 7 ms the 2-cell film crossed the top of the 19 um band. The
// speed there rose while the Courant number sat just above maxCo (0.4),
// so setDeltaT shortened the step by a few percent every iteration.
// Capping the speed keeps that Courant number under the limit on the
// fine cells. The ceiling is not a physical drag. phi is scaled with U
// so the next Courant evaluation sees the same limit.
if (linePinEnabled && linePinUmax > 0 && linePinZ0 > 0)
{
    const scalar uMax = linePinUmax;
    const scalar rMax =
        wireRadius + max(linePinWTop, scalar(0)) + scalar(4.0e-4);
    const scalar zLo = 0.3e-3;
    const scalar zHi = linePinZ0 + 0.6e-3;
    const vectorField& C = mesh.C().primitiveField();
    vectorField& Uc = U.primitiveFieldRef();
    label nClip = 0;

    forAll(Uc, celli)
    {
        const vector d = C[celli] - wireOrigin;
        const scalar sAx = d & wireUp;
        const vector rad = d - sAx*wireUp;
        if (rad.x() <= 0) continue;
        if (mag(rad) > rMax) continue;
        const scalar z = C[celli].z();
        if (z < zLo || z > zHi) continue;
        const scalar m = mag(Uc[celli]);
        if (m > uMax)
        {
            Uc[celli] *= uMax/m;
            ++nClip;
        }
    }

    scalarField& phif = phi.primitiveFieldRef();
    const scalarField& magSf = mesh.magSf().primitiveField();
    forAll(phif, facei)
    {
        const scalar uFace = mag(phif[facei])/max(magSf[facei], SMALL);
        if (uFace > uMax)
        {
            phif[facei] *= uMax/uFace;
        }
    }

    reduce(nClip, sumOp<label>());
    if (nClip > 0)
    {
        U.correctBoundaryConditions();
        if
        (
            runTime.timeIndex() <= 2
         || runTime.timeIndex() % max(contactInterval, 1) == 0
        )
        {
            Info<< "NeckU: clipped " << nClip
                << " trailing cells to " << uMax
                << " m/s (numerical ceiling)" << nl;
        }
    }
}

// ************************************************************************* //
