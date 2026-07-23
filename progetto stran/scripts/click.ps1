param([int]$X, [int]$Y)
$ErrorActionPreference = 'Stop'
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class WClick {
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr h, uint m, IntPtr w, IntPtr l);
}
"@
$p = Get-Process world_clocks | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1
$h = $p.MainWindowHandle
$lp = [IntPtr](($Y -shl 16) -bor ($X -band 0xFFFF))
[WClick]::PostMessage($h, 0x201, [IntPtr]1, $lp) | Out-Null
Start-Sleep -Milliseconds 60
[WClick]::PostMessage($h, 0x202, [IntPtr]0, $lp) | Out-Null
Write-Host "clicked $X,$Y"
