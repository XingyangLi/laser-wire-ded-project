@echo off
REM Wire-substrate gap study: queue state, benchmark decision, progress and ETA of every case (read-only)
title Laser Wire DED - gap study status
wsl -d Ubuntu-24.04 -u dukyong -- python3 /mnt/c/Users/dukyo/laser_wire_ded_project/scripts/pc/gap_study_status.py
echo.
echo Renders: C:\Users\dukyo\laser_wire_ded\viz\gap_study_1mm, _2mm, _3mm and viz\gap_study_compare
echo Look at one case live: Open_in_ParaView.bat gap_study_2mm
pause
