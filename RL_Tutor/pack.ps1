<#
    Build a clean RL_Tutor.zip to send to somebody.

    Run it from anywhere:      powershell -ExecutionPolicy Bypass -File pack.ps1
    Or right-click > Run with PowerShell.

    Excludes .venv (~770 MB of installed packages), __pycache__ and screenshot
    folders. The result is ~120 KB.
#>

$ErrorActionPreference = "Stop"

$src   = $PSScriptRoot
$name  = Split-Path $src -Leaf
$out   = Join-Path (Split-Path $src -Parent) "$name.zip"
$stage = Join-Path $env:TEMP "pack_$name\$name"

Write-Host "packing $src" -ForegroundColor Cyan

if (Test-Path (Split-Path $stage -Parent)) {
    Remove-Item (Split-Path $stage -Parent) -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $stage | Out-Null

$skip = '\\\.venv\\|\\__pycache__\\|\\_shots|\\\.git\\'
$files = Get-ChildItem $src -Recurse -File |
         Where-Object { $_.FullName -notmatch $skip -and $_.Name -ne "$name.zip" }

foreach ($f in $files) {
    $rel = $f.FullName.Substring($src.Length + 1)
    $dst = Join-Path $stage $rel
    New-Item -ItemType Directory -Force -Path (Split-Path $dst) | Out-Null
    Copy-Item $f.FullName $dst
}

if (Test-Path $out) { Remove-Item $out -Force }
Compress-Archive -Path $stage -DestinationPath $out -CompressionLevel Optimal

$kb = (Get-Item $out).Length / 1KB
Write-Host ("done: {0}  ({1:N0} KB, {2} files)" -f $out, $kb, $files.Count) `
           -ForegroundColor Green
Write-Host "send that single .zip -- the recipient needs Python 3.10+ and nothing else."
