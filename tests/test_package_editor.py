"""Tests for Quest package YAML editor helpers."""

from pathlib import Path

from aoj_mr_studio.adb_sync import AdbResult
from aoj_mr_studio.package_editor import default_yaml_text, ensure_default_yaml_on_quest


def test_default_yaml_text_uses_glb(tmp_path: Path) -> None:
    text = default_yaml_text("Leon", tmp_path, model_file="leon.glb")
    assert "Leon" in text
    assert "leon.glb" in text
    assert "version: 1" in text


def test_ensure_default_yaml_creates_when_missing(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(
        "aoj_mr_studio.package_editor.remote_file_exists",
        lambda _path: (AdbResult(True, "ok"), False),
    )
    pushed: list[str] = []

    def fake_save(_remote: str, _name: str, _cache: Path, yaml_text: str) -> tuple[bool, str]:
        pushed.append(yaml_text)
        return True, "saved"

    monkeypatch.setattr("aoj_mr_studio.package_editor.save_yaml_to_quest", fake_save)

    ok, created, message = ensure_default_yaml_on_quest(
        "/quest/Custom Objects/Leon",
        "Leon",
        tmp_path,
        "leon.glb",
    )

    assert ok is True
    assert created is True
    assert "leon.glb" in pushed[0]
    assert "model.file" in message or "leon.glb" in message
