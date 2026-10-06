param(
    [Parameter(Position = 0)]
    [string]$CasePath = ""
)

$ErrorActionPreference = "Stop"

$ParaView = "C:\Program Files\ParaView 6.2.0\bin\paraview.exe"
if (-not (Test-Path $ParaView)) {
    Write-Error "ParaView not found at: $ParaView"
    exit 1
}

$WslDistro = "Ubuntu-24.04"
$DefaultCase = "/home/dukyong/laser_wire_ded_stranded/val3mm_fe_ni_v2"

function Convert-ToWslUnixPath {
    param([string]$PathIn)

    if ([string]::IsNullOrWhiteSpace($PathIn)) {
        return $DefaultCase
    }

    $p = $PathIn.Trim().Trim('"')

    # Already UNC to WSL
    if ($p -match '^\\\\wsl(?:\.localhost)?\\([^\\]+)\\(.+)$') {
        $rest = $Matches[2] -replace '\\', '/'
        return "/" + $rest
    }

    # WSL home shorthand
    if ($p.StartsWith("~/") -or $p -eq "~") {
        return ($p -replace '^~', '/home/dukyong')
    }

    # Already a Linux absolute path
    if ($p.StartsWith("/")) {
        return $p
    }

    # Windows drive path -> /mnt/<drive>/...
    if ($p -match '^([A-Za-z]):[\\/](.*)$') {
        $drive = $Matches[1].ToLower()
        $rest = ($Matches[2] -replace '\\', '/')
        return "/mnt/$drive/$rest"
    }

    # Relative path: treat as under WSL home laser_wire_ded_stranded
    if ($p -notmatch '[\\/]') {
        return "/home/dukyong/laser_wire_ded_stranded/$p"
    }

    return ($p -replace '\\', '/')
}

function Convert-ToWslUnc {
    param([string]$UnixPath)
    $trimmed = $UnixPath.TrimStart('/')
    $uncTail = $trimmed -replace '/', '\'
    return "\\wsl.localhost\$WslDistro\$uncTail"
}

$unixCase = Convert-ToWslUnixPath $CasePath

# If path points at case.foam / *.foam, use its directory
if ($unixCase -match '\.foam$') {
    $unixCase = ($unixCase -replace '/[^/]+\.foam$', '')
}

$unixFoam = "$unixCase/case.foam"
$uncFoam = Convert-ToWslUnc $unixFoam
$uncCase = Convert-ToWslUnc $unixCase

# Create empty case.foam in WSL if missing (OpenFOAM reader needs it)
$createCmd = "mkdir -p '$unixCase' && if [ ! -f '$unixFoam' ]; then : > '$unixFoam'; fi && test -f '$unixFoam' && test -d '$unixCase'"
$wslResult = & wsl -d $WslDistro -u dukyong -- bash -lc $createCmd
if ($LASTEXITCODE -ne 0) {
    Write-Error "Case path not reachable in WSL: $unixCase"
    exit 1
}

if (-not (Test-Path -LiteralPath $uncFoam)) {
    # Fallback UNC form
    $uncFoamAlt = $uncFoam -replace '\\wsl\.localhost\', '\\wsl$\'
    if (Test-Path -LiteralPath $uncFoamAlt) {
        $uncFoam = $uncFoamAlt
    } else {
        Write-Warning "UNC path not visible yet from Windows: $uncFoam"
        Write-Warning "ParaView may still open it if WSL is running."
    }
}

Write-Host "Opening in ParaView:"
Write-Host "  case : $unixCase"
Write-Host "  foam : $uncFoam"
Write-Host ""
Write-Host "After it opens:"
Write-Host "  1. Properties -> Case Type = Decomposed Case  (for live mpirun / processor* folders)"
Write-Host "     Use Reconstructed Case only after reconstructPar."
Write-Host "  2. Check Mesh Regions -> internalMesh, then Apply."
Write-Host "  3. Color by T, alpha.metal, or cFe."
Write-Host "  4. Use the time scrubber; File -> Reload Files to pick up new times while the solver runs."
Write-Host ""

Start-Process -FilePath $ParaView -ArgumentList @("--data=`"$uncFoam`"")
Write-Host "ParaView launched."
