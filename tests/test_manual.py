"""Tests for bundled MR user manual."""

from aoj_mr_studio.manual import FALLBACK_MANUALS, load_user_manual_text, locale_from_manual_link
from aoj_mr_studio.manual_renderer import extract_toc_anchors, heading_to_anchor, is_toc_heading


def test_load_user_manual_text_pt() -> None:
    text = load_user_manual_text("pt")
    assert text
    assert text != FALLBACK_MANUALS["pt"]
    assert "Mixed Reality" in text
    assert "AOJ MR Studio" in text


def test_load_user_manual_text_en() -> None:
    text = load_user_manual_text("en")
    assert text
    assert text != FALLBACK_MANUALS["en"]
    assert "Mixed Reality" in text
    assert "AOJ MR Studio" in text


def test_locale_from_manual_link() -> None:
    assert locale_from_manual_link("MR_USER_GUIDE.pt.md") == "pt"
    assert locale_from_manual_link("MR_USER_GUIDE.en.md") == "en"
    assert locale_from_manual_link("#anchor") is None


def test_toc_anchors_match_section_headings_pt() -> None:
    _assert_toc_matches_headings(load_user_manual_text("pt"))


def test_toc_anchors_match_section_headings_en() -> None:
    _assert_toc_matches_headings(load_user_manual_text("en"))


def _assert_toc_matches_headings(text: str) -> None:
    if text in FALLBACK_MANUALS.values():
        return

    toc_anchors = extract_toc_anchors(text)

    heading_anchors: list[str] = []
    for line in text.splitlines():
        if line.startswith("## ") and not is_toc_heading(line):
            heading_anchors.append(heading_to_anchor(line))

    assert toc_anchors
    assert heading_anchors
    assert toc_anchors == heading_anchors[: len(toc_anchors)]


def test_heading_to_anchor_examples() -> None:
    assert heading_to_anchor("## 1. O que é o Mixed Reality?") == "1-o-que-é-o-mixed-reality"
    assert heading_to_anchor("## 8. Armário de configuração (CRT)") == "8-armário-de-configuração-crt"
    assert heading_to_anchor("## 1. What is Mixed Reality?") == "1-what-is-mixed-reality"
