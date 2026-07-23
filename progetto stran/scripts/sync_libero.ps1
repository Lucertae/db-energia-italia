# Sync libero pipeline: deploy to ciccio10, run ingest, pull CSV to local cache/
param(
    [string]$SshHost = "ciccio10@100.66.90.57",
    [switch]$LocalOnly
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if ((Split-Path -Leaf $root) -eq "scripts") { $root = Split-Path -Parent $root }
$libero = Join-Path $root "scripts\libero"
$cache = Join-Path $root "cache"
$remote = "~/lavoro/libero"
$ids = @("CBE","EMI","CVI","FEE","DIF","REV","HAS","BVL","MCP","GPR","CPU","EUA","GRN","DIR","NGF")

New-Item -ItemType Directory -Force -Path $cache | Out-Null

function Invoke-LocalLibero {
    $env:LIBERO_DB = Join-Path $libero "libero.db"
    $env:LIBERO_EXPORT = $cache
    python (Join-Path $libero "fetch_all.py") all
}

if ($LocalOnly) {
    Write-Host "libero local only"
    Invoke-LocalLibero
    exit 0
}

$remoteOk = $false
try {
    Write-Host "Deploy libero -> $SshHost"
    scp -r "$libero\requirements.txt" "$libero\libero_db.py" "$libero\fetch_all.py" `
        "$libero\setup_ciccio.sh" "${SshHost}:${remote}/"
    Write-Host "Run ingest on ciccio..."
    ssh $SshHost 'export PATH=$HOME/.local/bin:$PATH; /bin/bash $HOME/lavoro/libero/setup_ciccio.sh'
    Write-Host "Pull CSV -> cache\"
    foreach ($id in $ids) {
        $src = "${SshHost}:${remote}/export/${id}.csv"
        $dst = Join-Path $cache "${id}.csv"
        scp $src $dst 2>$null
        if (Test-Path $dst) { Write-Host "OK $id" }
    }
    $remoteOk = $true
} catch {
    Write-Host "WARN remote libero failed: $_"
}

if (-not $remoteOk) {
    Write-Host "Fallback: local libero fetch"
    Invoke-LocalLibero
}

Write-Host "libero sync done"
