@echo off
REM (Re)start the gap-study queue hidden + keep-awake. Safe to run twice: a running queue is detected and left alone.
REM Needed only after a reboot / WSL shutdown; unfinished cases continue from their latest saved time.
title Laser Wire DED - start gap study queue
set Q=/home/dukyong/laser_wire_ded_stranded/gap_study_queue
wsl -d Ubuntu-24.04 -u dukyong -- bash -c "test -f %Q%/queue.pid && kill -0 $(cat %Q%/queue.pid) 2>/dev/null && echo RUNNING"| findstr RUNNING >nul
if not errorlevel 1 (
  echo The gap-study queue is already running. Nothing to do.
  pause
  exit /b 0
)
powershell -NoProfile -Command "Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass','-File','C:\Users\dukyo\laser_wire_ded_project\scripts\pc\launch_wsl_job.ps1','-Script','%Q%/gap_study_queue.sh'"
echo Gap-study queue started in the background (hidden window, PC kept awake).
echo Check it with Gap_Study_Status.bat
pause
