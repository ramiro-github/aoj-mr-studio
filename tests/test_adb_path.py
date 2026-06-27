"""Tests for bundled adb resolution."""

from pathlib import Path

from aoj_mr_studio.adb_path import bundled_adb_directories, project_root


def test_project_root_exists() -> None:
    root = project_root()
    assert root.is_dir()
    assert (root / "pyproject.toml").is_file()


def test_bundled_adb_dir_includes_vendor() -> None:
    directories = bundled_adb_directories()
    vendor = project_root() / "vendor" / "adb"
    assert vendor in directories
