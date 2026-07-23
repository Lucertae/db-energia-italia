# Scarica owid-energy-data.csv e codebook da GitHub (repo ufficiale OWID).
$ErrorActionPreference = "Stop"
$Root = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$OwidDir = Join-Path $Root "progetto stran\cache\owid"
New-Item -ItemType Directory -Force -Path $OwidDir | Out-Null
$Base = "https://raw.githubusercontent.com/owid/energy-data/master"
$files = @("owid-energy-data.csv", "owid-energy-codebook.csv", "README.md")
foreach ($f in $files) {
    $out = Join-Path $OwidDir $f
    Invoke-WebRequest -Uri "$Base/$f" -OutFile $out -UseBasicParsing
    Write-Host "OK $f -> $out ($((Get-Item $out).Length) bytes)"
}
Write-Host "Repo: https://github.com/owid/energy-data"
