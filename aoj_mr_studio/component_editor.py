"""Tkinter UI for editing object.yaml components."""

from __future__ import annotations

import tkinter as tk
from tkinter import colorchooser, messagebox, ttk
from typing import Any, Callable

from aoj_mr_studio.component_schema import (
    COMPONENT_SCHEMAS,
    component_rows_from_dict,
    normalize_hex_color,
)
from aoj_mr_studio.config import COMPONENT_IDS
from aoj_mr_studio.glb_nodes import looks_like_bone_name
from aoj_mr_studio.package_defaults import (
    PackageContext,
    merge_component_config,
    str_field_suggestions,
    suggest_component_config,
)

import yaml


class ComponentRow(ttk.Frame):
    def __init__(
        self,
        master: tk.Misc,
        editor: ComponentsEditor,
        on_remove: Callable[[ComponentRow], None],
        on_change: Callable[[], None],
        *,
        component_id: str = "grab",
        config: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(master)
        self._editor = editor
        self.on_remove = on_remove
        self.on_change = on_change
        self.field_vars: dict[str, tk.Variable] = {}
        self._color_swatches: dict[str, tk.Label] = {}

        type_cell = ttk.Frame(self)
        type_cell.pack(side=tk.LEFT, padx=(0, 8))
        ttk.Label(type_cell, text="Component", font=("", 8)).pack(anchor=tk.W)

        self.type_var = tk.StringVar(value=component_id if component_id in COMPONENT_IDS else COMPONENT_IDS[0])
        self.type_combo = ttk.Combobox(
            type_cell,
            textvariable=self.type_var,
            values=list(COMPONENT_IDS),
            state="readonly",
            width=10,
        )
        self.type_combo.pack(anchor=tk.W)
        self.type_combo.bind("<<ComboboxSelected>>", lambda _event: self._on_type_changed())

        self.options_frame = ttk.Frame(self)
        self.options_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        ttk.Button(self, text="Remove", command=lambda: on_remove(self)).pack(side=tk.RIGHT, padx=(8, 0))

        self._build_option_columns(config)

    def _notify_change(self, *_args: object) -> None:
        self.on_change()

    def _on_type_changed(self) -> None:
        self._build_option_columns({})
        self._notify_change()

    def _resolve_config(self, comp_id: str, config: dict[str, Any] | None) -> dict[str, Any]:
        suggested = self._editor.defaults_for(comp_id)
        return merge_component_config(comp_id, config, suggested)

    def _is_editable_combobox_field(self, comp_id: str, field_key: str) -> bool:
        if comp_id == "animator" and field_key in ("clip", "target"):
            return True
        return False

    def _update_color_swatch(self, field_key: str, *_args: object) -> None:
        swatch = self._color_swatches.get(field_key)
        var = self.field_vars.get(field_key)
        if swatch is None or var is None:
            return
        hex_value = normalize_hex_color(var.get())
        try:
            swatch.configure(background=hex_value)
        except tk.TclError:
            swatch.configure(background="#ffffff")

    def _pick_color(self, field_key: str) -> None:
        var = self.field_vars.get(field_key)
        if var is None:
            return
        initial = normalize_hex_color(var.get())
        _rgb, hex_result = colorchooser.askcolor(
            color=initial,
            title="Light color (RGB)",
            parent=self.winfo_toplevel(),
        )
        if hex_result:
            var.set(str(hex_result).lower())

    def _build_color_picker(self, cell: ttk.Frame, field_key: str, value: str) -> tk.Variable:
        var = tk.StringVar(value=normalize_hex_color(value))
        picker = ttk.Frame(cell)
        picker.pack(anchor=tk.W)

        swatch = tk.Label(
            picker,
            width=3,
            relief=tk.SUNKEN,
            borderwidth=1,
            background=normalize_hex_color(value),
        )
        swatch.pack(side=tk.LEFT, padx=(0, 4), ipady=4)
        self._color_swatches[field_key] = swatch

        ttk.Button(
            picker,
            text="Pick…",
            width=7,
            command=lambda: self._pick_color(field_key),
        ).pack(side=tk.LEFT)

        entry = ttk.Entry(picker, textvariable=var, width=9)
        entry.pack(side=tk.LEFT, padx=(4, 0))

        var.trace_add("write", lambda *_args: self._update_color_swatch(field_key))
        var.trace_add("write", self._notify_change)
        self._update_color_swatch(field_key)
        return var

    def _build_option_columns(self, config: dict[str, Any] | None) -> None:
        for child in self.options_frame.winfo_children():
            child.destroy()
        self.field_vars.clear()
        self._color_swatches.clear()

        comp_id = self.type_var.get()
        schema = COMPONENT_SCHEMAS.get(comp_id, ())
        normalized = self._resolve_config(comp_id, config)
        context = self._editor.package_context

        for index, field in enumerate(schema):
            cell = ttk.Frame(self.options_frame)
            cell.grid(row=0, column=index, padx=(0, 10), sticky=tk.N)

            ttk.Label(cell, text=field.label, font=("", 8)).pack(anchor=tk.W)

            if field.kind == "bool":
                var: tk.Variable = tk.BooleanVar(value=bool(normalized[field.key]))
                widget: tk.Widget = ttk.Checkbutton(cell, variable=var)
                var.trace_add("write", self._notify_change)
                widget.pack(anchor=tk.W)
            elif field.kind == "choice":
                var = tk.StringVar(value=str(normalized[field.key]))
                widget = ttk.Combobox(
                    cell,
                    textvariable=var,
                    values=list(field.choices),
                    state="readonly",
                    width=8,
                )
                var.trace_add("write", self._notify_change)
                widget.pack(anchor=tk.W)
            elif field.kind == "color":
                var = self._build_color_picker(cell, field.key, str(normalized[field.key]))
            elif field.kind == "float":
                var = tk.StringVar(value=str(normalized[field.key]))
                widget = ttk.Entry(cell, textvariable=var, width=10)
                var.trace_add("write", self._notify_change)
                widget.pack(anchor=tk.W)
            else:
                var = tk.StringVar(value=str(normalized[field.key]))
                suggestions = str_field_suggestions(comp_id, field.key, context)
                if suggestions or self._is_editable_combobox_field(comp_id, field.key):
                    widget = ttk.Combobox(
                        cell,
                        textvariable=var,
                        values=suggestions,
                        width=16 if comp_id == "animator" and field.key == "clip" else 14,
                    )
                else:
                    widget = ttk.Entry(cell, textvariable=var, width=14)
                var.trace_add("write", self._notify_change)
                widget.pack(anchor=tk.W)

            self.field_vars[field.key] = var

    def get_row(self) -> tuple[str, dict[str, Any]]:
        comp_id = self.type_var.get()
        schema = COMPONENT_SCHEMAS[comp_id]
        config: dict[str, Any] = {}

        for field in schema:
            raw = self.field_vars[field.key].get()
            if field.kind == "bool":
                config[field.key] = bool(raw)
            elif field.kind == "float":
                try:
                    config[field.key] = float(raw)
                except (TypeError, ValueError):
                    config[field.key] = float(field.default)
            elif field.kind == "color":
                config[field.key] = normalize_hex_color(raw, str(field.default))
            else:
                config[field.key] = str(raw).strip() if field.kind == "str" else str(raw)

        return comp_id, config

    def used_component_id(self) -> str:
        return self.type_var.get()


class ComponentsEditor(ttk.LabelFrame):
    def __init__(self, master: tk.Misc, on_change: Callable[[], None] | None = None) -> None:
        super().__init__(master, text="Components", padding=(8, 6))
        self._on_change = on_change or (lambda: None)
        self.rows: list[ComponentRow] = []
        self.package_context: PackageContext | None = None

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X, pady=(0, 6))
        ttk.Button(toolbar, text="Add Component", command=self.add_row).pack(side=tk.LEFT)
        self.components_hint_var = tk.StringVar(value="")
        ttk.Label(
            toolbar,
            textvariable=self.components_hint_var,
            foreground="#666666",
            font=("", 8),
        ).pack(side=tk.LEFT, padx=(12, 0))

        self.rows_container = ttk.Frame(self)
        self.rows_container.pack(fill=tk.X)

    def set_package_context(self, context: PackageContext | None, *, refresh: bool = True) -> None:
        self.package_context = context
        if refresh and self.rows:
            self.refresh_row_suggestions()

    def defaults_for(self, comp_id: str) -> dict[str, Any]:
        return suggest_component_config(comp_id, self.package_context)

    def _row_changed(self) -> None:
        self._update_hint()
        self._on_change()

    def _update_hint(self) -> None:
        hints: list[str] = []
        if self.package_context and self.package_context.glb_node_names:
            hints.append(f"GLB nodes: {', '.join(self.package_context.glb_node_names[:6])}")
        if self.package_context and self.package_context.glb_animation_names:
            hints.append(
                f"GLB animations: {', '.join(self.package_context.glb_animation_names[:6])}"
            )
        for comp_id, config in self.get_rows():
            if comp_id == "rotator" and not str(config.get("target", "")).strip():
                hints.append("rotator needs target (pick from list or type a GLB child name)")
            if comp_id == "animator" and not str(config.get("clip", "")).strip():
                hints.append("animator needs clip (pick from GLB animation list or type a name)")
            if comp_id == "animator" and str(config.get("target", "")).strip() and looks_like_bone_name(str(config.get("target", ""))):
                hints.append("animator target should be rig root (e.g. Armature) — not a bone")
        self.components_hint_var.set(" · ".join(hints))

    def _remove_row(self, row: ComponentRow) -> None:
        if row in self.rows:
            self.rows.remove(row)
        row.destroy()
        self._row_changed()

    def clear_rows(self) -> None:
        for row in list(self.rows):
            row.destroy()
        self.rows.clear()
        self._update_hint()

    def add_row(self, component_id: str = "", config: dict[str, Any] | None = None) -> None:
        used = {row.used_component_id() for row in self.rows}
        if component_id and component_id in used and config is None:
            messagebox.showinfo("Components", f"'{component_id}' is already in the list.")
            return
        if not component_id:
            available = [candidate for candidate in COMPONENT_IDS if candidate not in used]
            if not available:
                messagebox.showinfo("Components", "All implemented components are already added.")
                return
            component_id = available[0]

        row = ComponentRow(
            self.rows_container,
            editor=self,
            on_remove=self._remove_row,
            on_change=self._row_changed,
            component_id=component_id,
            config=config,
        )
        row.pack(fill=tk.X, pady=(0, 6))
        self.rows.append(row)
        self._row_changed()

    def load_from_yaml_text(self, yaml_text: str) -> None:
        self.clear_rows()
        if not yaml_text.strip():
            return

        parsed = yaml.safe_load(yaml_text)
        if not isinstance(parsed, dict):
            return

        for comp_id, config in component_rows_from_dict(parsed):
            self.add_row(comp_id, config)

    def get_rows(self) -> list[tuple[str, dict[str, Any]]]:
        return [row.get_row() for row in self.rows]

    def refresh_row_suggestions(self) -> None:
        for row in self.rows:
            comp_id = row.used_component_id()
            current = row.get_row()[1]
            resolved = merge_component_config(comp_id, current, self.defaults_for(comp_id))
            row._build_option_columns(resolved)
        self._update_hint()
