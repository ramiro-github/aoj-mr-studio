"""Tests for adb shell path quoting."""

from aoj_mr_studio.adb_sync import quote_shell_path


def test_quote_shell_path_spaces() -> None:
    path = "/sdcard/Android/data/com.curif.AgeOfJoy/MR/Custom Objects"
    quoted = quote_shell_path(path)
    assert quoted.startswith("'") and quoted.endswith("'")
    assert "Custom Objects" in quoted


def test_quote_shell_path_simple() -> None:
    assert quote_shell_path("/sdcard/MR") == "/sdcard/MR"
