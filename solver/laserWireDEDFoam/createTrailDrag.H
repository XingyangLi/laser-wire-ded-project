// Hard-coded trailing-face contact line.
//
// The wire is a metal region, so a wall contact angle never acts on the gap.
// trailDrag (default off) moves a pinned line down the trailing (+x) face at
// the feed velocity. Below the line, a 1-3 cell shell is held at
// alpha.metal = 1 and at the feed velocity. Above the line, up to the
// wetted top the line started from, that same shell is held dry so the line
// cannot climb back. The flux is left alone: zeroing those faces made
// alpha unbounded. Cells outside the shell, including the pool, are left
// free: the outer wall of the gap is generated.
// ---------------------------------------------------------------------------

const dictionary trailDragDict(meltProperties.subOrEmptyDict("trailDrag"));
const bool trailDragEnabled =
    trailDragDict.getOrDefault<bool>("enabled", false);
const scalar trailDragRadial =
    max(trailDragDict.getOrDefault<scalar>("radialCells", 2), scalar(1));
const scalar trailDragAxial =
    max(trailDragDict.getOrDefault<scalar>("axialCells", 3), scalar(1));
const scalar trailDragSectorDeg =
    trailDragDict.getOrDefault<scalar>("sectorDeg", 75);
const scalar trailDragSector =
    trailDragSectorDeg*constant::mathematical::pi/180.0;
scalar trailDragZ0 = -GREAT;
scalar trailDragT0 = -GREAT;
bool trailDragReady = false;

if (trailDragEnabled)
{
    Info<< "TrailDrag: on  radialCells " << trailDragRadial
        << "  axialCells " << trailDragAxial
        << "  sector " << trailDragSectorDeg
        << " deg from +x"
        << "  (wet shell below the line, dry face above it,"
        << " pool outside the shell is free)" << nl
        << endl;
}
