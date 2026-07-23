# Cattura screenshot di tutte le pagine OPS DESK (world_clocks.exe) — v2 UI
param(
    [string]$OutDir = "",
    [int]$LoadWaitSec = 40,
    [int]$PageWaitMs = 2500
)
$ErrorActionPreference = 'Stop'
$proj = Split-Path $PSScriptRoot -Parent
if (-not $OutDir) {
    $OutDir = Join-Path (Split-Path $proj -Parent) "interfacce"
}

$pages = @(
    @{ Key = 0x70; File = "01-ops.png";      Name = "F1 OPS - alert + spine + horizon flash" },
    @{ Key = 0x71; File = "02-mkt.png";      Name = "F2 MKT - horizon grid 4 col" },
    @{ Key = 0x72; File = "03-fx.png";       Name = "F3 FX - network + carry" },
    @{ Key = 0x73; File = "04-nrg.png";      Name = "F4 NRG - zone tile + heatmap + tidal" },
    @{ Key = 0x74; File = "05-gas.png";      Name = "F5 GAS - storage + hub spread" },
    @{ Key = 0x75; File = "06-met.png";      Name = "F6 MET - meteo operativo" },
    @{ Key = 0x76; File = "07-astro.png";    Name = "F7 ASTRO - sole+luna forcing" },
    @{ Key = 0x77; File = "08-lab.png";      Name = "F8 LAB - backtest verdetti" },
    @{ Key = 0x78; File = "09-sig.png";      Name = "F9 SIG - pipeline segnali" },
    @{ Key = 0x79; File = "10-risk.png";     Name = "F10 RISK - corr + risk merged" },
    @{ Key = 0x7A; File = "11-geo.png";     Name = "F11 GEO - paesi + produzione" },
    @{ Key = 0x7B; File = "12-ais.png";      Name = "F12 AIS - marittimo" },
    @{ Key = 0x44; File = "13-cat.png";      Name = "D CAT - catalogo + QA" }
)

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null
Write-Host "Output: $OutDir"

Get-Process world_clocks -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 1

Push-Location $proj
$proc = Start-Process -FilePath (Join-Path $proj "world_clocks.exe") -WorkingDirectory $proj -PassThru -WindowStyle Normal
Pop-Location

Write-Host "Attendo ${LoadWaitSec}s per caricamento dati / ingest..."
Start-Sleep -Seconds $LoadWaitSec

Add-Type -AssemblyName System.Drawing
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WinSnap {
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr h, IntPtr dc, uint f);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
    [StructLayout(LayoutKind.Sequential)] public struct RECT { public int L, T, R, B; }
}
"@

function Wait-Window {
    param([int]$ProcessId, [int]$TimeoutSec = 30)
    $deadline = (Get-Date).AddSeconds($TimeoutSec)
    while ((Get-Date) -lt $deadline) {
        $p = Get-Process -Id $ProcessId -ErrorAction SilentlyContinue
        if (-not $p) { throw "world_clocks terminato prematuramente" }
        if ($p.MainWindowHandle -ne 0) { return [IntPtr]$p.MainWindowHandle }
        Start-Sleep -Milliseconds 200
    }
    throw "Timeout: finestra world_clocks non visibile"
}

function Send-Key {
    param([IntPtr]$H, [int]$Vk)
    [WinSnap]::PostMessage($H, 0x100, [IntPtr]$Vk, [IntPtr]0) | Out-Null
    Start-Sleep -Milliseconds 60
    [WinSnap]::PostMessage($H, 0x101, [IntPtr]$Vk, [IntPtr]0) | Out-Null
}

function Save-Snap {
    param([IntPtr]$H, [string]$Path)
    $r = New-Object WinSnap+RECT
    [WinSnap]::GetWindowRect($H, [ref]$r) | Out-Null
    $w = $r.R - $r.L; $ht = $r.B - $r.T
    if ($w -le 0 -or $ht -le 0) { throw "Dimensioni finestra invalide per $Path" }
    $bmp = New-Object System.Drawing.Bitmap($w, $ht)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $dc = $g.GetHdc()
    [WinSnap]::PrintWindow($H, $dc, 2) | Out-Null
    $g.ReleaseHdc($dc)
    $g.Dispose()
    $bmp.Save($Path, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Host "  -> $Path (${w}x${ht})"
}

$h = Wait-Window -ProcessId $proc.Id
$manifest = @()
$manifest += "OPS DESK v2 - cattura interfacce"
$manifest += "Data: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
$manifest += "Attesa pre-cattura: ${LoadWaitSec}s"
$manifest += "Cartella: $OutDir"
$manifest += ""
$manifest += "Pagine (F1-F12 + D CAT):"

foreach ($pg in $pages) {
    Send-Key -H $h -Vk $pg.Key
    Start-Sleep -Milliseconds $PageWaitMs
    $out = Join-Path $OutDir $pg.File
    Save-Snap -H $h -Path $out
    $manifest += "  $($pg.File) - $($pg.Name)"
}

$manifest | Set-Content -Encoding UTF8 (Join-Path $OutDir "screens-manifest.txt")

Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
Write-Host "Fatto. $($pages.Count) screenshot in $OutDir"
