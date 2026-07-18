"""Convert magazine PDFs into numbered page JPGs (1.jpg … N.jpg)."""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pymupdf

DEFAULT_DPI = 120
DEFAULT_JPG_QUALITY = 85

ProgressCallback = Callable[[int, int], None]


def convert_pdf_to_page_jpgs(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = DEFAULT_DPI,
    quality: int = DEFAULT_JPG_QUALITY,
    on_progress: ProgressCallback | None = None,
) -> list[Path]:
    """Render each PDF page to output_dir as 1.jpg, 2.jpg, … in page order."""
    output_dir.mkdir(parents=True, exist_ok=True)
    pages: list[Path] = []
    with pymupdf.open(pdf_path) as doc:
        total = doc.page_count
        for number, page in enumerate(doc, start=1):
            pixmap = page.get_pixmap(dpi=dpi)
            target = output_dir / f"{number}.jpg"
            pixmap.save(target, jpg_quality=quality)
            pages.append(target)
            if on_progress:
                on_progress(number, total)
    return pages
