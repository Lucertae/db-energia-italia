# Deploy full progetto stran to ciccio10 and run harvest setup
param(
    [string]$SshHost = "ciccio10@100.66.90.57",
    [switch]$DeployOnly,
    [switch]$SetupOnly
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if ((Split-Path -Leaf $root) -eq "scripts") { $root = Split-Path -Parent $root }
$remote = '~/lavoro/progetto stran'
$remoteQuoted = "'${remote}'"

if (-not $SetupOnly) {
    Write-Host "Deploy -> ${SshHost}:${remote}"
    ssh $SshHost 'mkdir -p "$HOME/lavoro/progetto stran"'
    # rsync preferred if available
    $rsync = Get-Command rsync -ErrorAction SilentlyContinue
    if ($rsync) {
        & rsync -az --delete `
            --exclude ".git" `
            --exclude "world_clocks.exe" `
            --exclude "bin/*.exe" `
            -e "ssh" `
            "$root/" "${SshHost}:${remote}/"
    } else {
        scp -r "$root\*" "${SshHost}:${remote}/"
    }
    foreach ($key in @("entsoe", "eia", "gie", "terna", "ais")) {
        $src = Join-Path $root "cache\$key.key"
        if (Test-Path $src) {
            ssh $SshHost 'mkdir -p "$HOME/lavoro/progetto stran/cache"'
            scp $src "${SshHost}:${remote}/cache/$key.key"
            Write-Host "OK remote cache\$key.key"
        }
    }
    Write-Host "Deploy complete"
}

if (-not $DeployOnly) {
    Write-Host "Remote setup + harvest..."
    scp (Join-Path $root "scripts\setup_ciccio_progetto.sh") "${SshHost}:${remote}/setup_ciccio_progetto.sh"
    ssh $SshHost 'chmod +x "$HOME/lavoro/progetto stran/setup_ciccio_progetto.sh"; nohup /bin/bash "$HOME/lavoro/progetto stran/setup_ciccio_progetto.sh" > "$HOME/lavoro/progetto stran/nohup_setup.log" 2>&1 &'
    Write-Host "Harvest started in background on ciccio10 (log: ~/lavoro/progetto stran/nohup_setup.log)"
}

Write-Host "Clone path on ciccio10: ${remote}"
