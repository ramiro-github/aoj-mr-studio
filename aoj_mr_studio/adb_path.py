"""Resolve adb executable — bundled vendor copy first, then PATH."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

_ADB_EXE = "adb.exe" if sys.platform == "win32" else "adb"


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def bundled_adb_directories() -> list[Path]:
    directories: list[Path] = []

    if getattr(sys, "frozen", False):
        app_dir = Path(sys.executable).resolve().parent
        meipass = getattr(sys, "_MEIPASS", None)
        if meipass:
            directories.append(Path(meipass) / "adb")
        directories.append(app_dir / "adb")
        directories.append(app_dir / "_internal" / "adb")

    directories.append(project_root() / "vendor" / "adb")
    return directories


def find_adb() -> str | None:
    for directory in bundled_adb_directories():
        candidate = directory / _ADB_EXE
        if candidate.is_file():
            return str(candidate)

    return shutil.which("adb")


def adb_source_label() -> str:
    path = find_adb()
    if not path:
        return "not found"

    resolved = Path(path).resolve()
    for directory in bundled_adb_directories():
        try:
            resolved.relative_to(directory.resolve())
            return "bundled"
        except ValueError:
            continue

    return "PATH"
