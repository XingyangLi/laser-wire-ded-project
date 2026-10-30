// ---------------------------------------------------------------------------
// Gas entry behind a contact line dragged by the wire (meltProperties/slitEntry).
//
// Imposed numerical model, not a painted gap. The pinned line is moved down
// at the feed from the generated crest. Nothing is opened until that line
// sits further below the crest than the ppm threshold. Higher ppm: stronger
// pin, smaller threshold, faster entry. The metal removed from the opened
// cells is put back into neighbouring liquid, then into the free surface.
// Alloy sigma is not changed.
//
// Columns: ppm threshold[m] entryRate[m/s] gapMouth[m] gapRoot[m]
// ---------------------------------------------------------------------------

const dictionary slitEntryDict(meltProperties.subOrEmptyDict("slitEntry"));
const bool slitEntryEnabled = slitEntryDict.getOrDefault<bool>("enabled", false);
scalar slitThresh = 4e-5;
scalar slitRate = 0.04;
scalar slitGapMouth = 6.5e-5;
scalar slitGapRoot = 3.5e-5;
const scalar slitSpan = slitEntryDict.getOrDefault<scalar>("depthSpan", 0.35e-3);
// Imposed line height and the front gas has reached. -1 until the crest
// has been measured. Both live for the run; they are not a field.
scalar slitZpin = -1;
scalar slitZfront = -1;

if (slitEntryEnabled)
{
    const List<scalarList> slitTable
    (
        slitEntryDict.getOrDefault<List<scalarList>>
        (
            "oxygenTable",
            List<scalarList>()
        )
    );
    const scalar ppm = slitEntryDict.getOrDefault<scalar>("ppm", 300);
    if (slitTable.size())
    {
        for (const scalarList& row : slitTable)
        {
            if (row.size() < 5)
            {
                FatalErrorInFunction
                    << "slitEntry/oxygenTable rows are ppm threshold "
                    << "entryRate gapMouth gapRoot, got " << row << nl
                    << exit(FatalError);
            }
        }
        label iLo = 0;
        label iHi = slitTable.size() - 1;
        for (label i = 0; i < slitTable.size(); ++i)
        {
            if (slitTable[i][0] <= ppm) iLo = i;
        }
        for (label i = 0; i < slitTable.size(); ++i)
        {
            if (slitTable[i][0] >= ppm)
            {
                iHi = i;
                break;
            }
        }
        const scalar x0 = slitTable[iLo][0];
        const scalar x1 = slitTable[iHi][0];
        const scalar f =
            (iLo == iHi) ? 0 : (ppm - x0)/max(x1 - x0, SMALL);
        slitThresh = slitTable[iLo][1] + f*(slitTable[iHi][1] - slitTable[iLo][1]);
        slitRate = slitTable[iLo][2] + f*(slitTable[iHi][2] - slitTable[iLo][2]);
        slitGapMouth = slitTable[iLo][3] + f*(slitTable[iHi][3] - slitTable[iLo][3]);
        slitGapRoot = slitTable[iLo][4] + f*(slitTable[iHi][4] - slitTable[iLo][4]);
    }
    slitThresh = max(slitThresh, scalar(0));
    slitRate = max(slitRate, scalar(0));
    slitGapMouth = max(slitGapMouth, scalar(1e-5));
    slitGapRoot = max(min(slitGapRoot, slitGapMouth), scalar(1e-5));

    Info<< "SlitEntry: imposed dragged line, ppm " << ppm
        << "  threshold " << slitThresh*1e3 << " mm"
        << "  entry " << slitRate*1e3 << " mm/s"
        << "  gap " << slitGapMouth*1e3 << " mm at the crest to "
        << slitGapRoot*1e3 << " mm at " << slitSpan*1e3 << " mm depth"
        << nl
        << "    Higher ppm pins harder (smaller threshold, faster entry)."
        << " The line starts on the generated crest. Gas is not painted."
        << nl
        << "    Each step removes at most entryRate*dt of metal "
        << "(capped at 0.002 mm) and at most a quarter of a cell. "
        << "The width is the physical gap, not a cell count."
        << nl << endl;
}
