// Drag a pinned contact line with the wire wall. See createWireWallSlide.H.
// Alpha is left alone. Off leaves the momentum equation unchanged.
{
    if (wireSlideEnabled)
    {
        const label patchi = mesh.boundaryMesh().findPatchID("wireWall");
        if (patchi < 0)
        {
            FatalErrorInFunction
                << "wireSlide is on but patch wireWall is missing"
                << exit(FatalError);
        }

        const scalar ramp = min
        (
            max(runTime.value()/max(wireSlideTau, SMALL), scalar(0)),
            scalar(1)
        );
        const scalar Keff = ramp*wireSlideK;
        const scalar radToDeg = 180.0/constant::mathematical::pi;
        const vectorField nf(mesh.boundary()[patchi].nf());
        const labelUList& faceCells = mesh.boundary()[patchi].faceCells();
        const vectorField gradAlpha(fvc::grad(alpha1)().primitiveField());
        const vectorField& C = mesh.C().primitiveField();
        const scalarField& Vc = mesh.V();

        // The triple line is the top of the wetted trailing wall, not every
        // mixed cell down the wire. Dragging the whole film shears the bead
        // and leaves the centre-plane line where it was.
        scalar zTop = -GREAT;
        forAll(nf, facei)
        {
            const label celli = faceCells[facei];
            const vector radial = C[celli] - wireOrigin;
            const scalar sAx = radial & wireUp;
            const vector rad = radial - sAx*wireUp;
            if (rad.x() <= 0) continue;
            if (alpha1[celli] > 0.5) zTop = max(zTop, C[celli].z());
        }
        reduce(zTop, maxOp<scalar>());
        const scalar band = 1.5e-4;

        scalar nPin = 0, nSlide = 0;
        scalar zPinMin = GREAT, zPinMax = -GREAT;

        forAll(nf, facei)
        {
            const label celli = faceCells[facei];
            const vector radial = C[celli] - wireOrigin;
            const scalar sAx = radial & wireUp;
            const vector rad = radial - sAx*wireUp;
            // Trailing face only. The leading side keeps the angle condition
            // and is not velocity-locked.
            if (rad.x() <= 0) continue;
            if (zTop < 0) continue;
            const scalar z = C[celli].z();
            if (z < zTop - band || z > zTop + 0.5*band) continue;

            const scalar a = alpha1[celli];
            // Gas above the line is not the attachment.
            if (a < 0.2) continue;
            // A skinned wall face has no adhesion. The non-wetting angle
            // on that face is what keeps liquid off the wire. The bare
            // triple line below the skin is still dragged with the feed.
            if (oxideSkinEnabled && oxideCoverage[celli] > 0.5)
            {
                nSlide += 1;
                continue;
            }
            const scalar h = Foam::cbrt(max(Vc[celli], SMALL));
            const scalar magG = mag(gradAlpha[celli]);

            bool pinned = true;
            if (magG*h >= wireSlideGradMin)
            {
                const vector nHat = gradAlpha[celli]/magG;
                const scalar cang = max(min(nHat & nf[facei], scalar(1)), scalar(-1));
                const scalar apparent = ::acos(cang)*radToDeg;
                pinned = apparent >= wireSlideThetaR && apparent <= wireSlideThetaA;
            }

            if (pinned)
            {
                if (Keff > 0)
                {
                    Kcontact[celli] = max(Kcontact[celli], Keff);
                    Ucontact[celli] = wireFeedVelocity;
                }
                zPinMin = min(zPinMin, z);
                zPinMax = max(zPinMax, z);
                nPin += 1;
            }
            else
            {
                nSlide += 1;
            }
        }

        reduce(nPin, sumOp<scalar>());
        reduce(nSlide, sumOp<scalar>());
        reduce(zPinMin, minOp<scalar>());
        reduce(zPinMax, maxOp<scalar>());

        if
        (
            runTime.timeIndex() <= 2
         || runTime.timeIndex() % max(contactInterval, 1) == 0
        )
        {
            Info<< "WireSlide: ppm " << wireSlidePpm
                << "  thetaR " << wireSlideThetaR
                << "  thetaA " << wireSlideThetaA
                << "  ramp " << ramp
                << "  zTop " << zTop*1e3
                << " mm  pinned " << nPin
                << "  sliding " << nSlide
                << "  zPin "
                << (nPin > 0 ? zPinMin*1e3 : 0)
                << ".."
                << (nPin > 0 ? zPinMax*1e3 : 0)
                << " mm  feed " << wireFeedVelocity.z()
                << "  (drag imposed while pinned, meniscus is free)"
                << nl;
        }
    }
}

// ************************************************************************* //
