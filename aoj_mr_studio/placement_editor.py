"""Tkinter UI for object.yaml placement (stacking / surfaces)."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

import yaml

from aoj_mr_studio.config import STICK_ROTATION_AXES, SURFACE_TYPES
from aoj_mr_studio.placement_schema import PlacementConfig, placement_from_dict
from aoj_mr_studio.theme import MUTED_FG


def _surface_labels() -> list[str]:
    return [f"{value} — {label}" for value, label in SURFACE_TYPES.items()]


def _surface_value_from_label(label: str) -> int:
    try:
        return int(label.split(" — ", 1)[0])
    except (ValueError, IndexError):
        return 0


def _label_for_surface(value: int) -> str:
    name = SURFACE_TYPES.get(value, SURFACE_TYPES[0])
    return f"{value} — {name}"


def _stick_axis_labels() -> list[str]:
    return [f"{value} — {label}" for value, label in STICK_ROTATION_AXES.items()]


def _stick_axis_value_from_label(label: str) -> int:
    try:
        return int(label.split(" — ", 1)[0])
    except (ValueError, IndexError):
        return 0


def _label_for_stick_axis(value: int) -> str:
    name = STICK_ROTATION_AXES.get(value, STICK_ROTATION_AXES[0])
    return f"{value} — {name}"


class PlacementEditor(ttk.LabelFrame):
    def __init__(self, master: tk.Misc, on_change: Callable[[], None] | None = None) -> None:
        super().__init__(master, text="Placement", padding=(8, 6))
        self._on_change = on_change or (lambda: None)

        row = ttk.Frame(self)
        row.pack(fill=tk.X)

        surface_cell = ttk.Frame(row)
        surface_cell.pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(surface_cell, text="surfaceType", font=("", 8)).pack(anchor=tk.W)
        self.surface_var = tk.StringVar(value=_label_for_surface(0))
        self.surface_combo = ttk.Combobox(
            surface_cell,
            textvariable=self.surface_var,
            values=_surface_labels(),
            state="readonly",
            width=28,
        )
        self.surface_combo.pack(anchor=tk.W)
        self.surface_combo.bind("<<ComboboxSelected>>", lambda _event: self._notify_change())

        stick_cell = ttk.Frame(row)
        stick_cell.pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(stick_cell, text="allowStickRotation", font=("", 8)).pack(anchor=tk.W)
        self.allow_stick_rotation_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            stick_cell,
            text="Rotate with stick before placing",
            variable=self.allow_stick_rotation_var,
            command=self._on_stick_rotation_changed,
        ).pack(anchor=tk.W)

        axis_cell = ttk.Frame(row)
        axis_cell.pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(axis_cell, text="stickRotationAxis", font=("", 8)).pack(anchor=tk.W)
        self.stick_axis_var = tk.StringVar(value=_label_for_stick_axis(0))
        self.stick_axis_combo = ttk.Combobox(
            axis_cell,
            textvariable=self.stick_axis_var,
            values=_stick_axis_labels(),
            state="readonly",
            width=16,
        )
        self.stick_axis_combo.pack(anchor=tk.W)
        self.stick_axis_combo.bind("<<ComboboxSelected>>", lambda _event: self._notify_change())

        speed_cell = ttk.Frame(row)
        speed_cell.pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(speed_cell, text="stickRotationSpeed", font=("", 8)).pack(anchor=tk.W)
        self.stick_speed_var = tk.StringVar(value="90")
        self.stick_speed_entry = ttk.Entry(speed_cell, textvariable=self.stick_speed_var, width=8)
        self.stick_speed_entry.pack(anchor=tk.W)
        self.stick_speed_var.trace_add("write", lambda *_args: self._notify_change())

        anchor_cell = ttk.Frame(row)
        anchor_cell.pack(side=tk.LEFT, padx=(0, 12))
        ttk.Label(anchor_cell, text="providesAnchor", font=("", 8)).pack(anchor=tk.W)
        self.provides_anchor_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            anchor_cell,
            text="Accept object on top",
            variable=self.provides_anchor_var,
            command=self._on_provides_anchor_changed,
        ).pack(anchor=tk.W)

        target_cell = ttk.Frame(row)
        target_cell.pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(target_cell, text="anchorTarget", font=("", 8)).pack(anchor=tk.W)
        self.anchor_target_var = tk.StringVar(value="")
        self.anchor_target_entry = ttk.Entry(target_cell, textvariable=self.anchor_target_var, width=18)
        self.anchor_target_entry.pack(anchor=tk.W)
        self.anchor_target_var.trace_add("write", lambda *_args: self._notify_change())

        self.hint_var = tk.StringVar(value="")
        ttk.Label(
            self,
            textvariable=self.hint_var,
            foreground=MUTED_FG,
            font=("", 8),
            wraplength=900,
        ).pack(anchor=tk.W, pady=(6, 0))

        self._update_hint()
        self._update_anchor_target_state()
        self._update_stick_rotation_state()

    def _notify_change(self) -> None:
        self._update_hint()
        self._on_change()

    def _on_provides_anchor_changed(self) -> None:
        self._update_anchor_target_state()
        self._notify_change()

    def _on_stick_rotation_changed(self) -> None:
        self._update_stick_rotation_state()
        self._notify_change()

    def _update_anchor_target_state(self) -> None:
        state = tk.NORMAL if self.provides_anchor_var.get() else tk.DISABLED
        self.anchor_target_entry.configure(state=state)

    def _update_stick_rotation_state(self) -> None:
        state = "readonly" if self.allow_stick_rotation_var.get() else tk.DISABLED
        self.stick_axis_combo.configure(state=state)
        entry_state = tk.NORMAL if self.allow_stick_rotation_var.get() else tk.DISABLED
        self.stick_speed_entry.configure(state=entry_state)

    def _update_hint(self) -> None:
        surface = _surface_value_from_label(self.surface_var.get())
        if self.allow_stick_rotation_var.get():
            self.hint_var.set(
                "allowStickRotation: use the right stick to rotate while placing (before confirming position)."
            )
        elif surface == 5:
            self.hint_var.set(
                "surfaceType 5 (Object): place this prop on another object that has providesAnchor enabled."
            )
        elif self.provides_anchor_var.get():
            self.hint_var.set(
                "providesAnchor: other props with surfaceType 5 can be placed on this object."
            )
        else:
            self.hint_var.set("")

    def get_config(self) -> PlacementConfig:
        try:
            stick_speed = float(self.stick_speed_var.get())
        except (TypeError, ValueError):
            stick_speed = 90.0

        return PlacementConfig(
            surface_type=_surface_value_from_label(self.surface_var.get()),
            provides_anchor=bool(self.provides_anchor_var.get()),
            anchor_target=self.anchor_target_var.get().strip(),
            allow_stick_rotation=bool(self.allow_stick_rotation_var.get()),
            stick_rotation_axis=_stick_axis_value_from_label(self.stick_axis_var.get()),
            stick_rotation_speed=stick_speed,
        )

    def set_config(self, config: PlacementConfig) -> None:
        self.surface_var.set(_label_for_surface(config.surface_type))
        self.provides_anchor_var.set(config.provides_anchor)
        self.anchor_target_var.set(config.anchor_target)
        self.allow_stick_rotation_var.set(config.allow_stick_rotation)
        self.stick_axis_var.set(_label_for_stick_axis(config.stick_rotation_axis))
        self.stick_speed_var.set(str(config.stick_rotation_speed))
        self._update_anchor_target_state()
        self._update_stick_rotation_state()
        self._update_hint()

    def load_from_yaml_text(self, yaml_text: str) -> None:
        if not yaml_text.strip():
            self.set_config(PlacementConfig())
            return

        parsed = yaml.safe_load(yaml_text)
        if not isinstance(parsed, dict):
            self.set_config(PlacementConfig())
            return

        self.set_config(placement_from_dict(parsed))

    def clear(self) -> None:
        self.set_config(PlacementConfig())
