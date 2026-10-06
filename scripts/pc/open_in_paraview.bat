@echo off
REM Double-click to open the live DED case (or pass a case path as arg 1).
setlocal
set "SCRIPT=%~dp0open_in_paraview.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT%" %*
