#!/bin/bash
# generate_case.py argv for the 10 mm Fe+Ni stranded-Invar validation track (track10mm_fe_ni):
# val3mm_fe_ni_v2 physics (defocus -1.5 mm / zR 1.2 mm, tip on plate, A_wire 0.25 / A_sub 0.35, contact
# conductance, liquidusUnmixed 0.85, rigidSubstrate 100 + stub floor) + conservative composition tracers
# (wire metal keeps its label in the bead) + wire-transfer diagnostics; NO stubbing stall, NO buckling.
# 10 mm of track = 3.75 s at 160 mm/min; refined (60 um) wire/bead box to x = 4.97 mm (recording planes
# 3.6-4.8 mm behind the ~3.5 mm pool tail).  Usage: recipe_track10mm_fe_ni.sh <caseDir>
CASE="${1:?case dir required}"
cat <<ARGS
--case $CASE
--laser-config transitional_r
--power 600
--scan-speed 0.002667
--wire-feed-speed 0.0101
--focus-height=-0.0015
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
--track-length 0.010
--end-time 3.75
--write-interval 0.05
--dx 0.00012
--resolution medium
--domain-y full
--wire-refine 1
--refine-downstream 0.0042
--refine-halfwidth-y 0.0013
--uniform-downstream 0.0056
--record-x 0.0036,0.0040,0.0044,0.0048
--np 8
--feed-scale 1.0
--rigid-substrate 100
--stub-floor
--conservative-tracers
--wire-transfer-stats
ARGS
