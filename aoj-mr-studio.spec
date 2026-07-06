# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — onedir build with bundled vendor/adb/."""

from pathlib import Path

block_cipher = None
project_root = Path(SPECPATH)
adb_dir = project_root / "vendor" / "adb"

datas = []
manual_data = project_root / "aoj_mr_studio" / "data"
if manual_data.is_dir():
    datas.append((str(manual_data), "aoj_mr_studio/data"))

# adb must be listed in binaries, not datas — PyInstaller 6 reclassifies .exe
# from datas and drops them from the expected adb/ folder in onedir builds.
binaries = []
_adb_bundle_files = ("adb.exe", "AdbWinApi.dll", "AdbWinUsbApi.dll")
if (adb_dir / "adb.exe").is_file():
    for name in _adb_bundle_files:
        path = adb_dir / name
        if path.is_file():
            binaries.append((str(path), "adb"))
else:
    print("WARNING: vendor/adb/adb.exe missing — run scripts/copy-adb.ps1 before release builds")

a = Analysis(
    ["aoj_mr_studio/__main__.py"],
    pathex=[str(project_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="AOJ MR Studio",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="AOJ MR Studio",
)
