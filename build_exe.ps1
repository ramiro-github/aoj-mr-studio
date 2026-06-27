# Build AOJ MR Studio.exe with bundled adb (SideQuest-style).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host "=== Copy platform-tools into vendor/adb ==="
& "$Root\scripts\copy-adb.ps1"

Write-Host "=== Install build deps ==="
if (Test-Path ".venv\Scripts\pip.exe") {
    .\.venv\Scripts\pip install -e ".[dev,build]" -q
    $Python = ".\.venv\Scripts\python.exe"
    $PyInstaller = ".\.venv\Scripts\pyinstaller.exe"
} else {
    pip install -e ".[dev,build]" -q
    $Python = "python"
    $PyInstaller = "pyinstaller"
}

Write-Host "=== PyInstaller (onedir) ==="
& $PyInstaller --noconfirm "aoj-mr-studio.spec"

$OutDir = Join-Path $Root "dist\AOJ MR Studio"
if (Test-Path (Join-Path $OutDir "AOJ MR Studio.exe")) {
    Write-Host ""
    Write-Host "Build OK:"
    Write-Host "  $OutDir\AOJ MR Studio.exe"
    if (Test-Path (Join-Path $OutDir "adb\adb.exe")) {
        Write-Host "  Bundled adb: $OutDir\adb\adb.exe"
    }
} else {
    Write-Error "Build failed - exe not found in dist\AOJ MR Studio"
}
