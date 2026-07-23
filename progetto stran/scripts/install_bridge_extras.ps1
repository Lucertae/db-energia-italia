param(
    [ValidateSet("energy", "fx", "weather", "all")]
    [string]$Sector = "energy"
)

$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "OPS DESK bridge extras: $Sector"

if ($Sector -eq "energy" -or $Sector -eq "all") {
    pip install -r requirements-bridge-energy.txt
}
if ($Sector -eq "fx" -or $Sector -eq "all") {
    pip install -r requirements-bridge-fx.txt
}
if ($Sector -eq "weather" -or $Sector -eq "all") {
    pip install -r requirements-bridge-weather.txt
}

python scripts\spine_build.py
Write-Host "Done. Check cache\spine\modules_index.json"
