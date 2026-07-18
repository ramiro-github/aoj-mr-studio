"""Helpers for magazine page listing and thumbnail previews."""

from __future__ import annotations

import re
from pathlib import Path

from PIL import Image, ImageTk

PAGE_IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}
_THUMB_SIZE = (96, 128)
_PAGE_NUMBER = re.compile(r"^(\d+)$")


def is_page_image(name: str) -> bool:
    return Path(name).suffix.lower() in PAGE_IMAGE_SUFFIXES


def page_sort_key(name: str) -> tuple[int, int | str]:
    stem = Path(name).stem
    match = _PAGE_NUMBER.fullmatch(stem)
    if match:
        return (0, int(match.group(1)))
    return (1, name.lower())


def list_local_page_images(folder: Path) -> list[Path]:
    if not folder.is_dir():
        return []
    pages = [path for path in folder.iterdir() if path.is_file() and is_page_image(path.name)]
    pages.sort(key=lambda path: page_sort_key(path.name))
    return pages


def make_thumbnail(path: Path, size: tuple[int, int] = _THUMB_SIZE) -> ImageTk.PhotoImage:
    with Image.open(path) as image:
        image = image.convert("RGB")
        image.thumbnail(size, Image.Resampling.LANCZOS)
        return ImageTk.PhotoImage(image)
