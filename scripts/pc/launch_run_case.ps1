# Detached launch of generate_and_run.sh via launch_wsl_job.ps1 (keeps PC awake).
param(
    [Parameter(Mandatory = $true)][string]$Recipe,
    [Parameter(Mandatory = $true)][string]$CaseName
)

$ErrorActionPreference = "Stop"
$Repo = "C:\Users\dukyo\laser_wire_ded_project"
$Launcher = Join-Path $Repo "scripts\pc\launch_wsl_job.ps1"
$Script = "/mnt/c/Users/dukyo/laser_wire_ded_project/scripts/pc/generate_and_run.sh"
$LogDir = Join-Path $Repo "viz\$CaseName"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$WinLog = Join-Path $LogDir "wsl_job.out"

# Build a tiny wrapper so bash receives two args cleanly
$Wrap = "/tmp/lwded_run_${CaseName}.sh"
$WrapBody = @"
#!/bin/bash
bash '$Script' '$Recipe' '$CaseName'
"@
$WrapBodyUnix = $WrapBody -replace "`r", ""
$bytes = [System.Text.Encoding]::UTF8.GetBytes($WrapBodyUnix)
$b64 = [Convert]::ToBase64String($bytes)
& wsl.exe -d Ubuntu-24.04 -u dukyong -- bash -lc "echo $b64 | base64 -d > $Wrap && chmod +x $Wrap"

Start-Process -WindowStyle Hidden -FilePath powershell.exe -ArgumentList @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass',
    '-File', $Launcher,
    '-Script', $Wrap,
    '-Log', $WinLog
)

Write-Host "Launched recipe=$Recipe case=$CaseName"
Write-Host "Log: $WinLog"
Write-Host "Status: double-click Status.bat $CaseName"
