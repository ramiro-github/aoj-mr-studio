"""Tests for Quest package create/upload helpers."""

from pathlib import Path
from unittest.mock import patch

from aoj_mr_studio.adb_sync import AdbResult
from aoj_mr_studio.package_actions import push_model_to_package, validate_package_name


def test_validate_package_name_rejects_empty() -> None:
    assert validate_package_name("  ") == "Package name is required."


def test_validate_package_name_rejects_invalid_chars() -> None:
    assert validate_package_name("bad/name") is not None


def test_validate_package_name_accepts_leon() -> None:
    assert validate_package_name("Leon") is None


def test_push_model_to_package_reports_replaced(tmp_path: Path) -> None:
    glb = tmp_path / "leon.glb"
    glb.write_bytes(b"glb")

    with (
        patch("aoj_mr_studio.package_actions.remote_dir_exists", return_value=(AdbResult(True, ""), True)),
        patch("aoj_mr_studio.package_actions.remote_file_exists", return_value=(AdbResult(True, ""), True)),
        patch("aoj_mr_studio.package_actions.push_remote_file", return_value=AdbResult(True, "")),
    ):
        result = push_model_to_package("Leon", glb)

    assert result.ok is True
    assert result.replaced is True
    assert result.file_name == "leon.glb"
    assert "Replaced" in result.message


def test_push_model_to_package_reports_upload(tmp_path: Path) -> None:
    glb = tmp_path / "leon.glb"
    glb.write_bytes(b"glb")

    with (
        patch("aoj_mr_studio.package_actions.remote_dir_exists", return_value=(AdbResult(True, ""), True)),
        patch("aoj_mr_studio.package_actions.remote_file_exists", return_value=(AdbResult(True, ""), False)),
        patch("aoj_mr_studio.package_actions.push_remote_file", return_value=AdbResult(True, "")),
    ):
        result = push_model_to_package("Leon", glb)

    assert result.ok is True
    assert result.replaced is False
    assert "Uploaded" in result.message
