"""Bundled Age of Joy MR user manuals (pt-BR and English)."""

from __future__ import annotations

import sys
from functools import lru_cache
from importlib import resources
from pathlib import Path
from typing import Literal

ManualLocale = Literal["pt", "en"]

MANUAL_FILES: dict[ManualLocale, str] = {
    "pt": "MR_USER_GUIDE.pt.md",
    "en": "MR_USER_GUIDE.en.md",
}

MANUAL_LABELS: dict[ManualLocale, str] = {
    "pt": "Guia do usuário — Mixed Reality (pt-BR)",
    "en": "User guide — Mixed Reality (English)",
}

FALLBACK_MANUALS: dict[ManualLocale, str] = {
    "pt": (
        "# Age of Joy — Guia do Usuário: Mixed Reality (MR)\n\n"
        "Manual não encontrado no pacote. Reinstale o AOJ MR Studio ou consulte a documentação do Age of Joy.\n"
    ),
    "en": (
        "# Age of Joy — User Guide: Mixed Reality (MR)\n\n"
        "Manual not found in the package. Reinstall AOJ MR Studio or see Age of Joy documentation.\n"
    ),
}


def _manual_candidates(filename: str) -> list[Path]:
    paths: list[Path] = []
    try:
        ref = resources.files("aoj_mr_studio").joinpath("data", filename)
        if ref.is_file():
            paths.append(Path(str(ref)))
    except (ModuleNotFoundError, TypeError, FileNotFoundError):
        pass

    package_data = Path(__file__).resolve().parent / "data" / filename
    paths.append(package_data)

    if getattr(sys, "frozen", False):
        exe_root = Path(sys.executable).resolve().parent
        paths.append(exe_root / "aoj_mr_studio" / "data" / filename)
        paths.append(exe_root / "data" / filename)

    return paths


def locale_from_manual_link(target: str) -> ManualLocale | None:
    lowered = target.lower()
    if lowered.endswith("mr_user_guide.pt.md"):
        return "pt"
    if lowered.endswith("mr_user_guide.en.md"):
        return "en"
    return None


@lru_cache(maxsize=4)
def load_user_manual_text(locale: ManualLocale = "en") -> str:
    filename = MANUAL_FILES.get(locale, MANUAL_FILES["en"])
    for path in _manual_candidates(filename):
        try:
            if path.is_file():
                return path.read_text(encoding="utf-8")
        except OSError:
            continue
    return FALLBACK_MANUALS.get(locale, FALLBACK_MANUALS["en"])
