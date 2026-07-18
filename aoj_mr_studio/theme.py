"""Custom dark theme for AOJ MR Studio (ttk clam + tk widgets)."""

from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

# Neutral charcoal palette — utilitarian, not Fluent/Bootstrap.
APP_BG = "#121418"
PANEL_BG = "#1a1d24"
FIELD_BG = "#22262e"
TEXT_FG = "#e8eaed"
MUTED_FG = "#9aa3b2"
BORDER = "#323844"
CODE_BG = "#1e222a"
CODE_FG = "#d7dbe3"
ACCENT_FG = "#7eb6ff"
LINK_FG = "#8fc1ff"
OK_FG = "#6fbf73"
ERROR_FG = "#e89b7a"
SELECT_BG = "#2f4f7a"
SELECT_FG = "#ffffff"
HR_FG = "#3a4150"
CURSOR_FG = "#e8eaed"
BUTTON_BG = "#2a303a"
BUTTON_ACTIVE = "#343b48"


def apply_dark_theme(root: tk.Tk) -> None:
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(background=APP_BG)
    _configure_ttk(style)
    _apply_hand_cursor(root)
    _enable_windows_dark_title_bar(root)


def _apply_hand_cursor(root: tk.Tk) -> None:
    """Hand cursor on every current and future button-like widget."""

    def set_hand(event: tk.Event) -> None:
        event.widget.configure(cursor="hand2")

    for widget_class in ("TButton", "TCheckbutton"):
        root.bind_class(widget_class, "<Enter>", set_hand, add="+")


def style_text_widget(widget: tk.Text) -> None:
    widget.configure(
        background=FIELD_BG,
        foreground=TEXT_FG,
        insertbackground=CURSOR_FG,
        selectbackground=SELECT_BG,
        selectforeground=SELECT_FG,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=ACCENT_FG,
        borderwidth=0,
        relief=tk.FLAT,
    )


def style_listbox(widget: tk.Listbox) -> None:
    widget.configure(
        background=FIELD_BG,
        foreground=TEXT_FG,
        selectbackground=SELECT_BG,
        selectforeground=SELECT_FG,
        highlightthickness=1,
        highlightbackground=BORDER,
        highlightcolor=ACCENT_FG,
        borderwidth=0,
        relief=tk.FLAT,
        activestyle="none",
    )


def style_menu(menu: tk.Menu) -> None:
    menu.configure(
        background=PANEL_BG,
        foreground=TEXT_FG,
        activebackground=SELECT_BG,
        activeforeground=SELECT_FG,
        borderwidth=0,
        relief=tk.FLAT,
    )


def _configure_ttk(style: ttk.Style) -> None:
    style.configure(".", background=APP_BG, foreground=TEXT_FG, fieldbackground=FIELD_BG)
    style.configure("TFrame", background=APP_BG)
    style.configure("TLabelframe", background=APP_BG, foreground=TEXT_FG, bordercolor=BORDER)
    style.configure("TLabelframe.Label", background=APP_BG, foreground=MUTED_FG)
    style.configure("TLabel", background=APP_BG, foreground=TEXT_FG)
    style.configure("TButton", background=BUTTON_BG, foreground=TEXT_FG, bordercolor=BORDER, lightcolor=BUTTON_BG, darkcolor=BUTTON_BG, focuscolor=BORDER, padding=(10, 5))
    style.map(
        "TButton",
        background=[("active", BUTTON_ACTIVE), ("pressed", SELECT_BG), ("disabled", PANEL_BG)],
        foreground=[("disabled", MUTED_FG)],
    )
    style.configure(
        "TEntry",
        fieldbackground=FIELD_BG,
        foreground=TEXT_FG,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        insertcolor=CURSOR_FG,
        padding=4,
    )
    style.map("TEntry", bordercolor=[("focus", ACCENT_FG)])
    style.configure(
        "TCombobox",
        fieldbackground=FIELD_BG,
        foreground=TEXT_FG,
        background=BUTTON_BG,
        bordercolor=BORDER,
        lightcolor=BORDER,
        darkcolor=BORDER,
        arrowcolor=TEXT_FG,
        padding=3,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", FIELD_BG)],
        foreground=[("readonly", TEXT_FG)],
        bordercolor=[("focus", ACCENT_FG)],
    )
    root_option = style.master
    root_option.option_add("*TCombobox*Listbox.background", FIELD_BG)
    root_option.option_add("*TCombobox*Listbox.foreground", TEXT_FG)
    root_option.option_add("*TCombobox*Listbox.selectBackground", SELECT_BG)
    root_option.option_add("*TCombobox*Listbox.selectForeground", SELECT_FG)

    style.configure("TCheckbutton", background=APP_BG, foreground=TEXT_FG, focuscolor=APP_BG)
    style.map("TCheckbutton", background=[("active", APP_BG)], foreground=[("disabled", MUTED_FG)])
    style.configure(
        "TProgressbar",
        background=ACCENT_FG,
        troughcolor=FIELD_BG,
        bordercolor=BORDER,
        lightcolor=ACCENT_FG,
        darkcolor=ACCENT_FG,
    )
    style.configure(
        "TScrollbar",
        background=BUTTON_BG,
        troughcolor=APP_BG,
        bordercolor=APP_BG,
        arrowcolor=TEXT_FG,
        lightcolor=BUTTON_BG,
        darkcolor=BUTTON_BG,
    )
    style.map("TScrollbar", background=[("active", BUTTON_ACTIVE)])
    style.configure("Horizontal.TSeparator", background=BORDER)
    style.configure("Vertical.TSeparator", background=BORDER)


def _enable_windows_dark_title_bar(root: tk.Tk) -> None:
    if sys.platform != "win32":
        return
    try:
        import ctypes

        root.update_idletasks()
        hwnd = ctypes.windll.user32.GetParent(root.winfo_id())
        value = ctypes.c_int(1)
        for attribute in (20, 19):
            status = ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd,
                attribute,
                ctypes.byref(value),
                ctypes.sizeof(value),
            )
            if status == 0:
                break
    except Exception:
        pass
