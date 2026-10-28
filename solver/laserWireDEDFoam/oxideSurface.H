// Trailing-neck oxide coverage, once per time step, before sigma and the
// contact line. See createOxideSkin.H. surface false: nothing happens.
//
// dynamic: the scalar is carried by the volume flux and relaxes toward the
// ppm strength on an exposed face. trailOnly restricts that growth to the
// trailing neck. Off that face it fades.
// fixed patch (dynamic false): coverage equals the ppm strength inside the
// trailing band and is zero elsewhere. The band is imposed. Alpha is not.
if (oxideSkinEnabled && oxideSurface && pimple.firstIter())
{
    const scalar dtOx = runTime.deltaTValue();
    scalarField& ox = oxideCoverage.primitiveFieldRef();
    const vectorField& Cc = mesh.C().primitiveField();
    const scalarField& Vp = mesh.V();
    const scalarField& aOx = alpha1.primitiveField();
    const scalar sat = oxideSkinStrength;
    const scalar tauG = max(oxideSkinGenTime, SMALL);
    const scalar tauL = max(oxideSkinLeaveTime, SMALL);
    vector trail(1, 0, 0);
    trail -= (trail & wireUp)*wireUp;
    const scalar mtTrail = mag(trail);
    if (mtTrail > SMALL) trail /= mtTrail;
    const scalar cosCut = Foam::cos(oxideSector);

    auto onTrail = [&](const label celli) -> bool
    {
        const vector d = Cc[celli] - wireOrigin;
        const scalar sAx = d & wireUp;
        const vector rad = d - sAx*wireUp;
        const scalar r = mag(rad);
        const scalar h = Foam::cbrt(max(Vp[celli], SMALL));
        if (sAx < oxideSkinZ0 || sAx > oxideSkinZ1) return false;
        if (r < wireRadius - 0.5*h) return false;
        if (r > wireRadius + oxideBand) return false;
        if (r > SMALL && (rad & trail) < cosCut*r) return false;
        return true;
    };

    if (oxideSkinDynamic)
    {
        oxideCoverage.correctBoundaryConditions();
        const volScalarField divOx(fvc::div(phi, oxideCoverage));
        const scalarField& dOx = divOx.primitiveField();
        const volVectorField gradOx(fvc::grad(alpha1));
        const vectorField& gOx = gradOx.primitiveField();
        forAll(ox, celli)
        {
            ox[celli] = max(min(ox[celli] - dtOx*dOx[celli], scalar(1)), scalar(0));
        }
        forAll(ox, celli)
        {
            const scalar h = Foam::cbrt(max(Vp[celli], SMALL));
            const bool exposed =
                mag(gOx[celli])*h > 0.25
             && aOx[celli] > 0.02
             && aOx[celli] < 0.98;
            const bool grow = exposed && (!oxideTrailOnly || onTrail(celli));
            if (grow)
            {
                ox[celli] += dtOx/tauG*(sat - ox[celli]);
            }
            else if (ox[celli] > 0)
            {
                ox[celli] -= dtOx/tauL*ox[celli];
            }
            ox[celli] = max(min(ox[celli], scalar(1)), scalar(0));
        }
    }
    else
    {
        forAll(ox, celli)
        {
            ox[celli] = onTrail(celli) ? sat : scalar(0);
        }
    }
    oxideCoverage.correctBoundaryConditions();

    if
    (
        runTime.timeIndex() <= 1
     || runTime.timeIndex() % max(oxideSkinInterval, 1) == 0
    )
    {
        scalar oxMax = 0, oxSum = 0, nOx = 0, nTrail = 0;
        forAll(ox, celli)
        {
            if (onTrail(celli)) nTrail += 1;
            if (ox[celli] > 1e-4)
            {
                oxMax = max(oxMax, ox[celli]);
                oxSum += ox[celli];
                nOx += 1;
            }
        }
        reduce(oxMax, maxOp<scalar>());
        reduce(oxSum, sumOp<scalar>());
        reduce(nOx, sumOp<scalar>());
        reduce(nTrail, sumOp<scalar>());
        Info<< "OxideSurface: "
            << (oxideSkinDynamic ? "growing" : "patch")
            << " sat " << sat
            << " oxMax " << oxMax
            << " oxMean " << (nOx > 0 ? oxSum/nOx : scalar(0))
            << " nOx " << nOx
            << " nTrail " << nTrail
            << " sigmaDrop " << oxideSigmaDrop
            << nl;
    }
}
