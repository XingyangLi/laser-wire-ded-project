    MRF.correctBoundaryVelocity(U);

    #include "marangoni.H"
    #include "oxideSkin.H"
    #include "oxideAngleForce.H"

    fvVectorMatrix UEqn
    (
        fvm::ddt(rho, U) + fvm::div(rhoPhi, U)
      + MRF.DDt(rho, U)
      + turbulence->divDevRhoReff(rho, U)
        // Carman-Kozeny sink -Kmushy (U - Usolid), plus the optional
        // contact-line pin -Kcontact (U - Ucontact). Ucontact equals Usolid
        // on the substrate line. On the internal wire it is the head frame
        // (0) or the feed velocity, see contactLine.H. On the true wire
        // wall, wireWallDrag.H sets it to the feed while the trailing line
        // sits inside the hysteresis window. Kcontact = 0 leaves this
        // identical to -Kmushy (U - Usolid).
        // Oxide skin (default off): -laplacian(muOxide, U) is an implicit
        // interfacial viscosity, and -Koxide (U - Ukeep) damps only the
        // radial part. mu = 0 and K = 0 leave both terms absent.
      - fvm::laplacian(muOxide, U)
      + fvm::Sp(Kmushy + Kcontact + Koxide, U)
     ==
        Kmushy*Usolid
      + Kcontact*Ucontact
      + Koxide*Ukeep
      + Fmarangoni
      + Foxide
      + Fbuoy
      + Fcontact
      + fvOptions(rho, U)
    );

    UEqn.relax();

    fvOptions.constrain(UEqn);

    if (pimple.momentumPredictor())
    {
        solve
        (
            UEqn
         ==
            fvc::reconstruct
            (
                (
                    stForcef
                  - ghf*fvc::snGrad(rho)
                  - fvc::snGrad(p_rgh)
                ) * mesh.magSf()
            )
        );

        fvOptions.correct(U);
    }
