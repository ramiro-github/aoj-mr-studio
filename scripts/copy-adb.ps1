# Copy Android platform-tools into vendor/adb/ for bundled Quest sync.
param(
    [string]$PlatformToolsDir = ""
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Dest = Join-Path $Root "vendor\adb"

function Find-PlatformTools {
    param([string]$Hint)

    if ($Hint -and (Test-Path $Hint)) {
        return (Resolve-Path $Hint).Path
    }

    $candidates = @(
        "$env:LOCALAPPDATA\Android\Sdk\platform-tools",
        "$env:USERPROFILE\AppData\Local\Android\Sdk\platform-tools",
        "$env:ANDROID_HOME\platform-tools",
        "$env:ANDROID_SDK_ROOT\platform-tools"
    )

    foreach ($path in $candidates) {
        if ($path -and (Test-Path (Join-Path $path "adb.exe"))) {
            return $path
        }
    }

    $pathAdb = Get-Command adb -ErrorAction SilentlyContinue
    if ($pathAdb) {
        return (Split-Path -Parent $pathAdb.Source)
    }

    return $null
}

$Source = Find-PlatformTools -Hint $PlatformToolsDir
if (-not $Source) {
    Write-Error "platform-tools not found. Install Android platform-tools, add adb to PATH, or pass -PlatformToolsDir."
}

New-Item -ItemType Directory -Force -Path $Dest | Out-Null

$files = @("adb.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll")
foreach ($name in $files) {
    $src = Join-Path $Source $name
    if (-not (Test-Path $src)) {
        Write-Warning "Skipping missing file: $src"
        continue
    }
    Copy-Item -Path $src -Destination (Join-Path $Dest $name) -Force
    Write-Host "Copied $name"
}

if (-not (Test-Path (Join-Path $Dest "adb.exe"))) {
    Write-Error "adb.exe was not copied; check platform-tools path: $Source"
}

Write-Host "Done. Bundled adb at: $Dest"
