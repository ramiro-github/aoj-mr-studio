"""Default values for components based on package files and GLB nodes."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from aoj_mr_studio.adb_sync import RemoteEntry, pull_remote_file
from aoj_mr_studio.component_schema import normalize_component_config
from aoj_mr_studio.glb_nodes import (
    list_animator_target_candidates,
    looks_like_bone_name,
    read_glb_animation_names,
    read_glb_node_names,
    suggest_animator_clip,
    suggest_animator_target,
    suggest_rotator_target,
    suggest_video_target,
)


@dataclass
class PackageContext:
    package_name: str
    remote_path: str
    cache_root: Path
    package_files: list[str] = field(default_factory=list)
    glb_node_names: list[str] = field(default_factory=list)
    glb_animation_names: list[str] = field(default_factory=list)
    model_file: str = ""
    local_glb_path: Path | None = None


def _first_matching(files: list[str], suffix: str) -> str:
    suffix = suffix.lower()
    for name in files:
        if name.lower().endswith(suffix):
            return name
    return ""


def sync_package_context(
    remote_path: str,
    package_name: str,
    cache_root: Path,
    entries: list[RemoteEntry],
) -> PackageContext:
    package_files = [entry.name for entry in entries if not entry.is_dir]
    model_file = _first_matching(package_files, ".glb")

    node_names: list[str] = []
    animation_names: list[str] = []
    local_glb: Path | None = None
    if model_file:
        local_glb = cache_root / package_name / model_file
        if not local_glb.is_file():
            pull_remote_file(f"{remote_path.rstrip('/')}/{model_file}", local_glb)
        if local_glb.is_file():
            node_names = read_glb_node_names(local_glb)
            animation_names = read_glb_animation_names(local_glb)

    return PackageContext(
        package_name=package_name,
        remote_path=remote_path,
        cache_root=cache_root,
        package_files=package_files,
        glb_node_names=node_names,
        glb_animation_names=animation_names,
        model_file=model_file,
        local_glb_path=local_glb if local_glb is not None and local_glb.is_file() else None,
    )


def suggest_component_config(comp_id: str, context: PackageContext | None) -> dict[str, Any]:
    base = normalize_component_config(comp_id, {})
    if context is None:
        return base

    if comp_id == "rotator":
        base["target"] = suggest_rotator_target(context.glb_node_names)
        return base

    if comp_id == "video":
        base["file"] = _first_matching(context.package_files, ".mp4")
        if not base["file"]:
            base["file"] = _first_matching(context.package_files, ".webm")
        if not base["file"]:
            base["file"] = _first_matching(context.package_files, ".mov")
        base["target"] = suggest_video_target(context.glb_node_names)
        return base

    if comp_id == "animator":
        base["clip"] = suggest_animator_clip(context.glb_animation_names)
        base["target"] = suggest_animator_target(context.glb_node_names, context.local_glb_path)
        return base

    return base


def merge_component_config(
    comp_id: str,
    config: dict[str, Any] | None,
    suggested: dict[str, Any],
) -> dict[str, Any]:
    """Apply GLB defaults without overwriting explicit YAML values."""
    merged = dict(suggested)
    if not config:
        return normalize_component_config(comp_id, merged)

    for key, value in config.items():
        if isinstance(value, str) and not value.strip():
            suggested_value = merged.get(key)
            if isinstance(suggested_value, str) and suggested_value.strip():
                continue
        merged[key] = value

    if comp_id == "animator":
        target = str(merged.get("target", "")).strip()
        suggested_target = str(suggested.get("target", "")).strip()
        if target and looks_like_bone_name(target) and suggested_target:
            merged["target"] = suggested_target

    return normalize_component_config(comp_id, merged)


def str_field_suggestions(comp_id: str, field_key: str, context: PackageContext | None) -> list[str]:
    if context is None:
        return []

    if comp_id == "rotator" and field_key == "target":
        return list(context.glb_node_names)

    if comp_id == "video":
        if field_key == "target":
            return list(context.glb_node_names)
        if field_key == "file":
            return [
                name
                for name in context.package_files
                if name.lower().endswith((".mp4", ".webm", ".mov"))
            ]

    if comp_id == "grab" and field_key == "target":
        return list(context.glb_node_names)

    if comp_id == "animator":
        if field_key == "clip":
            return list(context.glb_animation_names)
        if field_key == "target":
            return list_animator_target_candidates(context.glb_node_names, context.local_glb_path)

    return []
