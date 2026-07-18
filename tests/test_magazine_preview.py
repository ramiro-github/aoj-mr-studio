"""Tests for magazine page sorting and image filters."""

from pathlib import Path

from aoj_mr_studio.magazine_preview import is_page_image, list_local_page_images, page_sort_key


def test_is_page_image() -> None:
    assert is_page_image("1.jpg") is True
    assert is_page_image("12.JPEG") is True
    assert is_page_image("magazine.yaml") is False


def test_page_sort_key_orders_numerically() -> None:
    names = ["10.jpg", "2.jpg", "1.jpg", "cover.png"]
    assert sorted(names, key=page_sort_key) == ["1.jpg", "2.jpg", "10.jpg", "cover.png"]


def test_list_local_page_images(tmp_path: Path) -> None:
    (tmp_path / "2.jpg").write_bytes(b"a")
    (tmp_path / "1.jpg").write_bytes(b"b")
    (tmp_path / "magazine.yaml").write_text("version: 1\n", encoding="utf-8")

    pages = list_local_page_images(tmp_path)
    assert [page.name for page in pages] == ["1.jpg", "2.jpg"]
