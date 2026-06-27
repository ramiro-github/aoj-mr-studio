"""Read node and animation names from GLB files (stdlib only)."""

from __future__ import annotations

import json
import re
import struct
from pathlib import Path
from typing import Any

_PREFERRED_ROTATOR_NODES = ("Blades", "Fan", "Rotor", "Spinner", "Propeller", "Wheel")
_PREFERRED_VIDEO_NODES = ("Screen", "Display", "Monitor", "TV", "Panel")
_PREFERRED_ANIMATOR_NODES = ("Armature", "Character", "Rig", "Skeleton")
_SKIP_NODE_NAMES = frozenset({"", "Root", "Scene"})
_BLENDER_MESH_DUPLICATE_SUFFIX = re.compile(r"\.\d{3,}$")


def _read_glb_json(glb_path: Path) -> dict[str, Any] | None:
    if not glb_path.is_file():
        return None

    data = glb_path.read_bytes()
    if len(data) < 12 or data[:4] != b"glTF":
        return None

    offset = 12
    while offset + 8 <= len(data):
        chunk_length = struct.unpack_from("<I", data, offset)[0]
        chunk_type = data[offset + 4 : offset + 8]
        offset += 8
        chunk_data = data[offset : offset + chunk_length]
        offset += chunk_length

        if chunk_type != b"JSON":
            continue

        try:
            document = json.loads(chunk_data.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return None

        return document if isinstance(document, dict) else None

    return None


def read_glb_node_names(glb_path: Path) -> list[str]:
    document = _read_glb_json(glb_path)
    if document is None:
        return []

    names: list[str] = []
    for node in document.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        name = str(node.get("name") or "").strip()
        if name and name not in names:
            names.append(name)
    return names


def read_glb_animation_names(glb_path: Path) -> list[str]:
    document = _read_glb_json(glb_path)
    if document is None:
        return []

    names: list[str] = []
    for index, animation in enumerate(document.get("animations") or []):
        if not isinstance(animation, dict):
            continue
        name = _animation_display_name(document, animation, index)
        if name and name not in names:
            names.append(name)
    return names


def _animation_display_name(document: dict[str, Any], animation: dict[str, Any], index: int) -> str:
    name = str(animation.get("name") or "").strip()
    if name:
        return name

    nodes = document.get("nodes") or []
    for channel in animation.get("channels") or []:
        if not isinstance(channel, dict):
            continue
        target = channel.get("target") or {}
        node_index = target.get("node")
        if isinstance(node_index, int) and 0 <= node_index < len(nodes):
            node = nodes[node_index]
            if isinstance(node, dict):
                node_name = str(node.get("name") or "").strip()
                if node_name:
                    return node_name

    return f"Animation_{index}"


def pick_preferred_node(names: list[str], preferred: tuple[str, ...]) -> str:
    lowered = {name.lower(): name for name in names}
    for candidate in preferred:
        match = lowered.get(candidate.lower())
        if match:
            return match
    return ""


def first_useful_node(names: list[str]) -> str:
    for name in names:
        if name not in _SKIP_NODE_NAMES:
            return name
    return names[0] if names else ""


def suggest_rotator_target(node_names: list[str]) -> str:
    picked = pick_preferred_node(node_names, _PREFERRED_ROTATOR_NODES)
    if picked:
        return picked
    return first_useful_node(node_names)


def suggest_video_target(node_names: list[str]) -> str:
    picked = pick_preferred_node(node_names, _PREFERRED_VIDEO_NODES)
    if picked:
        return picked
    return first_useful_node(node_names)


def suggest_animator_clip(animation_names: list[str]) -> str:
    return animation_names[0] if animation_names else ""


def looks_like_bone_name(name: str) -> bool:
    lowered = name.lower().strip()
    if not lowered:
        return False
    if lowered.startswith("mixamorig"):
        return True
    if "mixamorig:" in lowered:
        return True
    if lowered.endswith("_end") or lowered.endswith(":end"):
        return True
    if lowered.startswith("bone") or lowered.endswith("_bone"):
        return True
    return False


def looks_like_mesh_node_name(name: str) -> bool:
    """Heuristic for skinned-mesh child nodes (e.g. Blender Body.001, Mesh_0)."""
    lowered = name.lower().strip()
    if not lowered:
        return False
    if lowered.startswith("mesh_"):
        return True
    if _BLENDER_MESH_DUPLICATE_SUFFIX.search(name):
        return True
    return False


def _is_animator_target_candidate(name: str, mesh_only_names: set[str] | None = None) -> bool:
    if not name or name in _SKIP_NODE_NAMES:
        return False
    if looks_like_bone_name(name):
        return False
    if looks_like_mesh_node_name(name):
        return False
    if mesh_only_names and name in mesh_only_names:
        return False
    return True


def _mesh_only_node_names(document: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for node in document.get("nodes") or []:
        if not isinstance(node, dict):
            continue
        if node.get("mesh") is None or node.get("skin") is not None:
            continue
        name = str(node.get("name") or "").strip()
        if name and not pick_preferred_node([name], _PREFERRED_ANIMATOR_NODES):
            names.add(name)
    return names


def _build_parent_map(document: dict[str, Any]) -> dict[int, int]:
    parent: dict[int, int] = {}
    for index, node in enumerate(document.get("nodes") or []):
        if not isinstance(node, dict):
            continue
        for child_index in node.get("children") or []:
            if isinstance(child_index, int):
                parent[child_index] = index
    return parent


def _node_name_at(nodes: list[Any], index: int) -> str:
    if index < 0 or index >= len(nodes):
        return ""
    node = nodes[index]
    if not isinstance(node, dict):
        return ""
    return str(node.get("name") or "").strip()


def _walk_to_rig_root(nodes: list[Any], parent_map: dict[int, int], start_index: int) -> str:
    current: int | None = start_index
    fallback = ""
    while current is not None and 0 <= current < len(nodes):
        name = _node_name_at(nodes, current)
        if name:
            if pick_preferred_node([name], _PREFERRED_ANIMATOR_NODES):
                return name
            if not looks_like_bone_name(name) and name not in _SKIP_NODE_NAMES:
                if not looks_like_mesh_node_name(name):
                    fallback = name
        current = parent_map.get(current)
    return fallback


def _animator_target_from_document(document: dict[str, Any]) -> str:
    nodes = document.get("nodes") or []
    parent_map = _build_parent_map(document)

    for index, node in enumerate(nodes):
        if not isinstance(node, dict):
            continue
        if node.get("skin") is not None:
            name = str(node.get("name") or "").strip()
            if name and pick_preferred_node([name], _PREFERRED_ANIMATOR_NODES):
                return name
            rig = _walk_to_rig_root(nodes, parent_map, index)
            if rig:
                return rig
            if name and not looks_like_bone_name(name) and not looks_like_mesh_node_name(name):
                return name

    animations = document.get("animations") or []
    if animations and isinstance(animations[0], dict):
        for channel in animations[0].get("channels") or []:
            if not isinstance(channel, dict):
                continue
            target = channel.get("target") or {}
            node_index = target.get("node")
            if isinstance(node_index, int):
                rig = _walk_to_rig_root(nodes, parent_map, node_index)
                if rig:
                    return rig

    return ""


def suggest_animator_target(node_names: list[str], glb_path: Path | None = None) -> str:
    picked = pick_preferred_node(node_names, _PREFERRED_ANIMATOR_NODES)
    if picked:
        return picked

    mesh_only_names: set[str] | None = None
    if glb_path is not None:
        document = _read_glb_json(glb_path)
        if document is not None:
            mesh_only_names = _mesh_only_node_names(document)
            from_glb = _animator_target_from_document(document)
            if from_glb:
                return from_glb

    for name in node_names:
        if _is_animator_target_candidate(name, mesh_only_names):
            return name

    return ""


def list_animator_target_candidates(node_names: list[str], glb_path: Path | None = None) -> list[str]:
    candidates: list[str] = []
    seen: set[str] = set()
    mesh_only_names: set[str] | None = None
    if glb_path is not None:
        document = _read_glb_json(glb_path)
        if document is not None:
            mesh_only_names = _mesh_only_node_names(document)

    def add(name: str) -> None:
        if name and name not in seen:
            seen.add(name)
            candidates.append(name)

    for preferred in _PREFERRED_ANIMATOR_NODES:
        match = pick_preferred_node(node_names, (preferred,))
        if match:
            add(match)

    suggested = suggest_animator_target(node_names, glb_path)
    if suggested:
        add(suggested)

    for name in node_names:
        if _is_animator_target_candidate(name, mesh_only_names):
            add(name)

    return candidates
