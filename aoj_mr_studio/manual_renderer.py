"""Render MR user manual markdown into a styled, read-only Tkinter Text widget."""

from __future__ import annotations

import re
import tkinter as tk
from tkinter import scrolledtext
from typing import Callable

from aoj_mr_studio.theme import (
    ACCENT_FG,
    CODE_BG,
    CODE_FG,
    HR_FG,
    LINK_FG,
    MUTED_FG,
    style_text_widget,
)

_HEADING_RE = re.compile(r"^(#{1,4})\s+(.*)$")
_ORDERED_RE = re.compile(r"^(\d+)\.\s+(.*)$")
_TOC_LINK_RE = re.compile(r"\[([^\]]+)\]\((#[^)]+)\)")
_INLINE_RE = re.compile(
    r"(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)]+\))"
)

_TOC_HEADINGS = frozenset({"índice", "table of contents"})


def is_toc_heading(line: str) -> bool:
    if not line.lstrip().startswith("#"):
        return False
    title = re.sub(r"^#+\s*", "", line).strip().lower()
    return title in _TOC_HEADINGS


def heading_to_anchor(line: str) -> str:
    title = re.sub(r"^#+\s*", "", line).strip()
    slug = title.lower()
    slug = re.sub(r"[\s.()]+", "-", slug)
    slug = re.sub(r"[^\w\-]+", "", slug, flags=re.UNICODE)
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug


def extract_toc_anchors(markdown: str) -> list[str]:
    anchors: list[str] = []
    in_toc = False
    for line in markdown.splitlines():
        if is_toc_heading(line):
            in_toc = True
            continue
        if in_toc and line.strip() == "---":
            break
        if in_toc:
            for target in re.findall(r"\]\((#[^)]+)\)", line):
                anchors.append(target[1:])
    return anchors


def _is_table_row(line: str) -> bool:
    stripped = line.strip()
    return stripped.startswith("|") and stripped.endswith("|")


def _is_table_sep(line: str) -> bool:
    stripped = line.strip()
    if not stripped.startswith("|"):
        return False
    return set(stripped.replace("|", "").replace(":", "").strip()) <= {"-"}


class ManualViewer(scrolledtext.ScrolledText):
    """Read-only styled manual with clickable table-of-contents links."""

    def __init__(
        self,
        master: tk.Misc,
        *,
        on_language_link: Callable[[str], None] | None = None,
        **kwargs,
    ) -> None:
        kwargs.setdefault("wrap", tk.WORD)
        kwargs.setdefault("font", ("Segoe UI", 10))
        kwargs.setdefault("padx", 8)
        kwargs.setdefault("pady", 8)
        kwargs.setdefault("borderwidth", 0)
        kwargs.setdefault("highlightthickness", 0)
        super().__init__(master, **kwargs)
        style_text_widget(self)
        self._on_language_link = on_language_link
        self._configure_tags()
        self.bind("<Key>", self._on_key)

    def _configure_tags(self) -> None:
        self.tag_configure("h1", font=("Segoe UI", 17, "bold"), spacing3=10)
        self.tag_configure(
            "h2",
            font=("Segoe UI", 13, "bold"),
            foreground=ACCENT_FG,
            spacing1=14,
            spacing3=6,
        )
        self.tag_configure("h3", font=("Segoe UI", 11, "bold"), spacing1=10, spacing3=4)
        self.tag_configure("h4", font=("Segoe UI", 10, "bold"), spacing1=8, spacing3=2)
        self.tag_configure("bold", font=("Segoe UI", 10, "bold"))
        self.tag_configure("muted", foreground=MUTED_FG)
        self.tag_configure(
            "code",
            font=("Consolas", 9),
            background=CODE_BG,
            foreground=CODE_FG,
        )
        self.tag_configure(
            "code_block",
            font=("Consolas", 9),
            background=CODE_BG,
            foreground=CODE_FG,
            lmargin1=12,
            lmargin2=12,
            rmargin=12,
            spacing1=4,
            spacing3=4,
        )
        self.tag_configure(
            "blockquote",
            foreground=MUTED_FG,
            lmargin1=18,
            lmargin2=18,
            spacing1=4,
            spacing3=4,
        )
        self.tag_configure("bullet", lmargin1=20, lmargin2=32, spacing3=2)
        self.tag_configure("ordered", lmargin1=20, lmargin2=32, spacing3=2)
        self.tag_configure("table", font=("Consolas", 9), spacing3=2)
        self.tag_configure("table_header", font=("Consolas", 9, "bold"), spacing3=2)
        self.tag_configure("hr", foreground=HR_FG, justify=tk.CENTER, spacing1=8, spacing3=8)
        self.tag_configure("toc_title", font=("Segoe UI", 12, "bold"), spacing1=6, spacing3=4)

    def _on_key(self, event: tk.Event) -> str | None:
        if event.state & 0x4 and event.keysym.lower() in {"c", "a"}:
            return None
        if event.keysym in {
            "Up",
            "Down",
            "Left",
            "Right",
            "Prior",
            "Next",
            "Home",
            "End",
            "Shift_L",
            "Shift_R",
        }:
            return None
        if event.keysym in {"Control_L", "Control_R"}:
            return None
        return "break"

    def load_markdown(self, markdown: str) -> None:
        self.configure(state=tk.NORMAL)
        self.delete("1.0", tk.END)
        for tag in self.tag_names():
            if tag.startswith("link_"):
                self.tag_delete(tag)
        self._render(markdown)
        # Stay editable-blocked (not DISABLED) so TOC link clicks work on all platforms.

    def _render(self, markdown: str) -> None:
        lines = markdown.splitlines()
        index = 0
        in_code = False
        code_lines: list[str] = []
        in_toc = False

        while index < len(lines):
            line = lines[index]
            stripped = line.strip()

            if stripped.startswith("```"):
                if in_code:
                    self._insert_code_block("\n".join(code_lines))
                    code_lines.clear()
                    in_code = False
                else:
                    in_code = True
                index += 1
                continue

            if in_code:
                code_lines.append(line)
                index += 1
                continue

            if stripped == "---":
                self.insert(tk.END, "─" * 42 + "\n", "hr")
                index += 1
                continue

            heading = _HEADING_RE.match(line)
            if heading:
                level = len(heading.group(1))
                title = heading.group(2).strip()
                if is_toc_heading(line):
                    in_toc = True
                    self.insert(tk.END, title + "\n", "toc_title")
                elif level == 1:
                    in_toc = False
                    self._insert_heading_line(title + "\n", "h1", None)
                elif level == 2:
                    in_toc = False
                    anchor = heading_to_anchor(line)
                    self._insert_heading_line(title + "\n", "h2", anchor)
                elif level == 3:
                    in_toc = False
                    self._insert_heading_line(title + "\n", "h3", None)
                else:
                    in_toc = False
                    self._insert_heading_line(title + "\n", "h4", None)
                index += 1
                continue

            if _is_table_row(line):
                table_lines: list[str] = []
                while index < len(lines) and _is_table_row(lines[index]):
                    if not _is_table_sep(lines[index]):
                        table_lines.append(lines[index])
                    index += 1
                self._insert_table(table_lines)
                continue

            if stripped.startswith("> "):
                self._insert_inline_paragraph(stripped[2:] + "\n", "blockquote")
                index += 1
                continue

            ordered = _ORDERED_RE.match(stripped)
            if ordered:
                prefix = f"{ordered.group(1)}. "
                self.insert(tk.END, prefix, "ordered")
                self._insert_inline_paragraph(ordered.group(2) + "\n", "ordered")
                index += 1
                continue

            if stripped.startswith("- "):
                self.insert(tk.END, "• ", "bullet")
                self._insert_inline_paragraph(stripped[2:] + "\n", "bullet")
                index += 1
                continue

            if not stripped:
                self.insert(tk.END, "\n")
                index += 1
                continue

            base_tag = "ordered" if in_toc and _TOC_LINK_RE.search(line) else None
            self._insert_inline_paragraph(line + "\n", base_tag)
            index += 1

        if in_code and code_lines:
            self._insert_code_block("\n".join(code_lines))

    def _insert_heading_line(self, text: str, tag: str, anchor: str | None) -> None:
        if anchor:
            mark = f"anchor_{anchor}"
            self.mark_set(mark, tk.END)
            self.mark_gravity(mark, tk.LEFT)
        self.insert(tk.END, text, tag)

    def _insert_code_block(self, text: str) -> None:
        self.insert(tk.END, text + "\n", "code_block")

    def _insert_table(self, rows: list[str]) -> None:
        for row_index, row in enumerate(rows):
            cells = [cell.strip() for cell in row.strip().strip("|").split("|")]
            line = "  ".join(cells) + "\n"
            tag = "table_header" if row_index == 0 else "table"
            self.insert(tk.END, line, tag)

    def _insert_inline_paragraph(self, text: str, base_tag: str | None) -> None:
        parts = _INLINE_RE.split(text)
        for part in parts:
            if not part:
                continue
            tags = [base_tag] if base_tag else []

            if part.startswith("**") and part.endswith("**"):
                self.insert(tk.END, part[2:-2], ("bold", *tags) if tags else "bold")
                continue

            if part.startswith("`") and part.endswith("`"):
                self.insert(tk.END, part[1:-1], ("code", *tags) if tags else "code")
                continue

            link = re.match(r"^\[([^\]]+)\]\(([^)]+)\)$", part)
            if link:
                label = link.group(1)
                target = link.group(2)
                self._insert_link(label, target, extra_tags=tags)
                continue

            self.insert(tk.END, part, tuple(tags) if tags else ())

    def _insert_link(
        self,
        label: str,
        target: str,
        *,
        extra_tags: list[str] | None = None,
    ) -> None:
        if target.startswith("#"):
            anchor = target[1:]
            tag_name = f"link_{anchor}"
            link_tags = (tag_name, *(extra_tags or []))
            self.insert(tk.END, label, link_tags)
            self.tag_configure(tag_name, foreground=LINK_FG, underline=True)
            self.tag_bind(tag_name, "<Enter>", lambda _e: self.configure(cursor="hand2"))
            self.tag_bind(tag_name, "<Leave>", lambda _e: self.configure(cursor="arrow"))
            self.tag_bind(
                tag_name,
                "<Button-1>",
                lambda _e, a=anchor: self._jump_to_anchor(a),
            )
            return

        lowered = target.lower()
        if lowered.endswith(".md") and self._on_language_link is not None:
            tag_name = f"lang_{lowered.replace('.', '_')}"
            link_tags = (tag_name, *(extra_tags or []))
            self.insert(tk.END, label, link_tags)
            self.tag_configure(tag_name, foreground=LINK_FG, underline=True)
            self.tag_bind(tag_name, "<Enter>", lambda _e: self.configure(cursor="hand2"))
            self.tag_bind(tag_name, "<Leave>", lambda _e: self.configure(cursor="arrow"))
            self.tag_bind(
                tag_name,
                "<Button-1>",
                lambda _e, t=target: self._on_language_link(t),
            )
            return

        tags = ("muted", *(extra_tags or []))
        self.insert(tk.END, label, tags)

    def _jump_to_anchor(self, anchor: str) -> None:
        mark = f"anchor_{anchor}"
        if mark not in self.mark_names():
            return
        self.see(mark)
        self.mark_set(tk.INSERT, mark)
