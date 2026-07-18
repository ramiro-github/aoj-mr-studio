"""Tests for Quest package create/upload helpers."""

from pathlib import Path
from unittest.mock import patch

from aoj_mr_studio.adb_sync import AdbResult
from aoj_mr_studio.package_actions import (
    push_magazine_pdf,
    push_model_to_package,
    validate_package_name,
)


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


def test_push_magazine_pdf_converts_pages_and_uploads(tmp_path: Path) -> None:
    pdf = tmp_path / "Nintendo World.pdf"
    pdf.write_bytes(b"%PDF")

    def fake_convert(pdf_path: Path, output_dir: Path, on_progress=None) -> list[Path]:
        output_dir.mkdir(parents=True, exist_ok=True)
        pages = []
        for number in (1, 2, 3):
            page = output_dir / f"{number}.jpg"
            page.write_bytes(b"jpg")
            pages.append(page)
        return pages

    with (
        patch("aoj_mr_studio.package_actions.remote_dir_exists", return_value=(AdbResult(True, ""), False)),
        patch("aoj_mr_studio.package_actions.create_remote_dir", return_value=AdbResult(True, "")),
        patch("aoj_mr_studio.package_actions.convert_pdf_to_page_jpgs", side_effect=fake_convert),
        patch("aoj_mr_studio.package_actions.push_remote_file", return_value=AdbResult(True, "")) as push,
    ):
        result = push_magazine_pdf(pdf)

    assert result.ok is True
    assert "3 page(s)" in result.message
    assert push.call_count == 3
    remote = push.call_args_list[0].args[1]
    assert remote.endswith("/Magazines/Nintendo World/1.jpg")
    assert push.call_args_list[-1].args[1].endswith("/3.jpg")


def test_push_magazine_pdf_rejects_existing_folder(tmp_path: Path) -> None:
    pdf = tmp_path / "Nintendo World.pdf"
    pdf.write_bytes(b"%PDF")

    with patch(
        "aoj_mr_studio.package_actions.remote_dir_exists",
        return_value=(AdbResult(True, ""), True),
    ):
        result = push_magazine_pdf(pdf)

    assert result.ok is False
    assert "already exists" in result.message


def test_push_magazine_pdf_rejects_non_pdf(tmp_path: Path) -> None:
    other = tmp_path / "page.jpg"
    other.write_bytes(b"jpg")

    result = push_magazine_pdf(other)
    assert result.ok is False
    assert "pdf" in result.message.lower()
