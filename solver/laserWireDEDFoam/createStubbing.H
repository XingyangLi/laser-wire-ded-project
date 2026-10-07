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
//     buckling                 // optional, default off (needs enabled true)
//     {
//         enabled         true;
//         plane           auto;     // auto | feed | lateral (or direction (x y z))
//         endCondition    clampedPinned;   // feeder clamped, tip pinned (K 0.70)
//                                          // | pinnedPinned (K 1)
//         criticalStall   -1;       // stalled feed [m] that buckles the column;
//                                   // <= 0: Euler (see below)
//         gyrationRadius  R/2;      // radius of gyration of the wire section [m]
//         pathFactor      1;        // compressed wire length / free column length
//         absorbFraction  1;        // part of the post-critical stalled feed that
//                                   // goes into the bow inside the domain
//         maxAmplitude    1.5;      // bow amplitude cap [wire diameters] ...
//         maxSlope        0.2;      // ... and [x column length] (max axis slope
//                                   // ~4 A/L at the pinned end: 0.8)
//         maxLateralSpeed 2|Ufeed|; // cap of the commanded lateral speed [m/s]
//         responseTime    5e-4;     // amplitude follows its target [s]
//         releaseTime     1e-3;     // compression decay after contact loss [s]
//         springBack      true;     // elastic: the bow relaxes when released;
//                                   // false: the bent strand stays bent (plastic)
//         minColumnLength 4R;       // no buckling of shorter free columns
//         nBins           24;       // axial bins of the measured wire centreline
//     }
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
//
// Buckling (stubbing/buckling, default off): while the stall lasts the solid
// wire between the stub contact (pinned end, axial position sTip) and the
// domain inlet (clamped in the feeder guide, sIn) is a slender column of free
// length L = sIn - sTip under displacement-controlled compression. The stalled
// feed of the current contact S is the end shortening. Euler: P_cr =
// pi^2 E I/(K L)^2 with P = E A S/(pathFactor L) gives the critical stall
//     S_cr = pi^2 r_g^2 pathFactor/(K^2 L)      (r_g^2 = I/A, = R^2/4 solid)
// Beyond it the column bows in its first mode phi(xi), xi = (s - sTip)/L
// (clamped-pinned: sin(b xi) - xi sin(b), tan b = b; normalised to max 1) with
// the inextensible-elastica amplitude that takes up the excess feed:
//     A_target = sqrt(absorbFraction (S - S_cr) L / c),  c = 1/2 int phi'^2 dxi
// capped at min(maxAmplitude 2R, maxSlope L). The commanded amplitude A follows
// A_target (responseTime, |dA/dt| <= maxLateralSpeed). The solid-metal target
// velocity of the wire zone gets the lateral part dA/dt phi(xi) e_b (a pure
// shear field, divergence free), and the wire zone follows the bent axis, so
// the never-molten wire is bent by the same Carman-Kozeny sink that feeds it.
// Melting/VOF still owns liquid metal. Contact loss: S decays (releaseTime)
// and the bow springs back (springBack true) or stays (false).
// e_b (plane auto): inclined wire -> in its vertical plane, away from the
// plate; vertical / coaxial wire -> horizontal, normal to the scan direction.
// NOT a beam FE model: one mode shape, no axial wire stress, no contact with
// other metal, no plasticity except the springBack switch.
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

// --- wire buckling under the stall (stubbing/buckling, default off)
const dictionary bkDict(stubDict.subOrEmptyDict("buckling"));
const bool bkEnabled = stubEnabled && bkDict.getOrDefault<bool>("enabled", false);
const word bkPlane = bkDict.getOrDefault<word>("plane", "auto");
const word bkEnd = bkDict.getOrDefault<word>("endCondition", "clampedPinned");
const bool bkClamped = (bkEnd != "pinnedPinned");
const scalar bkCritUser = bkDict.getOrDefault<scalar>("criticalStall", -1);
const scalar bkGyr = bkDict.getOrDefault<scalar>("gyrationRadius", 0.5*wireRadius);
const scalar bkPathFactor = bkDict.getOrDefault<scalar>("pathFactor", 1.0);
const scalar bkAbsorb = bkDict.getOrDefault<scalar>("absorbFraction", 1.0);
const scalar bkMaxAmpD = bkDict.getOrDefault<scalar>("maxAmplitude", 1.5);
const scalar bkMaxSlope = bkDict.getOrDefault<scalar>("maxSlope", 0.2);
const scalar bkMaxSpeed = bkDict.getOrDefault<scalar>
(
    "maxLateralSpeed", max(2*mag(wireFeedVelocity), 1e-3)
);
const scalar bkResponse = bkDict.getOrDefault<scalar>("responseTime", 5e-4);
const scalar bkRelease = bkDict.getOrDefault<scalar>("releaseTime", 1e-3);
const bool bkSpringBack = bkDict.getOrDefault<bool>("springBack", true);
const scalar bkMinLength = bkDict.getOrDefault<scalar>("minColumnLength", 4*wireRadius);
const label bkNBins = max(bkDict.getOrDefault<label>("nBins", 24), label(4));

// preferred bow direction e_b (unit, normal to the wire axis)
auto bkPerp = [&](vector v) -> vector
{
    v -= (v & wireUp)*wireUp;
    const scalar m = mag(v);
    return (m > 1e-6) ? v/m : vector(Zero);
};
vector bkDir(Zero);
{
    const vector ez(0, 0, 1);
    vector sc(solidVelocity);
    if (mag(sc) < VSMALL) sc = vector(1, 0, 0);
    sc /= mag(sc);
    if (bkDict.found("direction"))
    {
        bkDir = bkPerp(bkDict.get<vector>("direction"));
    }
    else
    {
        const scalar sinIncl = mag(wireUp - (wireUp & ez)*ez);
        if (bkPlane != "lateral" && sinIncl > 0.1)
        {
            bkDir = bkPerp(ez);          // vertical plane of the wire, away from the plate
        }
        if (mag(bkDir) < 0.5) bkDir = bkPerp(wireUp ^ sc);   // normal to the scan direction
    }
    if (mag(bkDir) < 0.5) bkDir = bkPerp(vector(0, 1, 0));
    if (mag(bkDir) < 0.5) bkDir = bkPerp(vector(1, 0, 0));
}
const vector bkDir2(wireUp ^ bkDir);     // the other lateral direction (diagnostics)

// first-mode shape phi(xi), xi = 0 at the pinned stub tip, 1 at the clamped inlet
const scalar bkBeta = 4.4934094579090642;     // tan(b) = b
const scalar bkK = bkClamped ? 0.6992 : 1.0;  // effective-length factor
auto bkShapeRaw = [&](const scalar xi) -> scalar
{
    if (xi <= 0 || xi >= 1) return 0;
    return bkClamped
        ? Foam::sin(bkBeta*xi) - xi*Foam::sin(bkBeta)
        : Foam::sin(constant::mathematical::pi*xi);
};
scalar bkShapeMax = SMALL, bkArc = 0;
{
    const label n = 4000;
    for (label i = 0; i <= n; ++i) bkShapeMax = max(bkShapeMax, bkShapeRaw(scalar(i)/n));
    for (label i = 0; i < n; ++i)
    {
        const scalar dphi =
            (bkShapeRaw(scalar(i + 1)/n) - bkShapeRaw(scalar(i)/n))/bkShapeMax*n;
        bkArc += 0.5*sqr(dphi)/n;      // c = 1/2 int phi'^2 dxi (pi^2/4 for a sine)
    }
}
auto bkShape = [&](const scalar xi) -> scalar { return bkShapeRaw(xi)/bkShapeMax; };

// axial position of the domain inlet (highest wire-zone cell centre)
scalar bkSIn = -GREAT;
{
    const vectorField& Cc = mesh.C().primitiveField();
    forAll(Cc, c)
    {
        const vector d = Cc[c] - wireOrigin;
        const scalar s = (d & wireUp);
        if (mag(d - s*wireUp) <= wireZoneRadiusFactor*wireRadius) bkSIn = max(bkSIn, s);
    }
    reduce(bkSIn, maxOp<scalar>());
}

// buckling state (bkS, bkA, bkSTip, bkNEvents, bkMaxA restored with the stubbing state)
scalar bkS = 0;           // compression = stalled feed of the current contact [m]
scalar bkA = 0;           // commanded midspan bow amplitude [m]
scalar bkAdot = 0;        // its rate this step [m/s]
scalar bkATarget = 0;     // elastica target amplitude [m]
scalar bkSTip = -GREAT;   // axial position of the stub contact (pinned end) [m]
scalar bkL = 0;           // free column length sIn - sTip [m]
scalar bkCrit = 0;        // critical stall S_cr [m]
bool   bkOn = false;      // post-critical (buckled and loaded) this step
scalar bkNEvents = 0;     // buckling events
scalar bkMaxA = 0;        // largest commanded amplitude so far [m]
scalar stubSTip = GREAT;  // lowest axial position of a contact cell (this step)

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
    scalarList st(15, Zero);
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
                st[10] = col("bkStall");
                st[11] = col("bkAmp");
                st[12] = col("bkTipS");
                st[13] = col("bkEvents");
                st[14] = col("bkMaxAmp");
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
        if (bkEnabled)
        {
            bkS = st[10];
            bkA = st[11];
            bkSTip = (bkA > 0) ? st[12] : -GREAT;
            bkNEvents = st[13];
            bkMaxA = st[14];
        }
        Info<< "    restored state: stall factor " << stubStallFac << ", events "
            << stubNEvents << ", contact time " << stubContactTime << " s, stalled "
            << stubStalledLen << " m";
        if (bkEnabled)
        {
            Info<< ", buckling compression " << bkS << " m amplitude " << bkA << " m";
        }
        Info<< nl;
    }
    Info<< "    wire buckling: " << (bkEnabled ? "ON" : "off");
    if (bkEnabled)
    {
        Info<< " (plane " << bkPlane << ", e_b " << bkDir << ", " << bkEnd
            << " K " << bkK << ", criticalStall "
            << (bkCritUser > 0 ? Foam::name(bkCritUser) : word("Euler")) << nl
            << "        r_g " << bkGyr << " pathFactor " << bkPathFactor
            << " absorbFraction " << bkAbsorb << " maxAmplitude " << bkMaxAmpD
            << " D maxSlope " << bkMaxSlope << " maxLateralSpeed " << bkMaxSpeed
            << " responseTime " << bkResponse << " releaseTime " << bkRelease
            << " springBack " << bkSpringBack << " minColumnLength " << bkMinLength
            << nl << "        inlet s " << bkSIn << " m, shape c " << bkArc
            << ", Euler S_cr for L = 3 mm: "
            << sqr(constant::mathematical::pi*bkGyr)*bkPathFactor/(sqr(bkK)*3e-3)
            << " m)";
    }
    else if (bkDict.getOrDefault<bool>("enabled", false))
    {
        Info<< " (buckling{enabled true} ignored: stubbing is not enabled)";
    }
    Info<< nl << endl;
}
