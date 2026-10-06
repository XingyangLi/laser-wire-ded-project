# Launch the Laser Wire DED GUI
$ErrorActionPreference = "Stop"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$py = "C:\Users\dukyo\AppData\Local\Programs\Python\Python311\python.exe"
if (-not (Test-Path $py)) { $py = "py" }
Set-Location $here
& $py (Join-Path $here "app.py")
