#!/bin/bash
# 0.5 mm side-to-side wiggle, 10 mm of travel on the long plate (5 zigzags, 2 mm apart).
export WIGGLE_MM=0.5
exec bash "$(dirname "$0")/run_wiggle_10mm.sh"
