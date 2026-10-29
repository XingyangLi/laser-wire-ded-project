# Restart checkpoint cal95b

Reconstructed fields at t = 0.8 s. The mesh is the undecomposed
`constant/polyMesh`. Copy this directory to a new case, rename `0.8` to
`0` if the pin window should start at t = 0, or keep the time name and set
`startFrom latestTime`.

Source case: `/home/xingyang/laser-wire-ded-project/cases/wire_cavity_cal95b`.

Recipe that produced it: `results/calibration/launch_track120.sh` with
`TRACK_TAG=cal95b`. Equal beam powers 246.6667/246.6667/246.6666 W
(740 W total), azimuths 60/−60/180, inclination 15°, plate spots at
0.55 mm from the wire, substrate 1100 K, plate window 10°/40°,
wire inlet 300 K, feed 24 mm/s, scan 4 mm/s.
