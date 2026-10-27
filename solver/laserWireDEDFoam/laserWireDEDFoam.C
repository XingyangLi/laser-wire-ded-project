/*---------------------------------------------------------------------------*\
  =========                 |
  \\      /  F ield         | OpenFOAM: The Open Source CFD Toolbox
   \\    /   O peration     |
    \\  /    A nd           | www.openfoam.com
     \\/     M anipulation  |
-------------------------------------------------------------------------------
    Copyright (C) 2011-2017 OpenFOAM Foundation
    Copyright (C) 2020 OpenCFD Ltd.
-------------------------------------------------------------------------------
License
    This file is part of OpenFOAM.

    OpenFOAM is free software: you can redistribute it and/or modify it
    under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    OpenFOAM is distributed in the hope that it will be useful, but WITHOUT
    ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
    FITNESS FOR A PARTICULAR PURPOSE.  See the GNU General Public License
    for more details.

    You should have received a copy of the GNU General Public License
    along with OpenFOAM.  If not, see <http://www.gnu.org/licenses/>.

Application
    laserWireDEDFoam

Group
    grpMultiphaseSolvers

Description
    Laser wire-feed directed energy deposition (LW-DED) solver, single track.
    Derived from interFoam (OpenFOAM.com v2406/v2412) via wireMeltFoam:
    two incompressible immiscible phases (metal + shielding gas), VOF/MULES
    interface capturing, plus
      - energy equation with enthalpy-porosity (Voller-Prakash) melting /
        solidification and liquid-fraction dependent conductivity,
      - Carman-Kozeny sink driving solid metal to a prescribed velocity:
        wire feed velocity inside the wire zone, substrate (scan) velocity
        elsewhere -> laboratory frame with fixed laser and moving substrate,
      - ray-traced (vertical beam, column march) laser surface heat flux
        deposited at the first metal/gas interface along the beam, with
        natural shadowing by the wire; Gaussian or top-hat profile,
      - liquid-only CSF surface tension with sigma(T), or optional
        Sahoo-Belton sigma(T, a_O) from chamberOxygenPpm, Marangoni stress
        using the matching dSigma/dT (sign can reverse at high oxygen),
        Clausius-Clapeyron recoil pressure, evaporative / radiative /
        convective free-surface heat loss, optional Boussinesq buoyancy,
      - an advected melt-history marker (fusion zone) and melt-pool / bead
        statistics written to postProcessing/meltPool/meltPool.dat,
      - optional rigid-wire stubbing model (meltProperties/stubbing): the
        feed of the solid wire and of the wireInlet stalls while solid,
        never-molten wire rests on solid support; contact / stalled feed /
        ball / bridge diagnostics in postProcessing/wireTransfer,
      - optional contact-line pinning (meltProperties/contactLine, default
        off): contact-angle hysteresis where the free surface meets solid
        substrate or, if pinWire is set, the unmelted wire. The window
        opens to a full pin once the metal at the line solidifies,
      - optional porosity (meltProperties/porosity, default off): enclosed
        gas is classified as entrapment, lack-of-fusion or keyhole and,
        once the metal shell freezes, locked against numerical filling.
        Counts, sizes and locations go to postProcessing/porosity.
        wireCavity also reports the open or closed gas cavity behind the
        wire (volume, depth, contact-line height),

    Modifications (C) 2026 laser_wire_ded project, GPL-3.0-or-later.

\*---------------------------------------------------------------------------*/

#include "fvCFD.H"
#include "dynamicFvMesh.H"
#include "syncTools.H"
#include "processorPolyPatch.H"
#include "CMULES.H"
#include "EulerDdtScheme.H"
#include "localEulerDdtScheme.H"
#include "CrankNicolsonDdtScheme.H"
#include "subCycle.H"
#include "immiscibleIncompressibleTwoPhaseMixture.H"
#include "incompressibleInterPhaseTransportModel.H"
#include "turbulentTransportModel.H"
#include "pimpleControl.H"
#include "fvOptions.H"
#include "CorrectPhi.H"
#include "fvcSmooth.H"
#include <map>
#include <algorithm>
#include <fstream>
#include <cmath>
#include <sstream>
#include <string>
#include <vector>
#include <functional>

// * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //

int main(int argc, char *argv[])
{
    argList::addNote
    (
        "Laser wire-feed DED solver (VOF + enthalpy-porosity melting,"
        " ray-traced laser surface flux, Marangoni, recoil, evaporation)."
    );

    #include "postProcess.H"

    #include "addCheckCaseOptions.H"
    #include "setRootCaseLists.H"
    #include "createTime.H"
    #include "createDynamicFvMesh.H"
    #include "initContinuityErrs.H"
    #include "createDyMControls.H"
    #include "createFields.H"
    #include "createAlphaFluxes.H"
    #include "initCorrectPhi.H"
    #include "createUfIfPresent.H"

    if (!LTS)
    {
        #include "CourantNo.H"
        #include "setInitialDeltaT.H"
    }

    // * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * * //
    Info<< "\nStarting time loop\n" << endl;

    while (runTime.run())
    {
        #include "readDyMControls.H"

        if (LTS)
        {
            #include "setRDeltaT.H"
        }
        else
        {
            #include "CourantNo.H"
            #include "alphaCourantNo.H"
            #include "setDeltaT.H"
            #include "capillaryDeltaT.H"
        }

        ++runTime;

        #include "updateWireZone.H"

        Info<< "Time = " << runTime.timeName() << nl << endl;

        // --- Pressure-velocity PIMPLE corrector loop
        while (pimple.loop())
        {
            if (pimple.firstIter() || moveMeshOuterCorrectors)
            {
                mesh.update();

                if (mesh.changing())
                {
                    // Do not apply previous time-step mesh compression flux
                    // if the mesh topology changed
                    if (mesh.topoChanging())
                    {
                        talphaPhi1Corr0.clear();
                    }

                    gh = (g & mesh.C()) - ghRef;
                    ghf = (g & mesh.Cf()) - ghRef;

                    MRF.update();


                    if (correctPhi)
                    {
                        // Calculate absolute flux
                        // from the mapped surface velocity
                        phi = mesh.Sf() & Uf();

                        #include "correctPhi.H"

                        // Make the flux relative to the mesh motion
                        fvc::makeRelative(phi, U);

                        mixture.correct();
                    }

                    if (checkMeshCourantNo)
                    {
                        #include "meshCourantNo.H"
                    }
                }
            }

            #include "alphaControls.H"
            #include "alphaEqnSubCycle.H"

            mixture.correct();

            #include "cWireEqn.H"

            // --- Energy equation with melting / solidification
            #include "TEqn.H"
            #include "updateSurfaceTension.H"
            #include "recoilPressure.H"
            #include "gasCavity.H"
            #include "contactLine.H"
            #include "porosity.H"

            if (pimple.frozenFlow())
            {
                continue;
            }

            #include "UEqn.H"

            // --- Pressure corrector loop
            while (pimple.correct())
            {
                #include "pEqn.H"
            }

            if (pimple.turbCorr())
            {
                turbulence->correct();
            }
        }

        #include "meltHistory.H"
        #include "meltPoolStats.H"
        #include "componentStats.H"
        #include "wireTransferStats.H"

        runTime.write();

        runTime.printExecutionTime(Info);
    }

    Info<< "End\n" << endl;

    return 0;
}


// ************************************************************************* //
