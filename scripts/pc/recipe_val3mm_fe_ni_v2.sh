#!/bin/bash
# Print generate_case.py argv for the 3 mm Fe+Ni defocus + anti-sinking recipe.
# Usage: recipe_val3mm_fe_ni_v2.sh <caseName>
# Then: python3 generate_case.py $(recipe...)  -- but prefer generate_from_recipe.sh
CASE="${1:?case name required}"
cat <<ARGS
--case $CASE
--laser-config transitional_r
--power 600
--scan-speed 0.002667
--wire-feed-speed 0.01818
--focus-height -0.0015
--rayleigh-length 0.0012
--beam-radius 0.0005
--spot-radius 0.0012
--beam-angle 25
--beam-direction -
--absorptivity-substrate 0.35
--absorptivity-wire 0.25
--alpha-hit 0.25
--strand-k-factor 0.4
--unmelted-k-factor 0.3
--liquidus-unmixed-threshold 0.85
--wire-type stranded
--strands 5
--strand-layout ring
--strand-diameter 0.0003
--strand-gap 8e-05
--strand-materials Fe,Ni,Fe,Ni,Fe
--strand-feed-basis metal
--substrate-material Invar36
--feed-angle 90
--feed-side front
--wire-gap 0
--feed-start 0
--track-length 0.003
--end-time 1.1249
--write-interval 0.02
--dx 0.00012
--resolution medium
--domain-y full
--wire-refine 1
--np 8
--feed-scale 1.0
--rigid-substrate 100
--stub-floor
ARGS
