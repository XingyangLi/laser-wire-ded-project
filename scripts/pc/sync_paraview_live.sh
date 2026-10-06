#!/bin/bash
# Mirror reconstructed time folders from a WSL case to a Windows-visible folder
# so ParaView can open without UNC/decomposed issues.
# Usage: sync_paraview_live.sh [caseName]
set -e
CASE_NAME="${1:-val3mm_fe_ni_v2}"
# Allow absolute path or name under stranded
if [[ "$CASE_NAME" == /* ]]; then
  SRC="$CASE_NAME"
  BASE=$(basename "$CASE_NAME")
else
  SRC="$HOME/laser_wire_ded_stranded/$CASE_NAME"
  BASE="$CASE_NAME"
fi
DST="/mnt/c/Users/dukyo/laser_wire_ded_project/viz/paraview_live"
# Also keep a named mirror for later browsing
NAMED="/mnt/c/Users/dukyo/laser_wire_ded_project/viz/${BASE}_paraview"

source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1 || true
cd "$SRC" || { echo "Case not found: $SRC"; exit 1; }

# Reconstruct any new times into the case root (safe while solver runs on processor*)
if [ -d processor0 ]; then
  reconstructPar -newTimes > "$SRC/log.reconstructPar" 2>&1 || true
fi

mkdir -p "$(dirname "$DST")"
rm -rf "$DST"
mkdir -p "$DST"
: > "$DST/case.foam"
rsync -a --delete "$SRC/constant" "$DST/"
rsync -a "$SRC/system" "$DST/" 2>/dev/null || true
for t in $(ls -d [0-9]* 2>/dev/null | grep -v orig || true); do
  rsync -a "$SRC/$t" "$DST/"
done

# Named copy (optional convenience)
rm -rf "$NAMED"
mkdir -p "$NAMED"
rsync -a "$DST/" "$NAMED/"

echo "Synced $SRC -> $DST"
ls "$DST" | head -40
du -sh "$DST"
