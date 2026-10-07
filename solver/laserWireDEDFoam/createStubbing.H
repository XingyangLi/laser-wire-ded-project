// ---------------------------------------------------------------------------
// Rigid-wire stubbing model + wire-transfer diagnostics
// (meltProperties/stubbing, default OFF; nothing changes without the dict)
//
// stubbing
// {
//     enabled         true;    // stall the wire feed on solid-solid contact
//     wireFlMax       0.5;     // wire metal counts as solid below this liquid fraction
//     supportFlMax    0.5;     // substrate/deposit counts as solid support below this
//     contactDist     1.8e-4;  // contact = solid wire cell centre less than this above
//                              // the top solid support cell centre of its column
//     minLength       2.4e-4;  // ... with at least this much contiguous solid unmelted
//                              // wire metal above it (ignores loose strand fragments)
//     minContactCells 1;
//     responseTime    5e-4;    // feed drive response (s): stall factor relaxes
//                              // exponentially to 0 (contact) or 1 (free)
//     dragContact     true;    // contact cells move with the part (tangential slide)
//     useFloor        false;   // also count stubFloorZ (components) as solid support
//     diagRadius      1.5e-3;  // horizontal radius about the wire axis for the
//                              // transfer diagnostics (ball / bridge / gap)
//     writeStats      true;    // postProcessing/wireTransfer/wireTransfer.dat
// }
//
// Physics: the never-molten wire is a rigid rod pushed by the feeder. When its
// solid tip rests on SOLID substrate/deposit (also through a pool to the solid
// pool bottom) it cannot advance: the axial feed of the whole solid wire AND of
// the wireInlet patch is multiplied by a stall factor (-> 0). The feed that the
// drive could not push in is counted as "stalled feed" (length and metal volume;
// in reality it buckles the wire / slips in the drive rolls). Contact cells are
// dragged with the moving part, so the stub tip slides/bends with the substrate
// instead of penetrating it. When the contacting metal melts the stall releases.
// The wireInlet U boundary must be a plain fixedValue (generate_case.py
// --stubbing writes it) so that the solver can set it; with another type the
// stall is applied in the domain only (warning).
// ---------------------------------------------------------------------------
const bool stubDictFound = meltProperties.found("stubbing");
const dictionary stubDict(meltProperties.subOrEmptyDict("stubbing"));
const bool stubEnabled = stubDict.getOrDefault<bool>("enabled", false);
const bool stubStats = stubDict.getOrDefault<bool>("writeStats", stubDictFound);
const scalar stubWireFlMax = stubDict.getOrDefault<scalar>("wireFlMax", 0.5);
const scalar stubSupportFlMax = stubDict.getOrDefault<scalar>("supportFlMax", 0.5);
const scalar stubContactDistNew = stubDict.getOrDefault<scalar>("contactDist", 1.8e-4);
const scalar stubMinLength = stubDict.getOrDefault<scalar>("minLength", 2.4e-4);
const label stubMinCells = stubDict.getOrDefault<label>("minContactCells", 1);
const scalar stubResponseTime = stubDict.getOrDefault<scalar>("responseTime", 5e-4);
const bool stubDragContact = stubDict.getOrDefault<bool>("dragContact", true);
const bool stubUseFloor = stubDict.getOrDefault<bool>("useFloor", false);
const scalar stubDiagRadius = stubDict.getOrDefault<scalar>("diagRadius", 1.5e-3);

// state (restored from the last wireTransfer.dat line at or before the start time)
scalar stubStallFac = 1.0;        // 1 = free feed, 0 = fully stalled
bool   stubWasOn = false;
scalar stubNEvents = 0;
scalar stubContactTime = 0;       // total time in solid-solid contact [s]
scalar stubEventStart = -1;
scalar stubFirstTime = -1;        // first stub contact [s]
scalar stubStalledLen = 0;        // feed length the drive could not push in [m]
scalar stubStalledVol = 0;        // ... as wire metal volume [m3]
scalar stubFedLen = 0;            // wire length actually fed [m]
scalar stubFedVol = 0;            // wire metal volume actually fed [m3]
scalar stubInletMetalArea = 0;    // metal area of the wireInlet patch [m2]
label  stubNCells = 0;            // contact cells (this step)
scalar stubArea = 0;              // contact area (columns x column area) [m2]
scalar stubSupZ = -GREAT;         // highest solid support under a contact
scalar stubFeedFac = 1.0;         // feed ramp factor (this step)
bool   stubStartup = true;        // first include (construction): no accumulation
boolList stubContact(mesh.nCells(), false);

const label stubInletPatch = mesh.boundaryMesh().findPatchID("wireInlet");
bool stubInletControlled = false;
if (stubInletPatch >= 0)
{
    stubInletControlled = (U.boundaryField()[stubInletPatch].type() == "fixedValue");
}

// never-molten wire metal in cell c (multi-component: unmelted markers;
// otherwise wire alloy that has never been molten)
auto lwdUnmeltedWire = [&](const label c) -> bool
{
    if (multiComp)
    {
        scalar uSum = 0;
        forAll(uComp, i) uSum += uComp[i][c];
        return uSum > 0.5;
    }
    return cWire[c] > 0.5 && meltHistory[c] < 0.5;
};

if (stubDictFound)
{
    Info<< "Stubbing model (rigid wire, feed stall on solid-solid contact): "
        << (stubEnabled ? "ON" : "off (diagnostics only)") << nl
        << "    wireFlMax " << stubWireFlMax << " supportFlMax " << stubSupportFlMax
        << " contactDist " << stubContactDistNew << " minLength " << stubMinLength
        << " minContactCells " << stubMinCells << " responseTime " << stubResponseTime
        << " dragContact " << stubDragContact << " useFloor " << stubUseFloor
        << " diagRadius " << stubDiagRadius << nl
        << "    wireInlet patch " << (stubInletPatch >= 0 ? "found" : "NOT found")
        << ", U type fixedValue (solver-controlled feed): " << stubInletControlled << nl;
    if (stubEnabled && !stubInletControlled)
    {
        Info<< "    WARNING: wireInlet U is not a plain fixedValue: the stall acts in the"
            << " domain only, the inlet keeps feeding" << nl;
    }

    // --- restore the accumulated state (restart from latestTime)
    scalarList st(10, Zero);
    if (Pstream::master())
    {
        const fileName fn
        (
            runTime.globalPath()/"postProcessing"/"wireTransfer"/"wireTransfer.dat"
        );
        std::ifstream is(fn.c_str());
        if (is.good())
        {
            std::string line;
            std::vector<std::string> hdr;
            std::vector<double> best;
            const double t0 = runTime.value() + 1e-12;
            while (std::getline(is, line))
            {
                if (line.empty()) continue;
                if (line[0] == '#')
                {
                    std::istringstream hs(line.substr(1));
                    std::string tok;
                    hdr.clear();
                    while (hs >> tok)
                    {
                        const auto p = tok.find('[');
                        hdr.push_back(p == std::string::npos ? tok : tok.substr(0, p));
                    }
                    continue;
                }
                std::istringstream ls(line);
                std::vector<double> v;
                double x;
                while (ls >> x) v.push_back(x);
                if (!v.empty() && v.size() == hdr.size() && v[0] <= t0) best = v;
            }
            if (!best.empty())
            {
                auto col = [&](const char* n) -> double
                {
                    for (size_t k = 0; k < hdr.size(); ++k) if (hdr[k] == n) return best[k];
                    return 0.0;
                };
                st[0] = 1;
                st[1] = col("stallFactor");
                st[2] = col("stubbed");
                st[3] = col("nStubEvents");
                st[4] = col("contactTime");
                st[5] = col("firstStubTime");
                st[6] = col("stalledLength");
                st[7] = col("stalledVolume");
                st[8] = col("fedLength");
                st[9] = col("fedVolume");
            }
        }
    }
    Pstream::listCombineReduce(st, plusEqOp<scalar>());
    if (st[0] > 0.5)
    {
        stubStallFac = st[1];
        stubWasOn = st[2] > 0.5;
        stubNEvents = st[3];
        stubContactTime = st[4];
        stubFirstTime = st[5];
        stubStalledLen = st[6];
        stubStalledVol = st[7];
        stubFedLen = st[8];
        stubFedVol = st[9];
        Info<< "    restored state: stall factor " << stubStallFac << ", events "
            << stubNEvents << ", contact time " << stubContactTime << " s, stalled "
            << stubStalledLen << " m" << nl;
    }
    Info<< endl;
}
