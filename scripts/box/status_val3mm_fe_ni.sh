#!/bin/bash
# Legacy name: default to the active defocus run. Pass a path to override
# (e.g. status_val3mm_fe_ni.sh /workspace/laser_wire_ded/val3mm_fe_ni_focus03_balled).
C=${1:-/workspace/laser_wire_ded/val3mm_fe_ni_defocus}
exec /workspace/laser_wire_ded/status_val3mm_fe_ni_defocus.sh "$C"
