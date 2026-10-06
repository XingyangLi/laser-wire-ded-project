@echo off
REM Launch the Laser Wire DED GUI with Windows Python (tkinter).
setlocal
set PY=C:\Users\dukyo\AppData\Local\Programs\Python\Python311\python.exe
if not exist "%PY%" set PY=py
cd /d "%~dp0"
"%PY%" "%~dp0app.py"
if errorlevel 1 pause
endlocal
