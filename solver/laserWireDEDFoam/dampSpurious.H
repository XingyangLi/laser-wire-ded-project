// Imposed numerical damper. A sharp corner or a newly opened gas cell
// can throw the velocity, the Courant number sticks just above maxCo, and
// setDeltaT then shrinks the step to nothing. Interface cells and their
// neighbours are held at or below 4 m/s, which is far above the wire feed
// and inside the capillary Courant number on a few-micrometre cell.
{
    const scalar Ucap = 4.0;
    vectorField& Uc = U.primitiveFieldRef();
    const scalarField& al = alpha1.primitiveField();
    const labelListList& cells = mesh.cellCells();
    scalarField factor(mesh.nCells(), 1.0);
    label nClip = 0;
    forAll(Uc, celli)
    {
        bool near = (al[celli] > 0.02 && al[celli] < 0.98);
        if (!near)
        {
            const labelList& nb = cells[celli];
            forAll(nb, ni)
            {
                const scalar an = al[nb[ni]];
                if (an > 0.02 && an < 0.98)
                {
                    near = true;
                    break;
                }
            }
        }
        if (!near) continue;
        const scalar magU = mag(Uc[celli]);
        if (magU > Ucap)
        {
            factor[celli] = Ucap/magU;
            Uc[celli] *= factor[celli];
            ++nClip;
        }
    }
    reduce(nClip, sumOp<label>());
    if (nClip && (runTime.timeIndex() % 400 == 0))
    {
        Info<< "SpuriousDamping: clipped " << nClip
            << " interface cells to " << Ucap
            << " m/s (imposed)" << nl;
    }
    if (nClip)
    {
        U.correctBoundaryConditions();
        // Scale only the faces of clipped cells. Replacing phi entirely
        // is not divergence-free and the bead drains out of the domain.
        scalarField& ph = phi.primitiveFieldRef();
        const labelUList& own = mesh.owner();
        const labelUList& nei = mesh.neighbour();
        forAll(nei, facei)
        {
            ph[facei] *= min(factor[own[facei]], factor[nei[facei]]);
        }
        forAll(phi.boundaryFieldRef(), patchi)
        {
            fvsPatchScalarField& pb = phi.boundaryFieldRef()[patchi];
            const labelUList& faceCells = mesh.boundary()[patchi].faceCells();
            forAll(pb, facei)
            {
                pb[facei] *= factor[faceCells[facei]];
            }
        }
    }
}
