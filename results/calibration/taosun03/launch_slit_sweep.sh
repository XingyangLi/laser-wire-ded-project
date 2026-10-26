#!/bin/bash
# Centre-plane gas slit on the trailing wire face.
# Neck mesh ~19 um (3 halvings of the 150 um cell). Wire and trailing-wire
# contact angles follow oxygen ppm; the plate window stays the fused-bead
# recipe. One rank, nice 10. Oxygen 50/100/300 ppm, feed 18/24/28 mm/s,
# on the cal113, cal117 and cal140 heats. Tags cal167-cal193.
DIR="$(cd "$(dirname "$0")" && pwd)"
# shellcheck disable=SC1091
source "$DIR/lib.sh"
tao_build

run_one() {
    local tag="$1"
    local ppm="$2"
    local feed="$3"
    local plate_r="$4"
    local plate_a="$5"
    local abs="$6"
    local preheat="$7"
    local half_ang="$8"
    local blend="$9"
    local dip="${10}"
    local np=1
    local log="$DIR/${tag}_driver.out"
    (
        exec > >(tee -a "$log") 2>&1
        set -euo pipefail
        echo "LAUNCH $tag ppm=$ppm feed=$feed $(date --iso-8601=seconds)"
        tao_acquire "$np"
        trap 'tao_release '"$np" EXIT
        tao_build
        local case="$TAO_ROOT/cases/wire_cavity_${tag}"
        local extra=()
        if [[ -n "$dip" ]]; then
            extra+=(--rear-power-dip "$dip")
        fi
        tao_cal08_case "$case" \
            --scan-speed 0.003 --wire-feed-speed "$feed" \
            --beam-powers 100,100,700 \
            --absorptivity-substrate "$abs" \
            --preheat "$preheat" \
            --wire-preheat 1100 \
            --end-time 0.40 --write-interval 0.10 --np "$np" \
            --neck-refine 3 \
            --theta-receding "$plate_r" --theta-advancing "$plate_a" \
            --theta-receding-wire 25 --theta-advancing-wire 70 \
            --wire-sector \
            --theta-receding-wire-trail 30 --theta-advancing-wire-trail 100 \
            --wire-sector-half-angle "$half_ang" --wire-sector-blend "$blend" \
            --oxygen-ppm "$ppm" --oxygen-wire-angles \
            "${extra[@]}"
        tao_run "$np" "$case"
        tao_post "$tag" "$case"
        echo "${tag}_DONE"
    ) &
}

# base, ppm, feed_m_s. Tag numbers follow this order from cal167.
# cal113 heat: plate 20/55, absorptivity 0.55, preheat 900 K, sector 60/20.
# cal117 heat: plate 10/40, absorptivity 0.65, preheat 300 K, sector 90/30.
# cal140 heat: cal117 plus the rear beam at 0.40 from 0.55 to 0.63 s.
i=0
for spec in \
    "113 50 0.018" "113 50 0.024" "113 50 0.028" \
    "113 100 0.018" "113 100 0.024" "113 100 0.028" \
    "113 300 0.018" "113 300 0.024" "113 300 0.028" \
    "117 50 0.018" "117 50 0.024" "117 50 0.028" \
    "117 100 0.018" "117 100 0.024" "117 100 0.028" \
    "117 300 0.018" "117 300 0.024" "117 300 0.028" \
    "140 50 0.018" "140 50 0.024" "140 50 0.028" \
    "140 100 0.018" "140 100 0.024" "140 100 0.028" \
    "140 300 0.018" "140 300 0.024" "140 300 0.028"
do
    set -- $spec
    base=$1
    ppm=$2
    feed=$3
    tag="cal$((167 + i))"
    i=$((i + 1))
    if [[ "$base" == "113" ]]; then
        run_one "$tag" "$ppm" "$feed" 20 55 0.55 900 60 20 ""
    elif [[ "$base" == "117" ]]; then
        run_one "$tag" "$ppm" "$feed" 10 40 0.65 300 90 30 ""
    else
        run_one "$tag" "$ppm" "$feed" 10 40 0.65 300 90 30 "0.55,0.63,0.40"
    fi
    sleep 20
done
wait
echo "SLIT_SWEEP_DONE"
