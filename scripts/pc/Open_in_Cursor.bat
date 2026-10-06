@echo off
REM Open the project folder in Cursor
set REPO=C:\Users\dukyo\laser_wire_ded_project
set CURSOR=%LOCALAPPDATA%\Programs\cursor\resources\app\bin\cursor.cmd
if exist "%CURSOR%" (
  start "" "%CURSOR%" "%REPO%"
) else (
  echo Cursor CLI not found. In Cursor: File - Open Folder - %REPO%
  pause
)
