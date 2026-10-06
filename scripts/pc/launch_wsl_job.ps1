# Detached runner for long WSL jobs: keeps the PC awake (SetThreadExecutionState)
# and keeps wsl.exe alive until the bash script finishes.
# Usage (returns immediately):
#   Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile','-ExecutionPolicy','Bypass',
#       '-File','C:\Users\dukyo\laser_wire_ded\launch_wsl_job.ps1','-Script','/mnt/c/Users/dukyo/laser_wire_ded/run_production.sh'
param([Parameter(Mandatory=$true)][string]$Script, [string]$Log = "")
$sig = '[DllImport("kernel32.dll")] public static extern uint SetThreadExecutionState(uint esFlags);'
Add-Type -Namespace Win32 -Name Power -MemberDefinition $sig
# ES_CONTINUOUS (0x80000000) | ES_SYSTEM_REQUIRED (0x00000001)
[Win32.Power]::SetThreadExecutionState([uint32]2147483649) | Out-Null
try {
    if ($Log -ne "") {
        & wsl.exe -d Ubuntu-24.04 -- bash -l $Script *> $Log
    } else {
        & wsl.exe -d Ubuntu-24.04 -- bash -l $Script
    }
} finally {
    [Win32.Power]::SetThreadExecutionState([uint32]2147483648) | Out-Null
}
