# Copia API key note sul PC -> terminal\cache\ (non committare)
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if ((Split-Path -Leaf $root) -eq "scripts") { $root = Split-Path -Parent $root }
$cache = Join-Path $root "cache"
New-Item -ItemType Directory -Force -Path $cache | Out-Null

function Set-KeyFromEnvFile($envPath, $varName, $outName) {
    if (-not (Test-Path $envPath)) { return $false }
    $val = $null
    foreach ($line in Get-Content $envPath) {
        if ($line -match "^\s*$varName\s*=\s*(.+)\s*$") {
            $val = $Matches[1].Trim().Trim('"').Trim("'")
            break
        }
    }
    if (-not $val) { return $false }
    Set-Content -Path (Join-Path $cache $outName) -Value $val -NoNewline
    Write-Host "OK $outName <- $varName ($envPath)"
    return $true
}

$hedge = "C:\Users\jecho\Desktop\lac\hedge\.env"
Set-KeyFromEnvFile $hedge "HEDGE_ENTSOE_TOKEN" "entsoe.key" | Out-Null
Set-KeyFromEnvFile $hedge "HEDGE_EUENERGY_TOKEN" "entsoe.key" | Out-Null
Set-KeyFromEnvFile $hedge "HEDGE_GIE_API_KEY" "gie.key" | Out-Null
Set-KeyFromEnvFile $hedge "TERNA_API_KEY" "terna.key" | Out-Null
Set-KeyFromEnvFile $hedge "EIA_API_KEY" "eia.key" | Out-Null
Set-KeyFromEnvFile $hedge "HEDGE_EIA_API_KEY" "eia.key" | Out-Null

$tok = "C:\Users\jecho\Desktop\math\data\euenergy_token.txt"
if (Test-Path $tok) {
    Copy-Item $tok (Join-Path $cache "entsoe.key") -Force
    Write-Host "OK entsoe.key <- math\data\euenergy_token.txt"
}

if ($env:EIA_API_KEY) {
    Set-Content -Path (Join-Path $cache "eia.key") -Value $env:EIA_API_KEY -NoNewline
    Write-Host "OK eia.key <- env EIA_API_KEY"
}

if ($env:ENTSOE_API_TOKEN) {
    Set-Content -Path (Join-Path $cache "entsoe.key") -Value $env:ENTSOE_API_TOKEN -NoNewline
    Write-Host "OK entsoe.key <- env ENTSOE_API_TOKEN"
}

if ($env:AISSTREAM_API_KEY) {
    Set-Content -Path (Join-Path $cache "ais.key") -Value $env:AISSTREAM_API_KEY -NoNewline
    Write-Host "OK ais.key <- env AISSTREAM_API_KEY"
}

Write-Host ""
Write-Host "=== keys status ==="
@(
    @{ name = "entsoe"; file = "entsoe.key"; url = "https://transparency.entsoe.eu" },
    @{ name = "eia";    file = "eia.key";    url = "https://www.eia.gov/opendata/register.php" },
    @{ name = "gie";    file = "gie.key";    url = "https://agsi.gie.eu" },
    @{ name = "terna";  file = "terna.key";  url = "https://api.terna.it" },
    @{ name = "ais";    file = "ais.key";    url = "https://aisstream.io" }
) | ForEach-Object {
    $p = Join-Path $cache $_.file
    if (Test-Path $p) { Write-Host "  + $($_.name)  ($p)" }
    else { Write-Host "  - $($_.name)  MISSING -> register $($_.url)" }
}

Write-Host "sync_keys done -> $cache"
