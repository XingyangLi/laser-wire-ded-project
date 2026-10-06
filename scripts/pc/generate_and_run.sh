#!/bin/bash
# Generate a case from a named recipe, mesh, and solve with ~/lwded_bin.
# Does NOT touch protected / live cases.
# Usage: generate_and_run.sh <recipe> <caseName>
set -euo pipefail
RECIPE="${1:?recipe required, e.g. val3mm_fe_ni_v2}"
CASE="${2:?case name required}"
REPO=/mnt/c/Users/dukyo/laser_wire_ded_project
WSL_WD=$HOME/laser_wire_ded_stranded
OUT=/mnt/c/Users/dukyo/laser_wire_ded_project/viz/$CASE
C=$WSL_WD/$CASE
ST=$C/run.status

# Safety
case "$CASE" in
  val3mm_fe_ni_v2|full_transitional_r*|results_keep|laser_wire_ded_scan*)
    echo "REFUSING protected or live case name: $CASE" >&2
    exit 2
    ;;
esac
if [ -d "$HOME/laser_wire_ded_stranded/val3mm_fe_ni_v2/processor0" ] && [ "$CASE" = "val3mm_fe_ni_v2" ]; then
  echo "REFUSING to overwrite live run" >&2
  exit 2
fi

source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1
export PATH=$HOME/lwded_bin:$PATH
mkdir -p "$WSL_WD" "$OUT"
cd "$WSL_WD"
cp -a "$REPO"/*.py "$WSL_WD/" 2>/dev/null || true

RECIPE_SH="$REPO/scripts/pc/recipe_${RECIPE}.sh"
if [ ! -f "$RECIPE_SH" ]; then
  echo "Unknown recipe: $RECIPE (expected $RECIPE_SH)" >&2
  exit 1
fi

echo "$(date) GENERATE recipe=$RECIPE case=$CASE binary=$(which laserWireDEDFoam)" | tee -a "$OUT/launch.log"
# shellcheck disable=SC2046
python3 generate_case.py $(bash "$RECIPE_SH" "$CASE") > "$OUT/gen.log" 2>&1 \
  || { echo "$(date) GENERATE FAILED" | tee -a "$OUT/launch.log"; exit 1; }

# Drop helper scripts into the case
cp -f "$REPO/scripts/pc/check_below_plate.py" "$C/" 2>/dev/null || true
cp -f "$REPO/scripts/pc/run_val3mm_fe_ni_v2.sh" "$C/run_v2.sh" 2>/dev/null || true
# Rewrite run_v2.sh paths for this case name
cat > "$C/run_this.sh" <<RUN
#!/bin/bash
source /usr/lib/openfoam/openfoam2406/etc/bashrc >/dev/null 2>&1
export PATH=\$HOME/lwded_bin:\$PATH
REPO=$REPO
C=$C
OUT=$OUT
cd "\$C" || exit 1
ST=\$C/run.status
echo "\$(date) START binary=\$(which laserWireDEDFoam)" >> "\$ST"
if [ ! -d processor0 ]; then
  ./Allrun 8; rc=\$?
else
  echo "\$(date) restart from latest time" >> "\$ST"
  mpirun -np 8 laserWireDEDFoam -parallel >> log.laserWireDEDFoam 2>&1; rc=\$?
fi
echo "\$(date) SOLVER_EXIT rc=\$rc" >> "\$ST"
mkdir -p "\$OUT"
cp case_params.json postProcessing/meltPool/meltPool.dat postProcessing/meltPool/components.dat "\$OUT/" 2>/dev/null || true
if [ -x "\$HOME/vizenv/bin/python" ]; then PY=\$HOME/vizenv/bin/python; else PY=python3; fi
\$PY \$REPO/visualize_multicomp.py --case . --out "\$OUT" > log.viz 2>&1 || true
echo "\$(date) viz multicomp rc=\$?" >> "\$ST"
\$PY \$REPO/visualize.py --case . --out "\$OUT/standard" --only-latest >> log.viz 2>&1 || true
echo "\$(date) viz standard rc=\$?" >> "\$ST"
echo "\$(date) ALL DONE" >> "\$ST"
RUN
chmod +x "$C/run_this.sh"

# Also copy status helper
cp -f "$REPO/scripts/pc/status_any.sh" "$C/status_${CASE}.sh"
chmod +x "$C/status_${CASE}.sh"

echo "$(date) START solver via run_this.sh" | tee -a "$OUT/launch.log" "$ST"
bash "$C/run_this.sh"
echo "$(date) finished run_this.sh" | tee -a "$OUT/launch.log"
