#!/bin/bash
# 1.0 mm side-to-side wiggle, 10 mm of travel on the long plate (2.5 zigzags, 4 mm apart).
export WIGGLE_MM=1.0
exec bash "$(dirname "$0")/run_wiggle_10mm.sh"
