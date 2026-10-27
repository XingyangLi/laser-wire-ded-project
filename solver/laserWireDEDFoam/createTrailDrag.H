// Hard-coded trailing-face contact line.
//
// The wire is a metal region, so a wall contact angle never acts on the gap.
// trailDrag (default off) holds alpha.metal = 1 and the feed velocity in a
// 1-3 cell shell on the trailing (+x) wire surface, from the wetted top
// downward a few cells. That shell moves down at the feed velocity. Cells
// outside it, including the pool, are left free.
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
        << "  (alpha and U held, pool outside the shell is free)" << nl
        << endl;
}
