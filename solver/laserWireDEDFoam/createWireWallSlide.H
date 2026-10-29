// Contact-line hysteresis on the solid wire wall. Off unless
// wireSlide { enabled true; }.
//
// The angle condition on the wall (pinnedAlphaContactAngle) supplies no
// Young force while the apparent angle is inside [thetaR, thetaA], and
// clamps to the nearer limit outside it so the line can slip. This block
// is the momentum half: while the angle is inside the window, the contact
// cells are pulled toward the wire feed velocity, so a pinned line is
// dragged down with the wall. Outside the window that pull is off and the
// line slides. Alpha is not rewritten. There is no gas shell.
//
// oxygenTable is a model assumption, not a measured isotherm. Higher ppm
// stands for a stronger oxide skin: a lower receding angle and a larger
// pinning coefficient. Columns are ppm, thetaR [deg], thetaA [deg],
// Kpin [kg/m3/s].
const dictionary wireSlideDict(meltProperties.subOrEmptyDict("wireSlide"));
const bool wireSlideEnabled = wireSlideDict.getOrDefault<bool>("enabled", false);
const scalar wireSlideTau = wireSlideDict.getOrDefault<scalar>("tau", 1e-3);
const scalar wireSlidePpm = wireSlideDict.getOrDefault<scalar>("ppm", 0);
const scalar wireSlideGradMin = wireSlideDict.getOrDefault<scalar>("gradMin", 0.25);
const List<scalarList> wireSlideTable
(
    wireSlideDict.getOrDefault<List<scalarList>>
    (
        "oxygenTable",
        List<scalarList>()
    )
);
scalar wireSlideThetaR = 30;
scalar wireSlideThetaA = 90;
scalar wireSlideK = 1e8;
if (wireSlideEnabled)
{
    if (wireSlideTable.size() < 1)
    {
        FatalErrorInFunction
            << "wireSlide/oxygenTable is empty" << exit(FatalError);
    }
    const List<scalarList>& rows = wireSlideTable;
    for (const scalarList& row : rows)
    {
        if (row.size() < 4)
        {
            FatalErrorInFunction
                << "wireSlide/oxygenTable rows are ppm thetaR thetaA Kpin, got "
                << row << exit(FatalError);
        }
    }
    label iLo = 0;
    label iHi = rows.size() - 1;
    for (label i = 0; i < rows.size(); ++i)
    {
        if (rows[i][0] <= wireSlidePpm) iLo = i;
    }
    for (label i = 0; i < rows.size(); ++i)
    {
        if (rows[i][0] >= wireSlidePpm)
        {
            iHi = i;
            break;
        }
    }
    const scalar x0 = rows[iLo][0];
    const scalar x1 = rows[iHi][0];
    const scalar f = (iLo == iHi) ? 0 : (wireSlidePpm - x0)/max(x1 - x0, SMALL);
    wireSlideThetaR = rows[iLo][1] + f*(rows[iHi][1] - rows[iLo][1]);
    wireSlideThetaA = rows[iLo][2] + f*(rows[iHi][2] - rows[iLo][2]);
    wireSlideK = rows[iLo][3] + f*(rows[iHi][3] - rows[iLo][3]);
    if (wireSlideThetaA < wireSlideThetaR)
    {
        FatalErrorInFunction
            << "wireSlide advancing angle is below the receding angle" << nl
            << exit(FatalError);
    }
    Info<< "Wire slide: hysteresis on wireWall, ppm " << wireSlidePpm
        << " (model table) thetaR " << wireSlideThetaR
        << " deg thetaA " << wireSlideThetaA
        << " deg Kpin " << wireSlideK
        << " kg/m3/s, tau " << wireSlideTau
        << " s. Gap is not painted." << nl;
}
