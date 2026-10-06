// Advected melt-history marker: 1 for metal that has been molten (fusion
// zone / deposited bead), carried with the moving substrate.
{
    fvScalarMatrix mEqn
    (
        fvm::ddt(meltHistory)
      + fvm::div(phi, meltHistory, "div(phi,meltHistory)")
      - fvm::Sp(fvc::div(phi), meltHistory)
    );
    mEqn.solve();
    scalarField& m = meltHistory.primitiveFieldRef();
    forAll(m, celli)
    {
        scalar v = max(min(m[celli], 1.0), 0.0);
        if (alpha1[celli]*liquidFraction[celli] > 0.5) v = 1.0;
        m[celli] = v;
    }
    meltHistory.correctBoundaryConditions();

    // multi-component: unmelted-wire markers are cleared irreversibly where the
    // metal of the cell is (mostly) liquid. A pure-Fe cell is liquid only above
    // its own (Fe) liquidus, so a solid Fe strand piece keeps u_Fe = c_Fe.
    if (multiComp)
    {
        forAll(uComp, i)
        {
            scalarField& u = uComp[i].primitiveFieldRef();
            forAll(u, celli)
            {
                if (alpha1[celli] > 1e-3 && liquidFraction[celli] > uMeltFl) u[celli] = 0;
            }
            uComp[i].correctBoundaryConditions();
        }
    }
}
