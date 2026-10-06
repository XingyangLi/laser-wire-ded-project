// ---------------------------------------------------------------------------
// Multi-component option (meltProperties/components, enabled true):
// N wire components (e.g. Fe, Ni strands) + the substrate alloy as background.
//   c<name>  volume (= mass, single VOF density) fraction of component <name>
//            in the metal, conservatively transported with the MULES flux;
//            c_substrate = 1 - sum(c_i)
//   u<name>  fraction of the metal that is component <name> AND has never
//            been molten (unmelted wire marker; u_i <= c_i, reset to 0 when the
//            cell is liquid, transported like c_i)
// Properties: rule of mixtures over (substrate, components).
// Tsolidus/Tliquidus: rule of mixtures, or (liquidusTable) interpolated in the
// local Ni content wNi = c_sub*wNi_sub + sum(c_i*wNi_i) [wt%] from a
// tabulated binary (Fe-Ni) phase diagram.
// cWire (existing field) is kept as sum(c_i) for the bead/dilution statistics.
// ---------------------------------------------------------------------------
const dictionary compDict(meltProperties.subOrEmptyDict("components"));
const bool multiComp = compDict.getOrDefault<bool>("enabled", false);
wordList compNames;
List<metalProps> compP;
scalarList compNi;
const scalar subNi = compDict.getOrDefault<scalar>("substrateNi", 0.0);
const bool meltedFollowsSubstrate =
    compDict.getOrDefault<bool>("meltedFollowsSubstrate", false);
const scalar uMeltFl = compDict.getOrDefault<scalar>("unmeltedResetFl", 0.5);
const bool wireStubbing = compDict.getOrDefault<bool>("wireStubbing", false);
const scalar stubContactDist = compDict.getOrDefault<scalar>("stubContactDist", 1e-4);
// If max(c_i) exceeds this, keep that component's own Tsol/Tliq instead of the
// Fe-Ni table (so a nearly-pure Fe strand stays at Tl=1811 K until mixed).
const scalar liquidusUnmixedThr =
    compDict.getOrDefault<scalar>("liquidusUnmixedThreshold", GREAT);
// Extra conductivity reduction in solid unmelted-wire cells (strand contact).
const scalar unmeltedKFactor =
    compDict.getOrDefault<scalar>("unmeltedKFactor", 1.0);
scalarList tabNi, tabTs, tabTl;
bool useLiqTable = false;
PtrList<volScalarField> cComp;
PtrList<volScalarField> uComp;
if (multiComp)
{
    compNames = compDict.get<wordList>("names");
    compP.setSize(compNames.size());
    compNi.setSize(compNames.size());
    forAll(compNames, i)
    {
        const dictionary& d = compDict.subDict(compNames[i]);
        compP[i] = metalProps
        {
            d.get<scalar>("cp"), d.get<scalar>("k"), d.get<scalar>("kLiquid"),
            d.get<scalar>("L"), d.get<scalar>("Tsolidus"), d.get<scalar>("Tliquidus"),
            d.get<scalar>("sigma"), d.get<scalar>("dSigmadT"), d.get<scalar>("absorptivity")
        };
        compNi[i] = d.getOrDefault<scalar>("Ni", 0.0);
        cComp.append
        (
            new volScalarField
            (
                IOobject("c" + compNames[i], runTime.timeName(), mesh,
                         IOobject::MUST_READ, IOobject::AUTO_WRITE),
                mesh
            )
        );
        uComp.append
        (
            new volScalarField
            (
                IOobject("u" + compNames[i], runTime.timeName(), mesh,
                         IOobject::MUST_READ, IOobject::AUTO_WRITE),
                mesh
            )
        );
        Info<< "Component " << compNames[i] << ": cp " << compP[i].cp
            << " k " << compP[i].ks << "/" << compP[i].kl << " L " << compP[i].L
            << " Ts/Tl " << compP[i].Ts << "/" << compP[i].Tl
            << " sigma " << compP[i].sigma << " dsig " << compP[i].dsig
            << " A " << compP[i].A << " Ni " << compNi[i] << " wt%" << nl;
    }
    if (compDict.found("liquidusTable"))
    {
        // list of (wtNi Tsolidus Tliquidus), ascending in wtNi
        const List<Vector<scalar>> tab(compDict.get<List<Vector<scalar>>>("liquidusTable"));
        tabNi.setSize(tab.size()); tabTs.setSize(tab.size()); tabTl.setSize(tab.size());
        forAll(tab, j) { tabNi[j] = tab[j].x(); tabTs[j] = tab[j].y(); tabTl[j] = tab[j].z(); }
        useLiqTable = tab.size() >= 2;
    }
    Info<< "Multi-component model: " << compNames.size() << " wire components + substrate "
        << "(Ni " << subNi << " wt%), liquidus "
        << (useLiqTable ? "from table (local wt% Ni)" : "rule of mixtures")
        << ", liquidusUnmixedThreshold " << liquidusUnmixedThr
        << ", unmeltedKFactor " << unmeltedKFactor
        << ", meltedFollowsSubstrate " << meltedFollowsSubstrate
        << ", wireStubbing " << wireStubbing << " (contact " << stubContactDist << " m)" << nl << endl;
}
