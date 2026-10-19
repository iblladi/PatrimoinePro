# Capture the screen or a window into a PNG (used to check rendering).
param(
    [int]$ProcessId = 0,
    [string]$Out = "capture.png",
    [switch]$FullScreen
)

Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Windows.Forms

if (-not ("Win32Capture" -as [type])) {
Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Win32Capture {
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hWnd, out RECT rect);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
    [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int cmd);
}
"@
}

$rect = New-Object Win32Capture+RECT
if ($FullScreen -or $ProcessId -eq 0) {
    $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
    $rect.Left = $bounds.Left; $rect.Top = $bounds.Top
    $rect.Right = $bounds.Right; $rect.Bottom = $bounds.Bottom
} else {
    $proc = Get-Process -Id $ProcessId -ErrorAction Stop
    $handle = $proc.MainWindowHandle
    if ($handle -eq [IntPtr]::Zero) { throw "No main window for PID $ProcessId" }
    [void][Win32Capture]::ShowWindow($handle, 9)
    [void][Win32Capture]::SetForegroundWindow($handle)
    Start-Sleep -Milliseconds 900
    [void][Win32Capture]::GetWindowRect($handle, [ref]$rect)
}

$width = $rect.Right - $rect.Left
$height = $rect.Bottom - $rect.Top
if ($width -le 0 -or $height -le 0) { throw "Invalid size: $width x $height" }

$bmp = New-Object System.Drawing.Bitmap $width, $height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($rect.Left, $rect.Top, 0, 0, $bmp.Size)
$g.Dispose()

$dir = Split-Path -Parent $Out
if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
$bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
$bmp.Dispose()
Write-Output "CAPTURE $Out ($width x $height) at $($rect.Left),$($rect.Top)"
