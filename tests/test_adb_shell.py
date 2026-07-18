"""Tests for adb shell path quoting."""

from unittest.mock import patch

from aoj_mr_studio.adb_sync import AdbResult, delete_remote_dir, quote_shell_path


def test_quote_shell_path_spaces() -> None:
    path = "/sdcard/Android/data/com.curif.AgeOfJoy/MR/Custom Objects"
    quoted = quote_shell_path(path)
    assert quoted.startswith("'") and quoted.endswith("'")
    assert "Custom Objects" in quoted


def test_quote_shell_path_simple() -> None:
    assert quote_shell_path("/sdcard/MR") == "/sdcard/MR"


def test_delete_remote_dir_quotes_path() -> None:
    with (
        patch(
            "aoj_mr_studio.adb_sync.check_device_connected",
            return_value=AdbResult(True, "connected"),
        ),
        patch(
            "aoj_mr_studio.adb_sync.run_adb_shell",
            return_value=AdbResult(True, "ok"),
        ) as shell,
    ):
        result = delete_remote_dir("/sdcard/MR/Magazines/Nintendo World")

    assert result.ok is True
    shell.assert_called_once_with("rm -rf '/sdcard/MR/Magazines/Nintendo World'")


def test_delete_remote_dir_rejects_root() -> None:
    result = delete_remote_dir("/")
    assert result.ok is False
