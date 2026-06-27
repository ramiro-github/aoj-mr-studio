"""AOJ MR Studio desktop GUI."""

from __future__ import annotations

import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, simpledialog, ttk

from aoj_mr_studio.adb_path import adb_source_label, find_adb
from aoj_mr_studio.adb_sync import (
    check_device_connected,
    list_remote_dir,
    parent_remote_path,
)
from aoj_mr_studio.component_editor import ComponentsEditor
from aoj_mr_studio.component_schema import apply_components_to_yaml_text, validate_component_rows
from aoj_mr_studio.placement_editor import PlacementEditor
from aoj_mr_studio.placement_schema import apply_placement_to_yaml_text
from aoj_mr_studio.config import (
    APP_NAME,
    OBJECT_YAML_NAME,
    QUEST_CUSTOM_OBJECTS,
)
from aoj_mr_studio.package_actions import create_quest_package, push_model_to_package
from aoj_mr_studio.package_defaults import sync_package_context
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

        self.quest_path = QUEST_CUSTOM_OBJECTS
        self._quest_entries: list[tuple[str, bool]] = []
        self.selected_package_path: str | None = None
        self.selected_package_name: str | None = None
        self.package_yaml_on_quest = False
        self._cache_root = Path.home() / ".aoj_mr_studio" / "cache"
        self._suppress_yaml_sync = False
        self._yaml_sync_job: str | None = None

        self.container = ttk.Frame(self)
        self.container.pack(fill=tk.BOTH, expand=True)

        self.start_frame = ttk.Frame(self.container)
        self.workspace_frame = ttk.Frame(self.container)
        self.package_frame = ttk.Frame(self.container)

        self.status_var = tk.StringVar(value="Ready")
        ttk.Label(self, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W, padding=(6, 2)).pack(
            fill=tk.X, side=tk.BOTTOM
        )

        self._build_start_screen()
        self._build_workspace_screen()
        self._build_package_screen()
        self.show_start_screen()

    def _hide_all_screens(self) -> None:
        self.start_frame.pack_forget()
        self.workspace_frame.pack_forget()
        self.package_frame.pack_forget()

    def set_status(self, message: str) -> None:
        self.status_var.set(message)

    def show_start_screen(self) -> None:
        self._hide_all_screens()
        self.start_frame.pack(fill=tk.BOTH, expand=True)
        self.title(APP_NAME)
        self.set_status("Connect Quest and open Custom Objects")

    def show_workspace_screen(self) -> None:
        self._hide_all_screens()
        self.workspace_frame.pack(fill=tk.BOTH, expand=True)
        self.title(f"{APP_NAME} — Custom Objects")
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
        self.load_package_editor()

    def _build_start_screen(self) -> None:
        outer = ttk.Frame(self.start_frame, padding=24)
        outer.pack(fill=tk.BOTH, expand=True)

        center = ttk.Frame(outer)
        center.place(relx=0.5, rely=0.5, anchor=tk.CENTER)

        self.folder_icon = tk.Label(
            center,
            text="\U0001F4C1",
            font=("Segoe UI Emoji", 96),
            cursor="hand2",
        )
        self.folder_icon.pack()
        self.folder_icon.bind("<Button-1>", lambda _event: self.open_quest_custom_objects())

        ttk.Label(
            center,
            text="Open Custom Objects on Quest",
            font=("", 14),
        ).pack(pady=(16, 4))

        ttk.Label(
            center,
            text="Age of Joy MR packages on the headset\n(object.yaml + .glb per folder)",
            justify=tk.CENTER,
            foreground="#555555",
        ).pack(pady=(0, 8))

        ttk.Label(
            center,
            text=QUEST_CUSTOM_OBJECTS,
            font=("Consolas", 9),
            foreground="#666666",
        ).pack(pady=(0, 20))

        ttk.Button(center, text="Open on Quest", command=self.open_quest_custom_objects).pack()

        adb = find_adb()
        if not adb:
            ttk.Label(
                center,
                text="adb not found — run scripts/copy-adb.ps1",
                foreground="#aa3300",
            ).pack(pady=(12, 0))

    def open_quest_custom_objects(self) -> None:
        self.set_status("Connecting to Quest…")
        self.update_idletasks()

        device = check_device_connected()
        if not device.ok:
            messagebox.showerror(APP_NAME, device.message)
            self.set_status(device.message)
            return

        self.quest_path = QUEST_CUSTOM_OBJECTS
        self.quest_path_var.set(self.quest_path)
        self.show_workspace_screen()

        result, entries = list_remote_dir(self.quest_path)
        if not result.ok:
            messagebox.showerror(APP_NAME, result.message)
            self.set_status(result.message)
            self.show_start_screen()
            return

        count = sum(1 for entry in entries if entry.is_dir)
        self.set_status(f"Quest Custom Objects — {count} package(s) ({adb_source_label()})")

    def _build_workspace_screen(self) -> None:
        header = ttk.Frame(self.workspace_frame, padding=(8, 8, 8, 4))
        header.pack(fill=tk.X)

        ttk.Button(header, text="Refresh", command=self.refresh_quest_listing).pack(side=tk.LEFT)
        ttk.Button(header, text="Create folder", command=self.create_quest_folder).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(header, text="Home", command=self.show_start_screen).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(header, text="Check device", command=self.check_device).pack(side=tk.RIGHT)

        path_row = ttk.Frame(header)
        path_row.pack(fill=tk.X, pady=(8, 0))
        ttk.Label(path_row, text="Quest:").pack(side=tk.LEFT)
        self.quest_path_var = tk.StringVar(value=self.quest_path)
        ttk.Entry(path_row, textvariable=self.quest_path_var, state="readonly").pack(
            side=tk.LEFT, fill=tk.X, expand=True, padx=(6, 0)
        )

        hint = ttk.Label(
            self.workspace_frame,
            text=f"Double-click a package folder to edit {OBJECT_YAML_NAME}.",
            foreground="#555555",
            padding=(8, 0, 8, 4),
        )
        hint.pack(anchor=tk.W)

        list_frame = ttk.Frame(self.workspace_frame, padding=(8, 0, 8, 8))
        list_frame.pack(fill=tk.BOTH, expand=True)

        self.quest_listbox = tk.Listbox(list_frame, font=("Consolas", 10))
        scroll = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.quest_listbox.yview)
        self.quest_listbox.configure(yscrollcommand=scroll.set)
        self.quest_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.quest_listbox.bind("<Double-Button-1>", self.on_quest_open_selected)

    def create_quest_folder(self) -> None:
        name = simpledialog.askstring(APP_NAME, "New package folder name:", parent=self)
        if not name:
            return

        self.set_status(f"Creating folder {name}…")
        self.update_idletasks()

        result = create_quest_package(name)
        if not result.ok:
            messagebox.showerror(APP_NAME, result.message)
            self.set_status(result.message)
            return

        self.refresh_quest_listing()
        self.set_status(f"Created package folder: {name.strip()}")
        messagebox.showinfo(APP_NAME, f"Folder created on Quest:\n{name.strip()}")

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
        ttk.Button(header, text="Home", command=self.show_start_screen).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(header, text="Refresh", command=self.load_package_editor).pack(side=tk.LEFT, padx=(6, 0))
        ttk.Button(header, text="Add model", command=self.add_model_to_package).pack(side=tk.LEFT, padx=(6, 0))

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
            foreground="#555555",
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
            foreground="#444444",
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

    def _is_custom_objects_root(self) -> bool:
        return self.quest_path.rstrip("/") == QUEST_CUSTOM_OBJECTS.rstrip("/")

    def _get_selected_entry(self) -> tuple[str, bool] | None:
        selection = self.quest_listbox.curselection()
        if not selection:
            return None
        index = selection[0]
        if index >= len(self._quest_entries):
            return None
        return self._quest_entries[index]

    def select_package(self, remote_path: str, package_name: str) -> None:
        self.selected_package_path = remote_path
        self.selected_package_name = package_name
        self.show_package_screen()

    def load_package_editor(self) -> None:
        if not self.selected_package_path or not self.selected_package_name:
            return

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

    def check_device(self) -> None:
        result = check_device_connected()
        if result.ok:
            messagebox.showinfo(APP_NAME, result.message)
        else:
            messagebox.showerror(APP_NAME, result.message)
        self.set_status(result.message)

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
        self.set_status(f"Listing {self.quest_path}…")
        self.update_idletasks()

        result, entries = list_remote_dir(self.quest_path)
        if not result.ok:
            self.set_status(result.message)
            messagebox.showerror(APP_NAME, result.message)
            return

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

    def on_quest_open_selected(self, _event: tk.Event | None = None) -> None:
        entry = self._get_selected_entry()
        if not entry:
            return

        name, is_dir = entry
        if not is_dir:
            self.set_status(f"File: {name}")
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
