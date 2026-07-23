# Prefetch FRED CSV into cache\ for OPS DESK (offline + fast startup)
$ErrorActionPreference = "Continue"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
if ((Split-Path -Leaf $root) -eq "scripts") { $root = Split-Path -Parent $root }
$cache = Join-Path $root "cache"
$days = 1900
$cosd = (Get-Date).AddDays(-$days).ToString("yyyy-MM-dd")

New-Item -ItemType Directory -Force -Path $cache | Out-Null

$series = @{
    BRT="DCOILBRENTEU"; WTI="DCOILWTICO"; HUB="DHHNGSP"; TTF="PNGASEUUSDM"
python (Join-Path $root "scripts\desk_harvest\eia_public_inventories.py")
    COA="PCOALAUUSDM"; JKM="PNGASJPUSDM"
    EUF="DEXUSEU"; GBF="DEXUSUK"; JPF="DEXJPUS"; CNF="DEXCHUS"; INF="DEXINUS"
    BRF="DEXBZUS"; MXF="DEXMXUS"; KEF="DEXKOUS"; NZF="DEXUSNZ"; ZAF="DEXSFUS"
    CAD="DEXCAUS"; U10="DGS10"; E10="IRLTLT01EZM156N"; Z10="IRLTLT01ZAM156N"
    SOF="SOFR"; EDF="ECBDFR"; CPR="PCOPPUSDM"; BE5="T5YIE"; VIX="VIXCLS"
    DXY="DTWEXBGS"; NOK="DEXNOUS"; SEK="DEXSDUS"; U2="DGS2"; U5="DGS5"
    BE1="T10YIE"; SPX="SP500"
    HYO="BAMLH0A0HYM2"; IGO="BAMLC0A0CM"
    NAS="NASDAQCOM"; FED="DFF"; U30="DGS30"
    HOL="DHOILNYH"; RBO="GASREGW"
}

$ok = 0; $fail = 0
foreach ($id in $series.Keys) {
    $fred = $series[$id]
    $url = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=$fred&cosd=$cosd"
    $out = Join-Path $cache "$id.csv"
    try {
        curl.exe -fsSL --max-time 90 -o $out $url
        if ($LASTEXITCODE -ne 0) { throw "curl exit $LASTEXITCODE" }
        if ((Get-Item $out).Length -gt 64) { $ok++; Write-Host "OK $id" }
        else { $fail++; Write-Host "FAIL $id (empty)" }
    } catch {
        $fail++; Write-Host "FAIL $id $_"
    }
    Start-Sleep -Milliseconds 200
}

& (Join-Path $root "scripts\sync_keys.ps1")

# Dati locali (math/data)
python (Join-Path $root "scripts\import_eu_power.py")
python (Join-Path $root "scripts\fetch_eia_weekly.py")
python (Join-Path $root "scripts\fetch_hashrate.py")
python (Join-Path $root "scripts\fetch_gold_binance.py")
python (Join-Path $root "scripts\desk_harvest\harvest_portwatch.py")
python (Join-Path $root "scripts\desk_harvest\harvest_intel.py")
python (Join-Path $root "scripts\spine_build.py")

if ($env:AISSTREAM_API_KEY) {
    Set-Content -Path (Join-Path $cache "ais.key") -Value $env:AISSTREAM_API_KEY -NoNewline
    Write-Host "AIS key -> cache\ais.key (from env)"
}
try {
    & (Join-Path $root "scripts\sync_desk.ps1")
} catch {
    Write-Host "WARN desk remote skipped: $_"
    $env:DESK_ROOT = $root
    $env:DESK_CACHE = $cache
    python (Join-Path $root "scripts\desk_harvest\harvest_all.py")
}

Write-Host "prefetch done FRED ok=$ok fail=$fail"
