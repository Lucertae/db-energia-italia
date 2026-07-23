# Deploy desk harvest to ciccio10, run full ingest, pull cache to local OPS DESK
param(
    [string]$SshHost = "ciccio10@100.66.90.57",
    [switch]$LocalOnly,
    [switch]$PullOnly
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if ((Split-Path -Leaf $root) -eq "scripts") { $root = Split-Path -Parent $root }
$desk = Join-Path $root "scripts\desk_harvest"
$libero = Join-Path $root "scripts\libero"
$cache = Join-Path $root "cache"
$remoteDesk = "~/lavoro/desk"
$remoteLibero = "~/lavoro/libero"

New-Item -ItemType Directory -Force -Path $cache | Out-Null
& (Join-Path $root "scripts\sync_keys.ps1")
@("fred", "ecb", "crypto", "stooq", "eia", "entsoe", "owid", "electricity_market") | ForEach-Object {
    New-Item -ItemType Directory -Force -Path (Join-Path $cache $_) | Out-Null
}

function Invoke-LocalHarvest {
    $env:DESK_ROOT = $root
    $env:DESK_CACHE = $cache
    python (Join-Path $desk "harvest_all.py")
}

if ($LocalOnly) {
    Write-Host "desk harvest local only"
    Invoke-LocalHarvest
    exit 0
}

# Copy API keys to remote (never commit these)
ssh $SshHost "mkdir -p ~/lavoro/desk/cache"
foreach ($key in @("entsoe", "eia", "gie", "terna")) {
    $src = Join-Path $cache "$key.key"
    if (Test-Path $src) {
        scp $src "${SshHost}:${remoteDesk}/cache/$key.key"
        Write-Host "OK remote cache\$key.key"
    }
}

if (-not $PullOnly) {
    Write-Host "Deploy desk_harvest + libero -> $SshHost"
    ssh $SshHost "mkdir -p ~/lavoro/desk ~/lavoro/libero"
    scp "$desk\*.py" "$desk\setup_ciccio.sh" "${SshHost}:${remoteDesk}/"
    scp "$libero\requirements.txt" "$libero\libero_db.py" "$libero\fetch_all.py" `
        "$libero\setup_ciccio.sh" "${SshHost}:${remoteLibero}/"

    Write-Host "Run harvest on ciccio10 (background)..."
    ssh $SshHost "chmod +x ~/lavoro/desk/setup_ciccio.sh; nohup /bin/bash ~/lavoro/desk/setup_ciccio.sh > ~/lavoro/desk/nohup.log 2>&1 &"
    Start-Sleep -Seconds 3
}

Write-Host "Pull cache from ciccio10..."
$pullOk = $false
try {
    scp -r "${SshHost}:${remoteDesk}/cache/*" $cache 2>$null
    $pullOk = $true
} catch {
    Write-Host "WARN initial pull: $_"
}

# Libero series at cache root
$liberoIds = @("CBE","EMI","CVI","FEE","DIF","REV","HAS","BVL","MCP","GPR","CPU","EUA","GRN","DIR","NGF")
foreach ($id in $liberoIds) {
    $src = "${SshHost}:${remoteDesk}/cache/${id}.csv"
    $dst = Join-Path $cache "${id}.csv"
    scp $src $dst 2>$null
}

Write-Host "Pull OWID + electricity market datasets..."
$owidDir = Join-Path $cache "owid"
$mktDir = Join-Path $cache "electricity_market"
ssh $SshHost "test -f ~/lavoro/desk/fetch_datasets_ciccio.sh && /bin/bash ~/lavoro/desk/fetch_datasets_ciccio.sh || true"
scp "${SshHost}:~/lavoro/owid-energy-data/owid-energy-data.csv" (Join-Path $owidDir "owid-energy-data.csv") 2>$null
scp "${SshHost}:~/lavoro/owid-energy-data/owid-energy-codebook.csv" (Join-Path $owidDir "owid-energy-codebook.csv") 2>$null
scp "${SshHost}:~/lavoro/datasets/electricity_market/electricity_market_dataset.csv" (Join-Path $mktDir "electricity_market_dataset.csv") 2>$null
if (Test-Path (Join-Path $owidDir "owid-energy-data.csv")) { Write-Host "OK owid-energy-data.csv" }
if (Test-Path (Join-Path $mktDir "electricity_market_dataset.csv")) { Write-Host "OK electricity_market_dataset.csv" }

if (-not $pullOk) {
    Write-Host "Fallback: local harvest"
    Invoke-LocalHarvest
}

Write-Host "desk sync done -> $cache"
