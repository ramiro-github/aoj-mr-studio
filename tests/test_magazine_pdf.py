"""Tests for PDF-to-JPG magazine page conversion."""

from pathlib import Path

import pymupdf

from aoj_mr_studio.magazine_pdf import convert_pdf_to_page_jpgs


def make_pdf(path: Path, page_count: int) -> None:
    doc = pymupdf.open()
    for number in range(1, page_count + 1):
        page = doc.new_page(width=200, height=300)
        page.insert_text((50, 100), f"Page {number}")
    doc.save(path)
    doc.close()


def test_convert_creates_numbered_jpgs(tmp_path: Path) -> None:
    pdf = tmp_path / "magazine.pdf"
    make_pdf(pdf, page_count=3)

    output = tmp_path / "out"
    pages = convert_pdf_to_page_jpgs(pdf, output)

    assert [page.name for page in pages] == ["1.jpg", "2.jpg", "3.jpg"]
    for page in pages:
        assert page.is_file()
        assert page.stat().st_size > 0


def test_convert_reports_progress(tmp_path: Path) -> None:
    pdf = tmp_path / "magazine.pdf"
    make_pdf(pdf, page_count=2)

    seen: list[tuple[int, int]] = []
    convert_pdf_to_page_jpgs(pdf, tmp_path / "out", on_progress=lambda p, t: seen.append((p, t)))

    assert seen == [(1, 2), (2, 2)]
