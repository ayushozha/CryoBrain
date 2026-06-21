# Measured C5 climb via WSL (PowerShell-safe entrypoint).
param(
    [int]$Steps = 5
)

$Repo = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
if ($Repo -match '^([A-Za-z]):\\(.*)$') {
    $WslRepo = "/mnt/$($Matches[1].ToLower())/$($Matches[2] -replace '\\', '/')"
} else {
    throw "Unsupported repo path for WSL: $Repo"
}

wsl --cd $WslRepo bash scripts/run_c5_climb_wsl.sh $Steps
exit $LASTEXITCODE