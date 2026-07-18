"""AOJ MR Studio desktop GUI."""

from __future__ import annotations

import shutil
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk

from aoj_mr_studio.adb_path import adb_source_label, find_adb
from aoj_mr_studio.adb_sync import (
    RemoteEntry,
    check_device_connected,
    delete_remote_dir,
    list_remote_dir,
    parent_remote_path,
    pull_remote_dir,
)
from aoj_mr_studio.component_editor import ComponentsEditor
from aoj_mr_studio.component_schema import apply_components_to_yaml_text, validate_component_rows
from aoj_mr_studio.manual import (
    MANUAL_LABELS,
    ManualLocale,
    locale_from_manual_link,
    load_user_manual_text,
)
from aoj_mr_studio.manual_renderer import ManualViewer
from aoj_mr_studio.magazine_config import (
    MAGAZINE_SHELF_LIMIT,
    active_magazine_count,
    ensure_magazines_yaml,
    load_magazines_yaml,
    save_magazines_yaml,
)
from aoj_mr_studio.magazine_preview import list_local_page_images, make_thumbnail
from aoj_mr_studio.placement_editor import PlacementEditor
from aoj_mr_studio.placement_schema import apply_placement_to_yaml_text
from aoj_mr_studio.config import (
    APP_NAME,
    OBJECT_YAML_NAME,
    QUEST_CUSTOM_OBJECTS,
    QUEST_MAGAZINES,
)
from aoj_mr_studio.package_actions import (
    create_quest_package,
    push_magazine_pdf,
    push_model_to_package,
)
from aoj_mr_studio.package_defaults import sync_package_context
from aoj_mr_studio.theme import (
    ERROR_FG,
    FIELD_BG,
    MUTED_FG,
    OK_FG,
    apply_dark_theme,
    style_listbox,
    style_menu,
    style_text_widget,
)
from aoj_mr_studio.package_editor import (
    default_yaml_text,
    ensure_default_yaml_on_quest,
    first_glb_in_package,
    pull_package_yaml,
    save_yaml_to_quest,
)

class StudioApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(APP_NAME)
        self.geometry("980x720")
        self.minsize(860, 600)
        apply_dark_theme(self)

        self.quest_path = QUEST_CUSTOM_OBJECTS
        self._quest_entries: list[tuple[str, bool]] = []
        self._magazine_activation: dict[str, bool] = {}
        self._magazine_check_vars: dict[str, tk.BooleanVar] = {}
        self._selected_magazine_row: str | None = None
        self.selected_package_path: str | None = None
        self.selected_package_name: str | None = None
        self._pending_custom_glb: Path | None = None
        self.selected_magazine_path: str | None = None
        self.selected_magazine_name: str | None = None
        self._magazine_thumbnails: list[tk.PhotoImage] = []
        self.package_yaml_on_quest = False
        self._cache_root = Path.home() / ".aoj_mr_studio" / "cache"
        self._suppress_yaml_sync = False
        self._yaml_sync_job: str | None = None

        self.container = ttk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.loading_frame = ttk.Frame(self.container)
        self.home_frame = ttk.Frame(self.container)
        self.workspace_frame = ttk.Frame(self.container)
        self.package_frame = ttk.Frame(self.container)
        self.magazine_frame = ttk.Frame(self.container)

        self._device_connected = False
        self._device_status_message = ""
        self._startup_connect_running = False
        self._manual_locale: ManualLocale = "en"

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=(6, 2)).pack(
            fill=tk.X, side=tk.BOTTOM
        )

        self._build_loading_screen()
        self._build_home_screen()
        self._build_workspace_screen()
        self._build_package_screen()
        self._build_magazine_screen()
        self.show_loading_screen()
        self.after(80, self._begin_startup_connect)

    def _hide_all_screens(self) -> None:
        self.loading_frame.pack_forget()
        self.home_frame.pack_forget()
        self.workspace_frame.pack_forget()
        self.package_frame.pack_forget()
        self.magazine_frame.pack_forget()

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def show_loading_screen(self) -> None:
        self._hide_all_screens()
        self.loading_frame.pack(fill=tk.BOTH, expand=True)
        self.title(APP_NAME)
        self.set_status("Connecting to Meta Quest…")
        if hasattr(self, "loading_progress"):
            self.loading_progress.start(12)

    def show_home_screen(self) -> None:
        self._hide_all_screens()
        if hasattr(self, "loading_progress"):
            self.loading_progress.stop()
        self.home_frame.pack(fill=tk.BOTH, expand=True)
        self.title(f"{APP_NAME} — Home")
        self._refresh_home_connection_ui()
        self.set_status(self._device_status_message or "Home")

    def show_workspace_screen(self) -> None:
        self._hide_all_screens()
        self.workspace_frame.pack(fill=tk.BOTH, expand=True)
        if self._is_magazines_root():
            self.title(f"{APP_NAME} — Magazines")
            self.create_folder_btn.configure(text="New Magazine")
            self.workspace_hint_var.set(
                f"Check to activate on the shelf (max {MAGAZINE_SHELF_LIMIT}). "
                "Double-click to preview pages."
            )
        else:
            self.title(f"{APP_NAME} — Custom Objects")
            self.create_folder_btn.configure(text="New Custom Object")
            self.workspace_hint_var.set(
                f"Double-click a package folder to edit {OBJECT_YAML_NAME}."
            )
        self.refresh_quest_listing()

    def show_package_screen(self) -> None:
        if not self.selected_package_path or not self.selected_package_name:
            return

        self._hide_all_screens()
        self.package_frame.pack(fill=tk.BOTH, expand=True)
        name = self.selected_package_name
        self.title(f"{APP_NAME} — {name}")
        self.package_title_var.set(name)
        self.package_path_var.set(self.selected_package_path)
        if self._pending_custom_glb is not None:
            self.load_pending_package_editor()
        else:
            self.load_package_editor()

    def show_magazine_screen(self) -> None:
        if not self.selected_magazine_path or not self.selected_magazine_name:
            return

        self._hide_all_screens()
        self.magazine_frame.pack(fill=tk.BOTH, expand=True)
        name = self.selected_magazine_name
        self.title(f"{APP_NAME} — {name}")
        self.magazine_title_var.set(name)
        self.magazine_path_var.set(self.selected_magazine_path)
        self.load_magazine_preview()

    def _build_loading_screen(self) -> None:
        outer = ttk.Frame(self.loading_frame, padding=24)
        outer.pack(fill=tk.BOTH, expand=True)

        center = ttk.Frame(outer)
        center.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        ttk.Label(
            center,
            text="Connecting to Meta Quest…",
            font=("", 16),
        ).pack(pady=(0, 16))

        self.loading_progress = ttk.Progressbar(
            center,
            mode="indeterminate",
            length=280,
        )
        self.loading_progress.pack()

        ttk.Label(
            center,
            text="Verifique o cabo USB, o modo desenvolvedor e a depuração USB.",
            justify=tk.CENTER,
            foreground=MUTED_FG,
        ).pack(pady=(16, 0))

    def _build_home_screen(self) -> None:
        outer = ttk.Frame(self.home_frame, padding=(12, 12, 12, 8))
        outer.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(outer)
        header.pack(fill=tk.X)

        ttk.Label(header, text=APP_NAME, font=("", 16, "bold")).pack(side=tk.LEFT)

        actions = ttk.Frame(header)
        actions.pack(side=tk.RIGHT)

        self.home_reconnect_btn = ttk.Button(
            actions,
            text="Reconnect",
            command=self._begin_startup_connect,
        )
        self.home_reconnect_btn.pack(side=tk.RIGHT)

        status_row = ttk.Frame(outer)
        status_row.pack(fill=tk.X, pady=(10, 8))
        ttk.Label(status_row, text="Quest:").pack(side=tk.LEFT)
        self.home_connection_var = tk.StringVar(value="Checking connection…")
        self.home_connection_label = ttk.Label(
            status_row,
            textvariable=self.home_connection_var,
            foreground=MUTED_FG,
        )
        self.home_connection_label.pack(side=tk.LEFT, padx=(6, 0))

        buttons_row = ttk.Frame(outer)
        buttons_row.pack(fill=tk.X, pady=(0, 8))

        self.home_open_btn = ttk.Button(
            buttons_row,
            text="Custom Object",
            command=self.open_quest_custom_objects,
        )
        self.home_open_btn.pack(side=tk.LEFT)

        self.home_magazines_btn = ttk.Button(
            buttons_row,
            text="Magazine",
            command=self.open_quest_magazines,
        )
        self.home_magazines_btn.pack(side=tk.LEFT, padx=(6, 0))

        adb = find_adb()
        if not adb:
            ttk.Label(
                outer,
                text="adb not found — run scripts/copy-adb.ps1",
                foreground=ERROR_FG,
            ).pack(anchor=tk.W, pady=(0, 6))

        manual_bar = ttk.Frame(outer)
        manual_bar.pack(fill=tk.X, pady=(4, 0))

        ttk.Label(manual_bar, text="Manual:").pack(side=tk.LEFT)

        self.manual_lang_var = tk.StringVar(value="English")
        self.manual_lang_combo = ttk.Combobox(
            manual_bar,
            textvariable=self.manual_lang_var,
            values=("English", "pt-BR"),
            state="readonly",
            width=10,
        )
        self.manual_lang_combo.pack(side=tk.LEFT, padx=(6, 0))
        self.manual_lang_combo.bind("<<ComboboxSelected>>", self._on_manual_language_selected)

        self.manual_frame = ttk.LabelFrame(
            outer,
            text=MANUAL_LABELS["en"],
            padding=(8, 6),
        )
        self.manual_frame.pack(fill=tk.BOTH, expand=True, pady=(6, 0))

        self.manual_view = ManualViewer(
            self.manual_frame,
            on_language_link=self._on_manual_language_link,
        )
        self.manual_view.pack(fill=tk.BOTH, expand=True)
        self._load_manual_view("en")

    def _load_manual_view(self, locale: ManualLocale) -> None:
        self._manual_locale = locale
        self.manual_frame.configure(text=MANUAL_LABELS[locale])
        self.manual_view.load_markdown(load_user_manual_text(locale))
        self.manual_view.see("1.0")

    def _on_manual_language_selected(self, _event: tk.Event | None = None) -> None:
        locale: ManualLocale = "en" if self.manual_lang_var.get() == "English" else "pt"
        self._load_manual_view(locale)

    def _on_manual_language_link(self, target: str) -> None:
        locale = locale_from_manual_link(target)
        if locale is None:
            return
        self.manual_lang_var.set("English" if locale == "en" else "pt-BR")
        self._load_manual_view(locale)

    def _refresh_home_connection_ui(self) -> None:
        if not hasattr(self, "home_connection_var"):
            return

        if self._device_connected:
            self.home_connection_var.set(self._device_status_message)
            self.home_connection_label.configure(foreground=OK_FG)
            self.home_open_btn.configure(state=tk.NORMAL)
        else:
            self.home_connection_var.set(self._device_status_message or "Not connected")
            self.home_connection_label.configure(foreground=ERROR_FG)
            self.home_open_btn.configure(state=tk.DISABLED)

        reconnect_state = tk.DISABLED if self._startup_connect_running else tk.NORMAL
        self.home_reconnect_btn.configure(state=reconnect_state)

    def _begin_startup_connect(self) -> None:
        if self._startup_connect_running:
            return

        self._startup_connect_running = True
        self.show_loading_screen()
        threading.Thread(target=self._startup_connect_worker, daemon=True).start()

    def _startup_connect_worker(self) -> None:
        result = check_device_connected()
        self.after(0, lambda: self._on_startup_connect_done(result.ok, result.message))

    def _on_startup_connect_done(self, connected: bool, message: str) -> None:
        self._startup_connect_running = False
        self._device_connected = connected
        self._device_status_message = message
        self.show_home_screen()

    def open_quest_custom_objects(self) -> None:
        self._open_quest_folder(QUEST_CUSTOM_OBJECTS, "Custom Objects")

    def open_quest_magazines(self) -> None:
        self._open_quest_folder(QUEST_MAGAZINES, "Magazines")

    def _open_quest_folder(self, remote_path: str, label: str) -> None:
        if not self._device_connected:
            messagebox.showerror(
                APP_NAME,
                self._device_status_message or "Meta Quest not connected.",
            )
            return

        self.set_status(f"Opening {label}…")
        self.update_idletasks()

        device = check_device_connected()
        if not device.ok:
            self._device_connected = False
            self._device_status_message = device.message
            self._refresh_home_connection_ui()
            messagebox.showerror(APP_NAME, device.message)
            self.set_status(device.message)
            return

        self.quest_path = remote_path
        self.quest_path_var.set(self.quest_path)
        self.show_workspace_screen()

        result, entries = list_remote_dir(self.quest_path)
        if not result.ok:
            messagebox.showerror(APP_NAME, result.message)
            self.set_status(result.message)
            self.show_home_screen()
            return

        config_created = False
        if remote_path.rstrip("/") == QUEST_MAGAZINES.rstrip("/"):
            config_result, config_created = ensure_magazines_yaml(entries, self._cache_root)
            if not config_result.ok:
                messagebox.showerror(APP_NAME, config_result.message)
                self.set_status(config_result.message)
                return
            if config_created:
                self.refresh_quest_listing()

        count = len(entries)
        status = f"Quest {label} — {count} item(s) ({adb_source_label()})"
        if config_created:
            status += " — created magazines.yaml"
        self.set_status(status)

    def _build_workspace_screen(self) -> None:
        header = ttk.Frame(self.workspace_frame, padding=(8, 8, 8, 4))
        header.pack(fill=tk.X)

        ttk.Button(header, text="Refresh", command=self.refresh_quest_listing).pack(side=tk.LEFT)
        self.create_folder_btn = ttk.Button(
            header,
            text="New Custom Object",
            command=self.create_workspace_item,
        )
        self.create_folder_btn.pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(header, text="Home", command=self.show_home_screen).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(header, text="Check device", command=self.check_device).pack(side=tk.RIGHT)

        path_row = ttk.Frame(header)
        path_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(path_row, text="Quest:").pack(side=tk.LEFT)
        self.quest_path_var = tk.StringVar(value=self.quest_path)
        ttk.Entry(path_row, textvariable=self.quest_path_var, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0)
        )

        self.workspace_hint_var = tk.StringVar(
            value=f"Double-click a package folder to edit {OBJECT_YAML_NAME}."
        )
        hint = ttk.Label(
            self.workspace_frame,
            textvariable=self.workspace_hint_var,
            foreground=MUTED_FG,
            padding=(8, 0, 8, 4),
        )
        hint.pack(anchor=tk.W)

        list_frame = ttk.Frame(self.workspace_frame, padding=(8, 0, 8, 8))
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.quest_listbox = tk.Listbox(list_frame, font=("Consolas", 10))
        style_listbox(self.quest_listbox)
        self.quest_list_scroll = ttk.Scrollbar(
            list_frame,
            orient=tk.VERTICAL,
            command=self.quest_listbox.yview,
        )
        self.quest_listbox.configure(yscrollcommand=self.quest_list_scroll.set)
        self.quest_listbox.bind("<Double-Button-1>", self.on_quest_open_selected)
        self.quest_listbox.bind("<Button-3>", self.on_quest_context_menu)

        self.magazine_list_wrap = ttk.Frame(list_frame)
        self.magazine_list_canvas = tk.Canvas(
            self.magazine_list_wrap,
            highlightthickness=0,
            background=FIELD_BG,
        )
        self.magazine_list_scroll = ttk.Scrollbar(
            self.magazine_list_wrap,
            orient=tk.VERTICAL,
            command=self.magazine_list_canvas.yview,
        )
        self.magazine_list_canvas.configure(yscrollcommand=self.magazine_list_scroll.set)
        self.magazine_list_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.magazine_list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.magazine_rows_frame = ttk.Frame(self.magazine_list_canvas)
        self._magazine_list_window = self.magazine_list_canvas.create_window(
            (0, 0),
            window=self.magazine_rows_frame,
            anchor=tk.NW,
        )
        self.magazine_rows_frame.bind(
            "<Configure>",
            lambda _event: self.magazine_list_canvas.configure(
                scrollregion=self.magazine_list_canvas.bbox("all")
            ),
        )
        self.magazine_list_canvas.bind("<Configure>", self._on_magazine_list_configure)
        self.magazine_list_canvas.bind("<MouseWheel>", self._on_magazine_list_mousewheel)
        self.magazine_rows_frame.bind("<MouseWheel>", self._on_magazine_list_mousewheel)

        self.workspace_context_menu = tk.Menu(self, tearoff=False)
        style_menu(self.workspace_context_menu)
        self.workspace_context_menu.add_command(
            label="Delete folder",
            command=self.delete_selected_folder,
        )

        self._show_custom_objects_list()

    def _on_magazine_list_configure(self, event: tk.Event) -> None:
        self.magazine_list_canvas.itemconfigure(self._magazine_list_window, width=event.width)

    def _on_magazine_list_mousewheel(self, event: tk.Event) -> None:
        if not self.magazine_list_wrap.winfo_ismapped():
            return
        self.magazine_list_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _show_custom_objects_list(self) -> None:
        self.magazine_list_wrap.pack_forget()
        self.quest_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.quest_list_scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _show_magazine_list(self) -> None:
        self.quest_listbox.pack_forget()
        self.quest_list_scroll.pack_forget()
        self.magazine_list_wrap.pack(fill=tk.BOTH, expand=True)

    def create_workspace_item(self) -> None:
        if self._is_magazines_root():
            self.add_magazine_pdf()
        else:
            self.create_custom_object_from_glb()

    def create_custom_object_from_glb(self) -> None:
        local_glb = filedialog.askopenfilename(
            parent=self,
            title="Select GLB model for new Custom Object",
            filetypes=[("GLB model", "*.glb"), ("All files", "*.*")],
        )
        if not local_glb:
            return

        glb_path = Path(local_glb)
        package_name = glb_path.stem.strip()
        remote = f"{QUEST_CUSTOM_OBJECTS.rstrip('/')}/{package_name}"
        self.selected_package_path = remote
        self.selected_package_name = package_name
        self._pending_custom_glb = glb_path
        self.show_package_screen()

    def add_magazine_pdf(self) -> None:
        local_pdf = filedialog.askopenfilename(
            parent=self,
            title="Select magazine PDF",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")],
        )
        if not local_pdf:
            return

        pdf_path = Path(local_pdf)
        self.set_status(f"Converting {pdf_path.name}…")
        self.update_idletasks()

        def report_convert(page: int, total: int) -> None:
            self.set_status(f"Converting {pdf_path.name} — page {page}/{total}…")
            self.update_idletasks()

        def report_upload(page: int, total: int) -> None:
            self.set_status(f"Uploading {pdf_path.name} — page {page}/{total}…")
            self.update_idletasks()

        result = push_magazine_pdf(
            pdf_path,
            on_progress=report_convert,
            on_upload_progress=report_upload,
        )
        if not result.ok:
            messagebox.showerror(APP_NAME, result.message)
            self.set_status(result.message)
            return

        self.refresh_quest_listing()
        self.set_status(result.message)
        messagebox.showinfo(APP_NAME, result.message)

    def add_model_to_package(self) -> None:
        if not self.selected_package_name:
            return

        package_name = self.selected_package_name
        local_glb = filedialog.askopenfilename(
            parent=self,
            title=f"Add model to {package_name}",
            filetypes=[("GLB model", "*.glb"), ("All files", "*.*")],
        )
        if not local_glb:
            return

        self.set_status(f"Uploading {Path(local_glb).name}…")
        self.update_idletasks()

        result = push_model_to_package(package_name, Path(local_glb))
        if not result.ok:
            messagebox.showerror(APP_NAME, result.message)
            self.set_status(result.message)
            return

        glb_name = result.file_name or Path(local_glb).name

        cached_glb = self._cache_root / package_name / glb_name
        if cached_glb.is_file():
            cached_glb.unlink()
        yaml_ok, yaml_created, yaml_message = ensure_default_yaml_on_quest(
            self.selected_package_path or "",
            package_name,
            self._cache_root,
            glb_name,
        )
        if not yaml_ok:
            messagebox.showwarning(
                APP_NAME,
                f"Model uploaded, but {OBJECT_YAML_NAME} could not be created:\n{yaml_message}",
            )

        self.load_package_editor()

        status = result.message
        if yaml_created:
            status += f" — default {OBJECT_YAML_NAME} created"
        self.set_status(status)

        detail = result.message + f"\n\n{package_name}/{glb_name}"
        if result.replaced:
            detail += "\n\nSame filename on Quest — previous model was overwritten."
        if yaml_created:
            detail += f"\n\nDefault {OBJECT_YAML_NAME} created (model.file: {glb_name})"
        messagebox.showinfo(APP_NAME, detail)

    def _build_package_screen(self) -> None:
        header = ttk.Frame(self.package_frame, padding=(8, 8, 8, 4))
        header.pack(fill=tk.X)

        ttk.Button(header, text="Back", command=self.show_workspace_screen).pack(side=tk.LEFT)
        ttk.Button(header, text="Home", command=self.show_home_screen).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(header, text="Refresh", command=self.show_package_screen).pack(side=tk.LEFT, padx=(6, 0))
        self.add_model_btn = ttk.Button(
            header,
            text="Add model",
            command=self.add_model_to_package,
        )
        self.add_model_btn.pack(side=tk.LEFT, padx=(6, 0))

        title_row = ttk.Frame(header)
        title_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(title_row, text="Package:").pack(side=tk.LEFT)
        self.package_title_var = tk.StringVar(value="")
        ttk.Label(title_row, textvariable=self.package_title_var, font=("", 12, "bold")).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        path_row = ttk.Frame(header)
        path_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(path_row, text="Quest:").pack(side=tk.LEFT)
        self.package_path_var = tk.StringVar(value="")
        ttk.Entry(path_row, textvariable=self.package_path_var, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0)
        )

        self.package_yaml_status_var = tk.StringVar(value="")
        ttk.Label(
            self.package_frame,
            textvariable=self.package_yaml_status_var,
            foreground=MUTED_FG,
            padding=(8, 4, 8, 0),
        ).pack(anchor=tk.W)

        files_row = ttk.Frame(self.package_frame, padding=(8, 0, 8, 4))
        files_row.pack(fill=tk.X)
        ttk.Label(files_row, text="Files on Quest:").pack(side=tk.LEFT)
        self.package_files_var = tk.StringVar(value="")
        ttk.Label(
            files_row,
            textvariable=self.package_files_var,
            font=("Consolas", 9),
            foreground=MUTED_FG,
        ).pack(side=tk.LEFT, padx=(6, 0))

        self.placement_editor = PlacementEditor(
            self.package_frame,
            on_change=self._schedule_yaml_sync,
        )
        self.placement_editor.pack(fill=tk.X, padx=8, pady=(0, 4))

        self.components_editor = ComponentsEditor(
            self.package_frame,
            on_change=self._schedule_yaml_sync,
        )
        self.components_editor.pack(fill=tk.X, padx=8, pady=(0, 4))

        editor_frame = ttk.Frame(self.package_frame, padding=(8, 4, 8, 4))
        editor_frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(editor_frame, text=f"{OBJECT_YAML_NAME}:").pack(anchor=tk.W)

        self.yaml_editor = scrolledtext.ScrolledText(
            editor_frame,
            font=("Consolas", 10),
            wrap=tk.NONE,
            undo=True,
            height=14,
        )
        style_text_widget(self.yaml_editor)
        self.yaml_editor.pack(fill=tk.BOTH, expand=True, pady=(4, 0))

        footer = ttk.Frame(self.package_frame, padding=(8, 8, 8, 8))
        footer.pack(fill=tk.X, side=tk.BOTTOM)
        self.create_yaml_btn = ttk.Button(
            footer,
            text=f"Create {OBJECT_YAML_NAME}",
            command=self.create_package_yaml,
        )
        self.create_yaml_btn.pack(side=tk.LEFT)
        ttk.Button(
            footer,
            text="Save to Meta Quest",
            command=self.save_package_yaml,
        ).pack(side=tk.RIGHT)

    def _build_magazine_screen(self) -> None:
        header = ttk.Frame(self.magazine_frame, padding=(8, 8, 8, 4))
        header.pack(fill=tk.X)

        ttk.Button(header, text="Back", command=self.show_workspace_screen).pack(side=tk.LEFT)
        ttk.Button(header, text="Home", command=self.show_home_screen).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(header, text="Refresh", command=self.load_magazine_preview).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        title_row = ttk.Frame(header)
        title_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(title_row, text="Magazine:").pack(side=tk.LEFT)
        self.magazine_title_var = tk.StringVar(value="")
        ttk.Label(title_row, textvariable=self.magazine_title_var, font=("", 12, "bold")).pack(
            side=tk.LEFT, padx=(6, 0)
        )

        path_row = ttk.Frame(header)
        path_row.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(path_row, text="Quest:").pack(side=tk.LEFT)
        self.magazine_path_var = tk.StringVar(value="")
        ttk.Entry(path_row, textvariable=self.magazine_path_var, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0)
        )

        self.magazine_status_var = tk.StringVar(value="")
        ttk.Label(
            self.magazine_frame,
            textvariable=self.magazine_status_var,
            foreground=MUTED_FG,
            padding=(8, 4, 8, 0),
        ).pack(anchor=tk.W)

        preview_wrap = ttk.Frame(self.magazine_frame, padding=(8, 4, 8, 8))
        preview_wrap.pack(fill=tk.BOTH, expand=True)

        self.magazine_canvas = tk.Canvas(preview_wrap, highlightthickness=0, background=FIELD_BG)
        scroll = ttk.Scrollbar(
            preview_wrap,
            orient=tk.VERTICAL,
            command=self.magazine_canvas.yview,
        )
        self.magazine_canvas.configure(yscrollcommand=scroll.set)
        self.magazine_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)

        self.magazine_thumbs_frame = ttk.Frame(self.magazine_canvas)
        self._magazine_canvas_window = self.magazine_canvas.create_window(
            (0, 0),
            window=self.magazine_thumbs_frame,
            anchor=tk.NW,
        )
        self.magazine_thumbs_frame.bind(
            "<Configure>",
            lambda _event: self.magazine_canvas.configure(
                scrollregion=self.magazine_canvas.bbox("all")
            ),
        )
        self.magazine_canvas.bind("<Configure>", self._on_magazine_canvas_configure)
        self.magazine_canvas.bind_all("<MouseWheel>", self._on_magazine_mousewheel)

    def _on_magazine_canvas_configure(self, event: tk.Event) -> None:
        self.magazine_canvas.itemconfigure(self._magazine_canvas_window, width=event.width)

    def _on_magazine_mousewheel(self, event: tk.Event) -> None:
        if not self.magazine_frame.winfo_ismapped():
            return
        self.magazine_canvas.yview_scroll(int(-event.delta / 120), "units")

    def _is_custom_objects_root(self) -> bool:
        return self.quest_path.rstrip("/") == QUEST_CUSTOM_OBJECTS.rstrip("/")

    def _is_magazines_root(self) -> bool:
        return self.quest_path.rstrip("/") == QUEST_MAGAZINES.rstrip("/")

    def _get_selected_entry(self) -> tuple[str, bool] | None:
        if self._is_magazines_root():
            if not self._selected_magazine_row:
                return None
            return self._selected_magazine_row, True

        selection = self.quest_listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        if index >= len(self._quest_entries):
            return None
        return self._quest_entries[index]

    def select_package(self, remote_path: str, package_name: str) -> None:
        self._pending_custom_glb = None
        self.selected_package_path = remote_path
        self.selected_package_name = package_name
        self.show_package_screen()

    def open_magazine(self, remote_path: str, magazine_name: str) -> None:
        self.selected_magazine_path = remote_path
        self.selected_magazine_name = magazine_name
        self.show_magazine_screen()

    def load_magazine_preview(self) -> None:
        if not self.selected_magazine_path or not self.selected_magazine_name:
            return

        name = self.selected_magazine_name
        remote = self.selected_magazine_path
        self._clear_magazine_thumbnails()
        self.magazine_status_var.set(f"Loading pages from Quest…")
        self.set_status(f"Loading magazine {name}…")
        self.update_idletasks()

        local_dir = self._cache_root / "magazines" / name
        pull = pull_remote_dir(remote, local_dir)
        if not pull.ok:
            self.magazine_status_var.set(pull.message)
            self.set_status(pull.message)
            messagebox.showerror(APP_NAME, pull.message)
            return

        pages = list_local_page_images(local_dir)
        if not pages:
            self.magazine_status_var.set("No page images found in this magazine.")
            self.set_status(f"{name} — no pages")
            return

        columns = 6
        for index, page in enumerate(pages):
            try:
                photo = make_thumbnail(page)
            except OSError as exc:
                self.set_status(f"Failed to load {page.name}: {exc}")
                continue

            self._magazine_thumbnails.append(photo)
            cell = ttk.Frame(self.magazine_thumbs_frame, padding=4)
            row, col = divmod(index, columns)
            cell.grid(row=row, column=col, sticky=tk.NW, padx=4, pady=4)

            ttk.Label(cell, image=photo).pack()
            ttk.Label(cell, text=page.name, foreground=MUTED_FG).pack()

            if index % 12 == 11:
                self.magazine_status_var.set(f"Building preview… {index + 1}/{len(pages)}")
                self.update_idletasks()

        self.magazine_status_var.set(f"{len(pages)} page(s)")
        self.set_status(f"{name} — {len(pages)} page(s)")

    def _clear_magazine_thumbnails(self) -> None:
        for child in self.magazine_thumbs_frame.winfo_children():
            child.destroy()
        self._magazine_thumbnails.clear()

    def load_pending_package_editor(self) -> None:
        if (
            self._pending_custom_glb is None
            or not self.selected_package_path
            or not self.selected_package_name
        ):
            return

        name = self.selected_package_name
        source_glb = self._pending_custom_glb
        cache_dir = self._cache_root / name
        cache_dir.mkdir(parents=True, exist_ok=True)
        cached_glb = cache_dir / source_glb.name
        if source_glb.resolve() != cached_glb.resolve():
            shutil.copy2(source_glb, cached_glb)

        entries = [RemoteEntry(name=source_glb.name, is_dir=False)]
        package_context = sync_package_context(
            self.selected_package_path,
            name,
            self._cache_root,
            entries,
        )
        self.components_editor.set_package_context(package_context, refresh=False)

        text = default_yaml_text(name, self._cache_root, model_file=source_glb.name)
        self.package_yaml_on_quest = False
        self.package_files_var.set(f"{source_glb.name} (local — not uploaded)")
        self.package_yaml_status_var.set(
            "New Custom Object — edit settings, then click Save to Meta Quest."
        )
        self.add_model_btn.configure(state=tk.DISABLED)

        self._suppress_yaml_sync = True
        self.yaml_editor.delete("1.0", tk.END)
        self.yaml_editor.insert(tk.END, text)
        self.placement_editor.load_from_yaml_text(text)
        self.components_editor.load_from_yaml_text(text)
        self.create_yaml_btn.configure(state=tk.DISABLED)
        self._suppress_yaml_sync = False
        self.components_editor.refresh_row_suggestions()
        self.set_status(f"{name} ready locally — not uploaded to Quest")

    def load_package_editor(self) -> None:
        if not self.selected_package_path or not self.selected_package_name:
            return

        self.add_model_btn.configure(state=tk.NORMAL)
        name = self.selected_package_name
        remote = self.selected_package_path
        self.set_status(f"Loading {name}…")
        self.update_idletasks()

        result, entries = list_remote_dir(remote)
        package_context = sync_package_context(remote, name, self._cache_root, entries)
        self.components_editor.set_package_context(package_context, refresh=False)
        if result.ok:
            if entries:
                labels = []
                for entry in entries:
                    prefix = "[DIR] " if entry.is_dir else ""
                    labels.append(prefix + entry.name)
                self.package_files_var.set(", ".join(labels))
            else:
                self.package_files_var.set("(empty folder)")
        else:
            self.package_files_var.set("(could not list files)")

        exists, text, message = pull_package_yaml(remote, name, self._cache_root)
        self.package_yaml_on_quest = exists
        self.package_yaml_status_var.set(message)

        self._suppress_yaml_sync = True
        self.yaml_editor.delete("1.0", tk.END)
        if text:
            self.yaml_editor.insert(tk.END, text)
            self.placement_editor.load_from_yaml_text(text)
            self.components_editor.load_from_yaml_text(text)
            self.create_yaml_btn.configure(state=tk.DISABLED)
        elif exists:
            self.placement_editor.clear()
            self.components_editor.clear_rows()
            self.create_yaml_btn.configure(state=tk.DISABLED)
        else:
            self.placement_editor.clear()
            self.components_editor.clear_rows()
            self.create_yaml_btn.configure(state=tk.NORMAL)
        self._suppress_yaml_sync = False

        self.components_editor.refresh_row_suggestions()

        self.set_status(message)

    def _schedule_yaml_sync(self) -> None:
        if self._suppress_yaml_sync:
            return
        if self._yaml_sync_job is not None:
            self.after_cancel(self._yaml_sync_job)
        self._yaml_sync_job = self.after(120, self._sync_yaml_from_components)

    def _sync_yaml_from_components(self) -> None:
        self._yaml_sync_job = None
        if self._suppress_yaml_sync or not hasattr(self, "yaml_editor"):
            return

        try:
            merged = self._yaml_text_with_components()
        except ValueError:
            return

        self._suppress_yaml_sync = True
        self.yaml_editor.delete("1.0", tk.END)
        self.yaml_editor.insert(tk.END, merged)
        self._suppress_yaml_sync = False

    def create_package_yaml(self) -> None:
        if not self.selected_package_name or not self.selected_package_path:
            return

        if self.yaml_editor.get("1.0", tk.END).strip():
            if not messagebox.askyesno(
                APP_NAME,
                f"The editor already has content.\nReplace with a new {OBJECT_YAML_NAME} template?",
            ):
                return

        name = self.selected_package_name
        model_file = first_glb_in_package(self.selected_package_path)
        text = default_yaml_text(name, self._cache_root, model_file=model_file)

        self.yaml_editor.delete("1.0", tk.END)
        self.yaml_editor.insert(tk.END, text)
        self.placement_editor.clear()
        self.components_editor.clear_rows()
        self.package_yaml_status_var.set(
            f"Template created"
            + (f" — model.file set to {model_file}" if model_file else " — add your .glb filename")
        )
        self.set_status(f"Created {OBJECT_YAML_NAME} template for {name}")

    def _yaml_text_with_components(self) -> str:
        yaml_text = self.yaml_editor.get("1.0", tk.END).strip()
        if not yaml_text:
            yaml_text = "version: 1\nname: " + (self.selected_package_name or "")
        yaml_text = apply_placement_to_yaml_text(yaml_text, self.placement_editor.get_config())
        rows = self.components_editor.get_rows()
        return apply_components_to_yaml_text(yaml_text, rows)

    def save_package_yaml(self) -> None:
        if not self.selected_package_path or not self.selected_package_name:
            return

        try:
            yaml_text = self._yaml_text_with_components()
        except ValueError as exc:
            messagebox.showerror(APP_NAME, str(exc))
            return

        component_errors = validate_component_rows(self.components_editor.get_rows())
        if component_errors:
            messagebox.showerror(APP_NAME, "Fix components before saving:\n\n" + "\n".join(component_errors))
            return

        if not yaml_text.strip():
            messagebox.showinfo(APP_NAME, f"Editor is empty — create or paste {OBJECT_YAML_NAME} first.")
            return

        self.yaml_editor.delete("1.0", tk.END)
        self.yaml_editor.insert(tk.END, yaml_text)

        if self._pending_custom_glb is not None:
            self._save_pending_custom_object(yaml_text)
            return

        self.set_status(f"Saving {OBJECT_YAML_NAME} to Quest…")
        self.update_idletasks()

        ok, message = save_yaml_to_quest(
            self.selected_package_path,
            self.selected_package_name,
            self._cache_root,
            yaml_text,
        )
        if not ok:
            messagebox.showerror(APP_NAME, message)
            self.set_status(message)
            return

        self.package_yaml_on_quest = True
        self.package_yaml_status_var.set(message)
        self.create_yaml_btn.configure(state=tk.DISABLED)
        messagebox.showinfo(APP_NAME, message)
        self.set_status(message)

    def _save_pending_custom_object(self, yaml_text: str) -> None:
        if (
            self._pending_custom_glb is None
            or not self.selected_package_path
            or not self.selected_package_name
        ):
            return

        package_name = self.selected_package_name
        glb_path = self._pending_custom_glb
        remote = self.selected_package_path

        self.set_status(f"Creating {package_name} on Meta Quest…")
        self.update_idletasks()

        created = create_quest_package(package_name)
        if not created.ok:
            messagebox.showerror(APP_NAME, created.message)
            self.set_status(created.message)
            return

        uploaded = push_model_to_package(package_name, glb_path)
        if not uploaded.ok:
            delete_remote_dir(remote)
            messagebox.showerror(APP_NAME, uploaded.message)
            self.set_status(uploaded.message)
            return

        ok, message = save_yaml_to_quest(
            remote,
            package_name,
            self._cache_root,
            yaml_text,
        )
        if not ok:
            delete_remote_dir(remote)
            messagebox.showerror(APP_NAME, message)
            self.set_status(message)
            return

        glb_name = uploaded.file_name or glb_path.name
        self._pending_custom_glb = None
        self.package_yaml_on_quest = True
        self.package_files_var.set(f"{glb_name}, {OBJECT_YAML_NAME}")
        self.package_yaml_status_var.set(message)
        self.create_yaml_btn.configure(state=tk.DISABLED)
        self.add_model_btn.configure(state=tk.NORMAL)
        success = f"Created {package_name} on Meta Quest."
        messagebox.showinfo(APP_NAME, success)
        self.set_status(success)

    def check_device(self) -> None:
        result = check_device_connected()
        self._device_connected = result.ok
        self._device_status_message = result.message
        if result.ok:
            messagebox.showinfo(APP_NAME, result.message)
        else:
            messagebox.showerror(APP_NAME, result.message)
        self.set_status(result.message)
        if hasattr(self, "home_connection_var"):
            self._refresh_home_connection_ui()

    def go_custom_objects(self) -> None:
        self.quest_navigate_to(QUEST_CUSTOM_OBJECTS)

    def quest_go_up(self) -> None:
        if self.quest_path.rstrip("/") == QUEST_CUSTOM_OBJECTS.rstrip("/"):
            self.set_status("Already at Custom Objects root")
            return

        parent = parent_remote_path(self.quest_path)
        if parent is None:
            self.set_status("Already at root")
            return

        if len(parent) < len(QUEST_CUSTOM_OBJECTS.rstrip("/")):
            self.quest_navigate_to(QUEST_CUSTOM_OBJECTS)
            return

        self.quest_navigate_to(parent)

    def quest_navigate_to(self, remote_path: str) -> None:
        self.quest_path = remote_path
        self.quest_path_var.set(remote_path)
        self.refresh_quest_listing()

    def refresh_quest_listing(self) -> None:
        if not hasattr(self, "quest_listbox"):
            return

        self.quest_listbox.delete(0, tk.END)
        self._quest_entries.clear()
        self._clear_magazine_rows()
        self.set_status(f"Listing {self.quest_path}…")
        self.update_idletasks()

        result, entries = list_remote_dir(self.quest_path)
        if not result.ok:
            self.set_status(result.message)
            messagebox.showerror(APP_NAME, result.message)
            return

        if self._is_magazines_root():
            self._show_magazine_list()
            self._populate_magazine_list(entries)
            return

        self._show_custom_objects_list()
        if not entries:
            self.quest_listbox.insert(tk.END, "(empty folder)")
            self.set_status(f"{self.quest_path} — empty")
            return

        for entry in entries:
            prefix = "[DIR]  " if entry.is_dir else "[FILE] "
            self.quest_listbox.insert(tk.END, prefix + entry.name)
            self._quest_entries.append((entry.name, entry.is_dir))

        dirs = sum(1 for _, is_dir in self._quest_entries if is_dir)
        files = len(self._quest_entries) - dirs
        self.set_status(f"{self.quest_path} — {dirs} folder(s), {files} file(s)")

    def _clear_magazine_rows(self) -> None:
        for child in self.magazine_rows_frame.winfo_children():
            child.destroy()
        self._magazine_check_vars.clear()
        self._selected_magazine_row = None

    def _populate_magazine_list(self, entries: list) -> None:
        load_result, activation = load_magazines_yaml(entries, self._cache_root)
        if not load_result.ok:
            messagebox.showerror(APP_NAME, load_result.message)
            self.set_status(load_result.message)
            return

        # Persist synced map (new folders added as false, removed folders dropped).
        save_result = save_magazines_yaml(activation, self._cache_root)
        if not save_result.ok:
            messagebox.showerror(APP_NAME, save_result.message)
            self.set_status(save_result.message)
            return

        self._magazine_activation = activation
        folders = [entry for entry in entries if entry.is_dir]
        if not folders:
            empty = ttk.Label(
                self.magazine_rows_frame,
                text="(empty folder)",
                foreground=MUTED_FG,
                padding=8,
            )
            empty.pack(anchor=tk.W)
            self.set_status(f"{self.quest_path} — empty")
            return

        for entry in folders:
            name = entry.name
            enabled = bool(activation.get(name, False))
            var = tk.BooleanVar(value=enabled)
            self._magazine_check_vars[name] = var
            self._quest_entries.append((name, True))

            row = ttk.Frame(self.magazine_rows_frame)
            row.pack(fill=tk.X, padx=4, pady=2)

            check = ttk.Checkbutton(
                row,
                variable=var,
                command=lambda magazine=name: self._on_magazine_toggle(magazine),
            )
            check.pack(side=tk.LEFT)

            label = ttk.Label(row, text=name, cursor="hand2")
            label.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(4, 0))
            label.bind("<Double-Button-1>", lambda _e, magazine=name: self._open_magazine_named(magazine))
            label.bind("<Button-1>", lambda _e, magazine=name: self._select_magazine_row(magazine))
            label.bind("<Button-3>", lambda e, magazine=name: self._magazine_row_context(e, magazine))
            row.bind("<Button-3>", lambda e, magazine=name: self._magazine_row_context(e, magazine))
            row.bind("<MouseWheel>", self._on_magazine_list_mousewheel)
            check.bind("<MouseWheel>", self._on_magazine_list_mousewheel)
            label.bind("<MouseWheel>", self._on_magazine_list_mousewheel)

        active = active_magazine_count(activation)
        self.set_status(
            f"{self.quest_path} — {len(folders)} magazine(s), "
            f"{active}/{MAGAZINE_SHELF_LIMIT} active on shelf"
        )

    def _select_magazine_row(self, name: str) -> None:
        self._selected_magazine_row = name

    def _open_magazine_named(self, name: str) -> None:
        remote = f"{self.quest_path.rstrip('/')}/{name}"
        self.open_magazine(remote, name)

    def _magazine_row_context(self, event: tk.Event, name: str) -> None:
        self._selected_magazine_row = name
        self.workspace_context_menu.tk_popup(event.x_root, event.y_root)

    def _on_magazine_toggle(self, name: str) -> None:
        var = self._magazine_check_vars.get(name)
        if var is None:
            return

        enabled = bool(var.get())
        if enabled:
            current_active = active_magazine_count(
                {key: value.get() for key, value in self._magazine_check_vars.items()}
            )
            # current_active already includes this newly checked item
            if current_active > MAGAZINE_SHELF_LIMIT:
                var.set(False)
                messagebox.showwarning(
                    APP_NAME,
                    f"The shelf supports at most {MAGAZINE_SHELF_LIMIT} active magazines.\n"
                    "Uncheck another magazine before activating this one.",
                    parent=self,
                )
                return

        self._magazine_activation = {
            key: bool(value.get()) for key, value in self._magazine_check_vars.items()
        }
        result = save_magazines_yaml(self._magazine_activation, self._cache_root)
        if not result.ok:
            var.set(not enabled)
            messagebox.showerror(APP_NAME, result.message)
            self.set_status(result.message)
            return

        active = active_magazine_count(self._magazine_activation)
        state = "active" if enabled else "inactive"
        self.set_status(
            f"{name} is {state} — {active}/{MAGAZINE_SHELF_LIMIT} on shelf"
        )

    def on_quest_context_menu(self, event: tk.Event) -> None:
        if not self._quest_entries:
            return

        index = self.quest_listbox.nearest(event.y)
        bounds = self.quest_listbox.bbox(index)
        if bounds is None:
            return
        _, row_y, _, row_height = bounds
        if not row_y <= event.y < row_y + row_height:
            return

        _, is_dir = self._quest_entries[index]
        if not is_dir:
            return

        self.quest_listbox.selection_clear(0, tk.END)
        self.quest_listbox.selection_set(index)
        self.quest_listbox.activate(index)
        self.workspace_context_menu.tk_popup(event.x_root, event.y_root)

    def delete_selected_folder(self) -> None:
        entry = self._get_selected_entry()
        if not entry:
            return

        name, is_dir = entry
        if not is_dir:
            return

        if not (self._is_custom_objects_root() or self._is_magazines_root()):
            messagebox.showerror(APP_NAME, "Folders can only be deleted from a root list.")
            return

        kind = "magazine" if self._is_magazines_root() else "custom object"
        confirmed = messagebox.askyesno(
            APP_NAME,
            f'Delete {kind} "{name}" from Meta Quest?\n\n'
            "This permanently deletes the folder and all files inside it.",
            icon=messagebox.WARNING,
            parent=self,
        )
        if not confirmed:
            return

        remote = f"{self.quest_path.rstrip('/')}/{name}"
        self.set_status(f"Deleting {name}…")
        self.update_idletasks()
        result = delete_remote_dir(remote)
        if not result.ok:
            messagebox.showerror(APP_NAME, result.message)
            self.set_status(result.message)
            return

        self.refresh_quest_listing()
        self.set_status(f"Deleted {kind}: {name}")

    def on_quest_open_selected(self, _event: tk.Event | None = None) -> None:
        entry = self._get_selected_entry()
        if not entry:
            return

        name, is_dir = entry
        if not is_dir:
            self.set_status(f"File: {name}")
            return

        if self._is_magazines_root():
            remote = f"{self.quest_path.rstrip('/')}/{name}"
            self.open_magazine(remote, name)
            return

        if not self.quest_path.startswith(QUEST_CUSTOM_OBJECTS):
            messagebox.showinfo(APP_NAME, "Open Custom Objects on the Quest first.")
            return

        if self._is_custom_objects_root():
            remote = f"{self.quest_path.rstrip('/')}/{name}"
        else:
            remote = self.quest_path.rstrip("/")
            name = remote.rsplit("/", 1)[-1]

        self.select_package(remote, name)


def run_app() -> None:
    app = StudioApp()
    app.mainloop()
